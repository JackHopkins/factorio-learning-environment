import ast
import asyncio
import json
from datasetgen.mcts.conversation import GenerationParameters
from typing import List, Tuple, Optional, Union

from datasetgen.mcts.conversation import Conversation, Message
from datasetgen.mcts.conversation_formatter import PLANNING_ADDITION_PROMPT
from datasetgen.mcts.game_state import GameState
from datasetgen.mcts.mcts import MCTS
from datasetgen.mcts.program import Program
from factorio_entities import Entity, EntityGroup


class ChunkedMCTS(MCTS):

    def __init__(self, *args, logit_bias: Optional[float] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.logit_bias = logit_bias

    def _split_into_chunks(self, program_code: str) -> List[Program]:
        """Split the program code into chunks based on docstrings."""

        program_code = program_code.replace("from factorio_instance import *", "").strip()
        lines = program_code.splitlines()
        chunks = []
        module = ast.parse(program_code)

        # Find all docstrings and their positions
        docstring_positions = []
        for node in module.body:
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                docstring_positions.append((node.lineno - 1, node.end_lineno - 1, node.value.s))

        if not docstring_positions:
            return []

        # Handle everything before first docstring
        first_docstring_start = docstring_positions[0][0]
        if first_docstring_start > 0:
            preamble = lines[:first_docstring_start]
            if any(line.strip() for line in preamble):  # If there's any non-empty content
                chunks.append(Program(
                    code='\n'.join(preamble),
                    conversation=Conversation(messages=[])
                ))

        # Process each chunk
        for i, (start_pos, end_pos, docstring) in enumerate(docstring_positions):
            chunk_lines = []

            # Add docstring lines
            chunk_lines.extend(lines[start_pos:end_pos + 1])

            # Add code lines until next docstring or end
            if i < len(docstring_positions) - 1:
                next_start = docstring_positions[i + 1][0]
                chunk_lines.extend(lines[end_pos + 1:next_start])
            else:
                # For last chunk, add all remaining lines
                chunk_lines.extend(lines[end_pos + 1:])

            # Create program for this chunk
            if chunk_lines:
                chunks.append(Program(
                    code='\n'.join(chunk_lines),
                    conversation=Conversation(messages=[])
                ))

        return chunks

    async def _evaluate_chunks(self, chunks: List[Program], start_state: GameState, instance_id: int) \
            -> Tuple[List[Program], List[float], List[List[Union[Entity, EntityGroup]]]]:
        """
        Evaluate chunks sequentially while computing holdout values for each chunk.

        Args:
            chunks: List of program chunks to evaluate
            start_state: Initial game state
            instance_id: ID of the instance to use for evaluation

        Returns:
            Tuple containing:
            - List of evaluated program chunks
            - List of holdout values (one per chunk)
            - List of entity lists (one per chunk)
        """
        current_state = start_state
        holdout_values = []
        entity_list = []

        try:
            # Initialize holdout instance
            self.evaluator.holdout.reset(start_state)
            initial_holdout_value, _ = self.evaluator.holdout.score()

            # Evaluate each chunk while tracking holdout
            for chunk in chunks:
                # Reset active instance to current state
                instance = self.evaluator.instances[instance_id]
                instance.reset(current_state)

                if self.evaluator.logger:
                    self.evaluator.logger.update_instance(
                        self.evaluator.instance_to_port[instance_id],
                        program_id=chunk.id,
                        status="executing"
                    )

                # Evaluate chunk
                reward, state, response, entities = await self.evaluator._evaluate_single(
                    instance_id,
                    chunk,
                    instance
                )

                # Get holdout value after this chunk
                holdout_score, _ = self.evaluator.holdout.score()
                holdout_value = holdout_score - initial_holdout_value

                # Store results
                entity_list.append(entities)
                holdout_values.append(holdout_value)

                # Update chunk with results
                chunk.state = state
                chunk.value = reward
                chunk.response = response

                # Update state for next chunk
                current_state = state

                if self.evaluator.logger:
                    self.evaluator.logger.update_instance(
                        self.evaluator.holdout.tcp_port,
                        status="completed",
                        current_reward=holdout_value
                    )

            return chunks, holdout_values, entity_list

        except Exception as e:
            print(f"Error during chunk evaluation:")
            print(f"Instance ID: {instance_id}")
            print(f"Number of chunks: {len(chunks)}")
            print(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
            raise e

    async def search(self, n_iterations: int, samples_per_iteration: int, skip_failures: bool = False):
        for iteration in range(n_iterations):
            self.run_iteration(samples_per_iteration, skip_failures)
            self.evaluator.logger.update_progress()

    async def run_iteration(self, samples_per_iteration, skip_failures):
        parent = await self.db.sample_parent(version=self.version)
        start_state = parent.state if parent else self.initial_state
        conversation = parent.conversation if parent else Conversation(messages=[
            Message(role="system", content=self.system_prompt),
            Message(role="user",
                    content=f"Inventory: {json.dumps(start_state.inventory.__dict__)}\n\n{PLANNING_ADDITION_PROMPT}")
        ])

        self.evaluator.set_sampling_status()
        raw_programs = await self._generate_programs_batch(conversation, samples_per_iteration)

        # Process programs in parallel
        eval_futures = []
        for i, (program, chunks) in enumerate(raw_programs):
            instance_id = i % (len(self.evaluator.instances))
            self.evaluator.instances[instance_id].reset(start_state)
            self.evaluator.logger.update_instance(self.evaluator.instances[i].tcp_port, program_id=program.id, status="resetting")

            # Create evaluation future for this program's chunks
            eval_futures.append(self._process_program_chunks(
                program=program,
                chunks=chunks,
                start_state=start_state,
                instance_id=instance_id,
                parent_id=parent.id if parent else None,
                skip_failures=skip_failures
            ))

        # Wait for all programs to complete
        await asyncio.gather(*eval_futures)

    async def _process_program_chunks(self, program: Program, chunks: List[Program],
                                      start_state: GameState, instance_id: int,
                                      parent_id: Optional[int], skip_failures: bool):
        """Process and evaluate a program's chunks with updated holdout calculation"""
        try:
            evaluated_chunks, holdout_values, entity_list = await self._evaluate_chunks(
                chunks, start_state, instance_id
            )

            last_chunk_id = parent_id
            last_conversation_stage = program.conversation

            for chunk, holdout_value, entities in zip(evaluated_chunks, holdout_values, entity_list):
                try:
                    chunk_program = Program(
                        code=chunk.code,
                        conversation=program.conversation,
                        value=chunk.value - holdout_value,  # Use per-chunk holdout value
                        raw_reward=chunk.value,
                        holdout_value=holdout_value,
                        state=chunk.state,
                        response=chunk.response,
                        version=self.version,
                        version_description=self.version_description,
                        parent_id=last_chunk_id,
                        token_usage=program.token_usage // len(evaluated_chunks),
                        completion_token_usage=program.completion_token_usage // len(evaluated_chunks),
                        prompt_token_usage=program.prompt_token_usage // len(evaluated_chunks)
                    )

                    last_conversation_stage.add_result(
                        chunk.code,
                        chunk.response,
                        score=chunk.value,
                        advantage=chunk.value - holdout_value
                    )

                    chunk_program.id = hash(
                        (chunk.code, json.dumps(chunk_program.conversation.model_dump()['messages']))
                    )
                    chunk_program.conversation = last_conversation_stage

                    if skip_failures and "error" in chunk.response.lower():
                        print(f"Skipping chunk due to error in response:")
                        print(f"Response: {chunk.response}")
                        break

                    created = await self.db.create_program(chunk_program)
                    last_chunk_id = created.id

                except Exception as e:
                    print(f"Error processing chunk:")
                    print(f"Chunk code: {chunk.code}")
                    print(f"Response: {chunk.response}")
                    print(f"Error: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    raise

        except Exception as e:
            print(f"Failed to evaluate program on instance {instance_id}:")
            print(f"Program code: {program.code}")
            print(f"Number of chunks: {len(chunks)}")
            print(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

    async def _generate_programs_batch(self, conversation: Conversation, n_samples: int) -> List[Tuple[Program, List[Program]]]:
        generation_parameters = GenerationParameters(n = n_samples+1,
                                                         model = self.llm.model,
                                                         logit_bias=self.logit_bias,)
        # We generate one extra program in case there is an error in parsing one. This way we can always return n_samples programs to keep the servers occupied.
        programs = (await super()._generate_programs_batch(conversation, generation_params=generation_parameters))[:n_samples]
        chunked_programs = []

        for i, program in enumerate(programs):
            try:
                chunks = self._split_into_chunks(program.code)
                if not chunks:
                    continue

                chunked_programs.append((program, chunks))

            except Exception as e:
                print(f"Failed to process chunks for program: {str(e)}")
                continue

        return chunked_programs