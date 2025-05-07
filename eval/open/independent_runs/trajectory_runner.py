import asyncio
import argparse
from itertools import product
import os
import copy
import time
from dataclasses import dataclass
from typing import Optional, Dict, List
import multiprocessing
from dotenv import load_dotenv

from agents import CompletionResult, CompletionReason
from agents.agent_abc import AgentABC
from agents.basic_agent import BasicAgent
from eval.open.db_client import PostgresDBClient, SQLliteDBClient
from eval.open.independent_runs.simple_evaluator import SimpleFactorioEvaluator
from env.src.models.conversation import Conversation
from env.src.models.message import Message
from env.src.models.game_state import GameState
from env.src.models.multiagent_game_state import MultiagentGameState
from env.src.models.program import Program
from env.src.instance import FactorioInstance
from cluster.local.cluster_ips import get_local_container_ips
from agents.utils.python_parser import PythonParser
#from models.response import EnvironmentResponse
from namespace import FactorioNamespace
from tools.agent.send_message.client import AgentMessage

from agents import Response
import json
from eval.tasks.task_abc import TaskABC
load_dotenv()

COURTESY_SLEEP = 5

@dataclass
class EvalConfig:
    """Configuration for evaluation"""
    agents: list[AgentABC]
    version: int
    version_description: str
    exit_on_task_success: bool
    task: Optional[TaskABC] = None

    def __post_init__(self):
        if self.task is None and hasattr(self.agents[0], 'task'):
            self.task = self.agents[0].task


class TrajectoryRunner:
    """Handles program generation and evaluation for a single trajectory"""

    def __init__(self,
                 #llm_factory: LLMFactory,
                 agents: list[AgentABC],
                 db_client: PostgresDBClient,
                 evaluator: SimpleFactorioEvaluator,
                 config: EvalConfig,
                 process_id: int):
        self.agents = agents
        self.db = db_client
        self.evaluator = evaluator
        self.config = config
        self.iteration_times = []
        self.process_id = process_id
        # Track messages for each agent
        self.agent_messages: Dict[int, List[AgentMessage]] = {i: [] for i in range(len(agents))}
        # Track the last timestamp we've shown for each agent
        self.last_message_timestamps: Dict[int, float] = {i: 0.0 for i in range(len(agents))}


    def _is_model_compatible_with_n_samples(self, model):
        """Check if model supports batch sampling"""
        return "gpt" in model or 'o1' in model or 'gemini' in model


    async def _generate_program(self, conversation: Conversation, response: Response, namespace: FactorioNamespace, meta={}, instance_param: int = -1) -> Program:
        conversation = copy.deepcopy(conversation)
        agent_idx = 0 if instance_param == -1 else instance_param
        try:
            policy, policy_meta = await self.agents[agent_idx].step(conversation, response, namespace)

            if not policy:
                raise Exception("Policy not valid Python. Skipping.")

            try:
                messages = policy.input_conversation.model_dump()['messages'] if policy.input_conversation else conversation.model_dump()['messages']
            except Exception:
                messages = policy.input_conversation.dict()['messages'] if policy.input_conversation else conversation.dict()['messages']

            program = Program(
                code=policy.code,
                conversation=policy.input_conversation if policy.input_conversation else conversation,
                response=response.response if response else None,
                token_usage=policy.meta.total_tokens,
                completion_token_usage=policy.meta.output_tokens,
                prompt_token_usage=policy.meta.input_tokens,
                version=self.config.version,
                instance=instance_param,  # used to denote agent index for multiagent runs
                model=self.agents[agent_idx].model,
                version_description=self.config.version_description,
                meta={"model": self.agents[agent_idx].model, "process_id": self.process_id},
                depth=len(messages) - 2
            )

            if meta:
                program.meta.update(meta)
            if policy_meta:
                program.meta.update(policy_meta)
            return program

        except Exception as e:
            print(f"Program generation failed: {str(e)}")
            return []

    def get_eta(self, current_iteration):
        """Calculate estimated time remaining"""
        if not self.iteration_times:
            return "calculating..."

        avg_iteration_time = sum(self.iteration_times) / len(self.iteration_times)
        remaining_iterations = self.config.task.trajectory_length - current_iteration
        seconds_remaining = avg_iteration_time * remaining_iterations

        # Convert to hours:minutes:seconds
        hours = int(seconds_remaining // 3600)
        minutes = int((seconds_remaining % 3600) // 60)
        seconds = int(seconds_remaining % 60)

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
    def _collect_new_messages(self, agent_idx: int) -> str:
        """Collect new messages for an agent and format them for display"""
        new_messages = []
        latest_timestamp = 0

        # Get new messages from the game state
        raw_messages = self.evaluator.instance.namespaces[agent_idx]._get_messages()
        for msg in raw_messages:
            # Create AgentMessage object and check if newer than last shown
            agent_msg = AgentMessage(
                sender=msg['sender'],
                recipient=msg['recipient'],
                content=msg['message'],
                timestamp=msg['timestamp']
            )
            if agent_msg.timestamp > self.last_message_timestamps[agent_idx]:
                new_messages.append(agent_msg)
                # Add to agent_messages collection
                self.agent_messages[agent_idx].append(agent_msg)
                latest_timestamp = max(latest_timestamp, agent_msg.timestamp)
                
        # Update the last timestamp
        if new_messages:
            self.last_message_timestamps[agent_idx] = latest_timestamp
            
        # Format messages for display
        if not new_messages:
            return ""
            
        formatted_messages = "\n\nMessages received:\n"
        for msg in new_messages:
            sender_info = f"Agent {msg.sender}" if msg.sender != 0 else "Leader"
            formatted_messages += f"[{sender_info}]: {msg.content}\n"
            
        return formatted_messages

    async def run(self):
        """Run a single trajectory"""
        # Initialize state based on resume or fresh start
        import time
        self.start_time = time.time()

        current_state = None
        current_conversations = [None] * len(self.agents)
        last_responses = [None] * len(self.agents)
        agent_step_budget = [self.config.task.trajectory_length] * len(self.agents)
        if self.config.version:
            for agent_idx in range(len(self.agents)):
                current_state, current_conversations[agent_idx], parent_id, depth = await self.db.get_resume_state(
                    resume_version = self.config.version, process_id = self.process_id, agent_idx = agent_idx
                )
            
        if not current_state:
            current_state = self.config.task.starting_game_state
            depth = 0
            self.evaluator.instance.reset(current_state)
            entities = self.evaluator.instance.first_namespace.get_entities()
            for agent_idx in range(len(self.agents)):
                if current_state.is_multiagent:
                    inventory = current_state.inventories[agent_idx]
                else:
                    inventory = current_state.inventory

                current_conversations[agent_idx] = Conversation(messages=[
                    Message(role="system", content=self.config.agents[agent_idx].system_prompt),
                    Message(role="assistant", content="```python\nprint(f'Inventory: {inspect_inventory()}')\n"
                                                  "print(f'Entities: {get_entities()}')\n```"),
                    Message(role="user", content=f"1: ('Inventory: {inventory.__dict__}')\n"
                                                f"2: ('Entities: {entities}')"),
                ])
                parent_id = None

        # Run trajectory
        for iteration, agent_idx in product(range(depth, self.config.task.trajectory_length), range(len(self.agents))):
            iteration_start = time.time()
            time.sleep(COURTESY_SLEEP) # courtesy sleep
            agent_completed = False
            try:
                # Collect new messages for this agent
                new_messages_text = self._collect_new_messages(agent_idx)
                
                # Update the conversation with new messages if any
                if new_messages_text:
                    # Get the last user message
                    last_user_message = None
                    for msg in reversed(current_conversations[agent_idx].messages):
                        if msg.role == "user":
                            last_user_message = msg
                            break
                    
                    if last_user_message:
                        # Append new messages to the last user message
                        last_user_message.content += new_messages_text
                
                instance_param = -1 if len(self.agents) == 1 else agent_idx
                # loop while the agent is not completed yet
                while not agent_completed and agent_step_budget[agent_idx] > 0:
                    program = await self._generate_program(current_conversations[agent_idx], last_responses[agent_idx], self.evaluator.instance.namespaces[agent_idx], instance_param=instance_param)
                    agent_step_budget[agent_idx] -= 1
                    print(f"Generated program {multiprocessing.current_process().name} - "
                          f"Model: {self.config.agents[agent_idx].model} - "
                          f"Iteration {iteration}/{self.config.task.trajectory_length}")

                    if not program:
                        print(f"Program generation failed for agent {agent_idx} at iteration {iteration}")
                        break

                    if not program.parent_id: program.parent_id = parent_id

                    # Evaluate program
                    if current_state.is_multiagent:
                        update_messages = [namespace._get_messages() for namespace in self.evaluator.instance.namespaces]
                        current_state.agent_messages = update_messages
                    self.evaluator.instance.reset(current_state)
                    instance_namespace_before_program = self.evaluator.instance.namespaces[agent_idx]
                    evaluated_program, task_verification_response = await self.evaluator.evaluate(program, current_state, self.config.task, agent_idx=agent_idx, step_statistics={"current_step_id": iteration})
                    print(program.code + "\n"+"="*50)
                    print("\033[1m\n".join(['>>>\t'+line for line in program.response.strip().replace('\\n', '\n\t').split('\n')]).strip()+"\033[0m")
                    print(f"Evaluated program {multiprocessing.current_process().name} - "
                          f"Model: {self.config.agents[agent_idx].model} - "
                          f"Iteration {iteration}/{self.config.task.trajectory_length} - "
                          f"Agent #{agent_idx}")

                    if not evaluated_program:
                        print(f"Evaluation failed for agent {agent_idx} at iteration {iteration}")
                        break

                    # Record iteration time
                    iteration_time = time.time() - iteration_start
                    self.iteration_times.append(iteration_time)

                    # Keep only last 50 iterations for moving average
                    if len(self.iteration_times) > 50:
                        self.iteration_times = self.iteration_times[-50:]

                    if iteration % 10 == 0:
                        elapsed = time.time() - self.start_time
                        elapsed_str = f"{int(elapsed // 3600):02d}:{int((elapsed % 3600) // 60):02d}:{int(elapsed % 60):02d}"
                        eta = self.get_eta(iteration)
                        print(f"\033[92m Process {multiprocessing.current_process().name} - "
                              f"Model: {self.config.agents[agent_idx].model} - "
                              f"Iteration {iteration}/{self.config.task.trajectory_length} - "
                              f"Value: {program.value:.2f} - "
                              f"Elapsed: {elapsed_str} - "
                              f"ETA: {eta}")

                    last_responses[agent_idx] = Response(
                        code=f"```python\n{evaluated_program.code}\n```",
                        created_at=evaluated_program.created_at,
                        score=evaluated_program.value,
                        achievements=evaluated_program.achievements,
                        step=depth,
                        ticks = evaluated_program.ticks,
                        flows = evaluated_program.flows,
                        response=evaluated_program.response,
                        task=task_verification_response,
                        error=evaluated_program.meta.get("error_occurred", False),
                        program_id=evaluated_program.id,
                    )

                    # get the agent_completed flag from the agent
                    agent_completed, update_state = self.agents[agent_idx].check_completion(last_responses[agent_idx])
                    if not update_state:
                        self.evaluator.instance.namespaces[agent_idx] = instance_namespace_before_program
                    else:
                        current_state = program.state


                    program = evaluated_program
                    program.meta["task_key"] = self.config.agent.task.task_key

                    # Save program
                    saved_program = await self.db.create_program(program)
                    print(f"Saved program {multiprocessing.current_process().name} - "
                          f"Model: {self.config.agents[agent_idx].model} - "
                          f"Iteration {iteration}/{self.config.agent.task.trajectory_length}")

                    parent_id = saved_program.id
                    last_responses[agent_idx].program_id = saved_program.id
                    # Update state for next iteration
                    if program.state:
                        # add the last 2 messages from program.conversation to the current conversation
                        current_conversations[agent_idx].messages.extend(program.conversation.messages[-2:])

                    if task_verification_response.success and self.config.exit_on_task_success:
                        print(f"Task verification success: {task_verification_response.success}")
                        completion_result = CompletionResult(step = iteration, 
                                                             reason = CompletionReason.SUCCESS)
                        for agent in self.agents:
                            await agent.end(program.conversation, completion_result)
                        # exit the loop
                        return 
            except Exception as e:
                print(f"Error in iteration {iteration}: {e}")
                continue


def create_factorio_instance(instance_id: int, num_agents: int = 1) -> FactorioInstance:
    """Create a single Factorio instance"""
    ips, udp_ports, tcp_ports = get_local_container_ips()

    instance = FactorioInstance(
        address=ips[instance_id],
        tcp_port=tcp_ports[instance_id],
        bounding_box=200,
        fast=True,
        cache_scripts=True,
        inventory={},
        all_technologies_researched=True,
        num_agents=num_agents
    )
    instance.speed(10)
    return instance


async def create_db_client() -> PostgresDBClient:
    """Create database client with connection pool"""
    return PostgresDBClient(
        max_conversation_length=40,
        min_connections=2,
        max_connections=5,
        host=os.getenv("SKILLS_DB_HOST"),
        port=os.getenv("SKILLS_DB_PORT"),
        dbname=os.getenv("SKILLS_DB_NAME"),
        user=os.getenv("SKILLS_DB_USER"),
        password=os.getenv("SKILLS_DB_PASSWORD")
    )


async def run_trajectory(process_id: int, config: EvalConfig):
    """Entry point for running a single trajectory"""
    # Initialize components
    db_client = await create_db_client()
    #llm_factory = LLMFactory(model=config.model)
    instance = create_factorio_instance(process_id, len(config.agents))
    evaluator = SimpleFactorioEvaluator(
        db_client=db_client,
        instance=instance,
        value_accrual_time=1,
        error_penalty=0
    )

    # setup the instance
    task = config.task
    task.setup(instance)
    runner = TrajectoryRunner(config.agents, db_client, evaluator, config, process_id)
    
    await runner.run()
    await db_client.cleanup()


def run_process(process_id: int, config: EvalConfig):
    """Process entry point"""
    asyncio.run(run_trajectory(process_id, config))


async def get_next_version() -> int:
    """Get next available version number"""
    db_client = await create_db_client()
    version = await db_client.get_largest_version()
    await db_client.cleanup()
    return version + 1

