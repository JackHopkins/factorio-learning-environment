import ast
import asyncio
import json
import pickle
import re
from typing import Optional, Tuple, Union

from fle.commons.models.conversation import Conversation
from fle.commons.models.game_state import GameState
from fle.commons.models.generation_parameters import GenerationParameters
from fle.commons.models.message import Message
from fle.commons.models.program import Program
from fle.env.entities import Entity, EntityGroup

from .mcts import MCTS


class ChunkedMCTS(MCTS):
    def __init__(self, *args, logit_bias: Optional[float] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.logit_bias = logit_bias

    from typing import List

    def _split_into_chunks(self, program_code: str) -> List[Program]:
        """Split the program code into chunks based on docstrings and comments."""
        program_code = program_code.replace(
            "from factorio_instance import *", ""
        ).strip()
        if not program_code:
            return []

        # Try to parse AST to find docstrings
        try:
            module = ast.parse(program_code)
            # Get all nodes that look like docstrings
            docstring_nodes = [
                node
                for node in module.body
                if isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
                and node.value.value.strip().startswith('"""')
            ]

            if docstring_nodes:
                # If we have docstrings, split based on their line numbers
                chunks = []
                lines = program_code.splitlines()
                last_end = 0

                for node in docstring_nodes:
                    # Get the start line (1-based in AST)
                    start_line = node.lineno - 1  # Convert to 0-based

                    # Get the chunk from last_end to this docstring
                    if start_line > last_end:
                        chunk_lines = lines[last_end:start_line]
                        chunk_content = "\n".join(chunk_lines).strip()
                        if chunk_content:
                            chunks.append(
                                Program(
                                    code=chunk_content,
                                    conversation=Conversation(messages=[]),
                                )
                            )

                    # Add all lines until we find the closing docstring
                    current_chunk = []
                    docstring_quotes = 1

                    for line in lines[start_line:]:
                        current_chunk.append(line)
                        docstring_quotes += line.strip().count('"""')
                        if docstring_quotes % 2 == 0:
                            break

                    last_end = start_line + len(current_chunk)

                    # Continue collecting lines until next docstring or end
                    while last_end < len(lines):
                        line = lines[last_end]
                        if line.strip().startswith('"""'):
                            break
                        current_chunk.append(line)
                        last_end += 1

                    chunk_content = "\n".join(current_chunk).strip()
                    if chunk_content:
                        chunks.append(
                            Program(
                                code=chunk_content,
                                conversation=Conversation(messages=[]),
                            )
                        )

                # Add any remaining code as final chunk
                if last_end < len(lines):
                    chunk_content = "\n".join(lines[last_end:]).strip()
                    if chunk_content:
                        chunks.append(
                            Program(
                                code=chunk_content,
                                conversation=Conversation(messages=[]),
                            )
                        )

                return chunks

        except SyntaxError:
            pass  # Fall through to line-based approach

        # Split the code into lines
        lines = program_code.splitlines()

        # Check for numbered comments (e.g., "# 1. Do something")
        has_numbered_comments = any(
            re.match(r"^#\s*\d+\.", line.strip()) for line in lines
        )

        if has_numbered_comments:
            # Handle code with numbered comments
            chunks = []
            current_chunk = None
            current_lines = []

            for line in lines:
                line = line.strip()
                if not line:
                    if current_lines:
                        current_lines.append("")
                    continue

                comment_match = re.match(r"^#\s*(\d+)\.\s*(.+)$", line)
                if comment_match:
                    if current_chunk and current_lines:
                        current_chunk.code = "\n".join(current_lines).strip()
                        chunks.append(current_chunk)
                        current_lines = []

                    current_chunk = Program(
                        code="", conversation=Conversation(messages=[])
                    )
                    current_lines = [line]
                elif current_chunk is not None:
                    current_lines.append(line)
                else:
                    # First content, start a chunk
                    current_chunk = Program(
                        code="", conversation=Conversation(messages=[])
                    )
                    current_lines = [line]

            if current_chunk and current_lines:
                current_chunk.code = "\n".join(current_lines).strip()
                chunks.append(current_chunk)

            return chunks
        else:
            # Split on task comment boundaries
            chunks = []
            current_chunk = []

            for i, line in enumerate(lines):
                line_stripped = line.strip()
                if not line_stripped:
                    if current_chunk:
                        current_chunk.append("")
                    continue

                # Start new chunk if this line is a task-starting comment
                if (
                    line_stripped.startswith("#")
                    and (i == 0 or not lines[i - 1].strip())
                    and i + 1 < len(lines)
                    and lines[i + 1].strip()
                    and not lines[i + 1].strip().startswith("#")
                ):
                    if current_chunk:
                        chunk_content = "\n".join(current_chunk).strip()
                        if chunk_content:
                            chunks.append(
                                Program(
                                    code=chunk_content,
                                    conversation=Conversation(messages=[]),
                                )
                            )
                    current_chunk = []

                current_chunk.append(line)

            if current_chunk:
                chunk_content = "\n".join(current_chunk).strip()
                if chunk_content:
                    chunks.append(
                        Program(
                            code=chunk_content, conversation=Conversation(messages=[])
                        )
                    )

            return (
                chunks
                if chunks
                else [
                    Program(
                        code=program_code.strip(),
                        conversation=Conversation(messages=[]),
                    )
                ]
            )

    # def _split_into_chunks(self, program_code: str) -> List[Program]:
    #     """Split the program code into chunks based on docstrings and blank lines."""
    #     program_code = program_code.replace("from factorio_instance import *", "").strip()
    #     if not program_code:
    #         return []
    #
    #     # Parse the AST to find docstring positions
    #     module = ast.parse(program_code)
    #     lines = program_code.splitlines()
    #
    #     # Find all docstrings and their positions
    #     docstring_positions = []
    #     for node in module.body:
    #         if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
    #             docstring_positions.append((node.lineno - 1, node.end_lineno - 1, node.value.s))
    #
    #     #if not docstring_positions:
    #     #    return []
    #
    #     chunks = []
    #
    #     # If there's content before the first docstring, add it as a chunk
    #     if docstring_positions and docstring_positions[0][0] > 0:
    #         content = '\n'.join(lines[:docstring_positions[0][0]]).strip()
    #         if content:
    #             chunks.append(Program(
    #                 code=content,
    #                 conversation=Conversation(messages=[])
    #             ))
    #
    #     # Process chunks based on number of docstrings
    #     if len(docstring_positions) == 1:
    #         # Get the docstring and all following content
    #         start_pos, end_pos, docstring = docstring_positions[0]
    #         docstring_lines = lines[start_pos:end_pos + 1]
    #         remaining_lines = lines[end_pos + 1:]
    #
    #         # Split remaining content on blank lines
    #         current_chunk = docstring_lines[:]
    #         for line in remaining_lines:
    #             if not line.strip():
    #                 if current_chunk:
    #                     chunks.append(Program(
    #                         code='\n'.join(current_chunk),
    #                         conversation=Conversation(messages=[])
    #                     ))
    #                     current_chunk = []
    #             else:
    #                 current_chunk.append(line)
    #
    #         # Add final chunk if it exists
    #         if current_chunk:
    #             chunks.append(Program(
    #                 code='\n'.join(current_chunk),
    #                 conversation=Conversation(messages=[])
    #             ))
    #
    #     elif len(docstring_positions) == 0:
    #         chunk_list = program_code.split('\n\n')
    #         chunks = [Program(
    #             code=chunk.strip(),
    #             conversation=Conversation(messages=[])
    #         ) for chunk in chunk_list if chunk.strip()]
    #
    #     else:
    #         # Multiple docstrings - process each section
    #         for i, (start_pos, end_pos, docstring) in enumerate(docstring_positions):
    #             chunk_lines = []
    #
    #             # Add the docstring
    #             chunk_lines.extend(lines[start_pos:end_pos + 1])
    #
    #             # Add code until next docstring
    #             if i < len(docstring_positions) - 1:
    #                 next_start = docstring_positions[i + 1][0]
    #                 code_lines = lines[end_pos + 1:next_start]
    #             else:
    #                 code_lines = lines[end_pos + 1:]
    #
    #             # Add non-empty lines
    #             for line in code_lines:
    #                 if line.strip():
    #                     chunk_lines.append(line)
    #
    #             if chunk_lines:
    #                 chunks.append(Program(
    #                     code='\n'.join(chunk_lines),
    #                     conversation=Conversation(messages=[])
    #                 ))
    #
    #     if len(chunks) == 1:
    #         # If the chunking didn't work, we try a different strategy.
    #         # Split the code into lines
    #         lines = program_code.strip().split('\n')
    #
    #         chunks = []
    #         current_chunk = None
    #         current_code = []
    #
    #         for line in lines:
    #             # Skip empty lines
    #             if not line.strip():
    #                 continue
    #
    #             # Check if line starts with a comment
    #             comment_match = re.match(r'^#\s*(\d+)\.\s*(.+)$', line)
    #             if comment_match:
    #                 # If we have a previous chunk with code, save it
    #                 if current_chunk and current_code:
    #                     current_chunk.code = '\n'.join(current_code).strip()
    #                     chunks.append(current_chunk)
    #
    #                 # Start a new chunk
    #                 number = int(comment_match.group(1))
    #                 comment_text = comment_match.group(2)
    #                 current_chunk = Program(
    #                     code='# '+comment_text,
    #                     conversation=Conversation(messages=[])
    #                 )
    #                 current_code = [line]
    #             elif current_chunk is not None:
    #                 # Add code line to current chunk
    #                 current_code.append(line)
    #
    #         # Add the last chunk if it exists and has code
    #         if current_chunk and current_code:
    #             current_chunk.code = '\n'.join(current_code).strip()
    #             chunks.append(current_chunk)
    #
    #     return chunks

    async def _evaluate_chunks(
        self, chunks: List[Program], start_state: GameState, instance_id: int
    ) -> Tuple[List[Program], List[List[Union[Entity, EntityGroup]]]]:
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
        try:
            vars = pickle.loads(current_state.namespaces[0])  # noqa
        except Exception:
            # This is good - the current state should be wiped.
            pass

        entity_list = []
        achievement_list = []

        try:
            # Initialize holdout instance
            # self.evaluator.holdout.reset(start_state)

            executed_chunks = []
            # Evaluate each chunk while tracking holdout
            for chunk in chunks:
                # Reset active instance to current state
                instance = self.evaluator.instances[instance_id]
                instance.reset(current_state)

                if self.evaluator.logger:
                    self.evaluator.logger.update_instance(
                        self.evaluator.instance_to_port[instance_id],
                        program_id=chunk.id,
                        status="executing",
                    )

                # Evaluate chunk
                (
                    reward,
                    state,
                    response,
                    entities,
                    achievements,
                    ticks,
                ) = await self.evaluator._evaluate_single(instance_id, chunk, instance)

                # Get holdout value after this chunk
                # holdout_score, _ = self.evaluator.holdout.score()
                # holdout_value = holdout_score - initial_holdout_value

                # Store results
                executed_chunks.append(chunk)
                achievement_list.append(achievements)
                entity_list.append(entities)
                # holdout_values.append(holdout_value)

                # Update chunk with results
                chunk.state = state
                chunk.value = reward
                chunk.advantage = reward
                chunk.response = response

                # Update state for next chunk
                current_state = state

                # if self.evaluator.logger:
                #     self.evaluator.logger.update_instance(
                #         self.evaluator.holdout.tcp_port,
                #         status="completed",
                #         current_reward=holdout_value
                #     )

                # If there was an error in the chunk, do not continue evaluating. We need to reflect on the issue
                # and determine how to proceed.
                if "error" in response.lower():
                    break

            return executed_chunks, entity_list, achievement_list

        except Exception as e:
            print("Error during chunk evaluation:")
            print(f"Instance ID: {instance_id}")
            print(f"Number of chunks: {len(chunks)}")
            print(f"Error: {str(e)}")
            import traceback

            traceback.print_exc()
            raise e

    async def search(
        self, n_iterations: int, samples_per_iteration: int, skip_failures: bool = False
    ):
        for iteration in range(n_iterations):
            await self.run_iteration(samples_per_iteration, skip_failures, iteration)
            self.evaluator.logger.update_progress()

    async def run_iteration(
        self, samples_per_iteration, skip_failures, iteration, n_iterations
    ):
        parent = await self.sampler.sample_parent(version=self.version)
        start_state = parent.state if parent else self.initial_state
        if not parent:
            self.evaluator.instances[0].reset(start_state)
            entities = self.evaluator.instances[0].get_entities()
            conversation = Conversation(
                messages=[
                    Message(role="system", content=self.system_prompt),
                    # Message(role="user", content=PLANNING_ADDITION_PROMPT),
                    Message(
                        role="assistant",
                        content="print(f'Inventory: {inspect_inventory()}')\n"
                        "print(f'Entities: {get_entities()}')\n",
                    ),
                    Message(
                        role="user",
                        content=f"1: ('Inventory: {start_state.inventories[0].__dict__}')\n"
                        f"2: ('Entities: {entities}')",
                    ),
                ]
            )
        else:
            conversation = parent.conversation

        # if len(conversation.messages) > (self.db.max_conversation_length*2)+1:
        #     difference = (len(conversation.messages) - ((self.db.max_conversation_length*2)+1)) // 2
        #     conversation.messages = conversation.messages[difference:]

        # verify that the system message exists
        if not any(msg.role == "system" for msg in conversation.messages):
            raise RuntimeError("System message has been lost somehow...")

        self.evaluator.set_sampling_status()
        self.evaluator.set_iteration(iteration, n_iterations)
        raw_programs = await self._generate_programs_batch(
            conversation, samples_per_iteration
        )

        # Process programs in parallel
        eval_futures = []
        for i, (program, chunks) in enumerate(raw_programs):
            instance_id = i % (len(self.evaluator.instances))
            self.evaluator.instances[instance_id].reset(start_state)
            self.evaluator.logger.update_instance(
                self.evaluator.instances[i].tcp_port,
                program_id=program.id,
                status="resetting",
                n_iterations=n_iterations,
            )

            # Create evaluation future for this program's chunks
            eval_futures.append(
                self._process_program_chunks(
                    program=program,
                    chunks=chunks,
                    start_state=start_state,
                    instance_id=instance_id,
                    parent_id=parent.id if parent else None,
                    skip_failures=skip_failures,
                )
            )

        # Wait for all programs to complete
        await asyncio.gather(*eval_futures)

        # Visit parent
        if parent:
            await self.sampler.visit(parent.id, len(eval_futures))

    async def _process_program_chunks(
        self,
        program: Program,
        chunks: List[Program],
        start_state: GameState,
        instance_id: int,
        parent_id: Optional[int],
        skip_failures: bool,
    ):
        """Process and evaluate a program's chunks with updated holdout calculation"""
        try:
            (
                evaluated_chunks,
                entity_list,
                achievement_list,
            ) = await self._evaluate_chunks(chunks, start_state, instance_id)

            last_chunk_id = parent_id
            last_conversation_stage = program.conversation

            depth = program.depth
            for chunk, entities, achievements in zip(
                evaluated_chunks, entity_list, achievement_list
            ):
                try:
                    chunk_program = Program(
                        code=chunk.code,
                        conversation=program.conversation,
                        value=chunk.value
                        - (
                            abs(self.error_penalty)
                            if "error" in chunk.response.lower()
                            else 0
                        ),  # Use per-chunk holdout value
                        raw_reward=chunk.value,
                        advantage=chunk.advantage
                        - (
                            abs(self.error_penalty)
                            if "error" in chunk.response.lower()
                            else 0
                        ),
                        holdout_value=0,
                        state=chunk.state,
                        response=chunk.response,
                        version=self.version,
                        version_description=self.version_description,
                        parent_id=last_chunk_id,
                        token_usage=program.token_usage // len(evaluated_chunks),
                        completion_token_usage=program.completion_token_usage
                        // len(evaluated_chunks),
                        prompt_token_usage=program.prompt_token_usage
                        // len(evaluated_chunks),
                        achievements=achievements,
                        instance=instance_id,
                        depth=depth + 2,
                    )
                    depth += 1

                    last_conversation_stage.add_result(
                        chunk.code,
                        chunk.response,
                        score=chunk.value,
                        advantage=chunk.value,
                    )

                    chunk_program.id = hash(
                        (
                            chunk.code,
                            json.dumps(
                                chunk_program.conversation.model_dump()["messages"]
                            ),
                        )
                    )
                    chunk_program.conversation = last_conversation_stage

                    if skip_failures and "error" in chunk.response.lower():
                        print("Skipping chunk due to error in response:")
                        print(f"Response: {chunk.response}")
                        break

                    created = await self.db.create_program(chunk_program)
                    last_chunk_id = created.id

                except Exception as e:
                    print("Error processing chunk:")
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

    async def _generate_programs_batch(
        self, conversation: Conversation, n_samples: int
    ) -> List[Tuple[Program, List[Program]]]:
        generation_parameters = GenerationParameters(
            n=n_samples,
            model=self.llm.model,
            logit_bias=self.logit_bias,
        )
        # We generate one extra program in case there is an error in parsing one. This way we can always return n_samples programs to keep the servers occupied.
        programs = (
            await super()._generate_programs_batch(
                conversation, generation_params=generation_parameters
            )
        )[:n_samples]
        chunked_programs = []

        for i, program in enumerate(programs):
            try:
                chunks = self._split_into_chunks(program.code)
                if not chunks:
                    chunks = [program]

                chunked_programs.append((program, chunks))

            except Exception as e:
                print(f"Failed to process chunks for program: {str(e)}")
                continue

        return chunked_programs
