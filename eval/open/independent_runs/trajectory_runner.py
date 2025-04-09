import asyncio
import argparse
from itertools import product
import os
import copy
from dataclasses import dataclass
from typing import Optional
import multiprocessing
from dotenv import load_dotenv

from agents import CompletionResult, CompletionReason
from agents.agent_abc import AgentABC
from agents.basic_agent import BasicAgent
from eval.open.db_client import PostgresDBClient, SQLliteDBClient
from eval.open.independent_runs.simple_evaluator import SimpleFactorioEvaluator
from models.conversation import Conversation
from models.message import Message
from models.game_state import GameState
from models.program import Program
from instance import FactorioInstance
from cluster.local.cluster_ips import get_local_container_ips
from agents.utils.python_parser import PythonParser
#from models.response import EnvironmentResponse
from namespace import FactorioNamespace

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
                 evaluators: list[SimpleFactorioEvaluator],
                 config: EvalConfig,
                 process_id: int):
        self.agents = agents
        self.db = db_client
        self.evaluators = evaluators
        self.config = config
        self.iteration_times = []
        self.process_id = process_id


    def _is_model_compatible_with_n_samples(self, model):
        """Check if model supports batch sampling"""
        return "gpt" in model or 'o1' in model or 'gemini' in model


    async def _generate_program(self, conversation: Conversation, response: Response, namespace: FactorioNamespace, meta={}, instance: int = -1) -> Program:
        conversation = copy.deepcopy(conversation)
        agent_idx = 0 if instance == -1 else instance
        try:
            policy = await self.agents[agent_idx].step(conversation, response, namespace)

            if not policy:
                raise Exception("Policy not valid Python. Skipping.")

            try:
                messages = conversation.model_dump()['messages']
            except Exception:
                messages = conversation.dict()['messages']

            program = Program(
                code=policy.code,
                conversation=conversation,
                response=response.response if response else None,
                token_usage=policy.meta.total_tokens,
                completion_token_usage=policy.meta.output_tokens,
                prompt_token_usage=policy.meta.input_tokens,
                version=self.config.version,
                instance=instance,
                model=self.agents[agent_idx].model,
                version_description=self.config.version_description,
                meta={"model": self.agents[agent_idx].model, "process_id": self.process_id},
                depth=len(messages) - 2
            )

            if meta:
                program.meta.update(meta)

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

    async def run(self):
        """Run a single trajectory"""
        # Initialize state based on resume or fresh start
        import time
        self.start_time = time.time()

        current_state = None
        current_conversations = [None] * len(self.agents)
        
        if self.config.version and len(self.agents) == 1:
            current_state, current_conversations[0], parent_id, depth = await self.db.get_resume_state(resume_version = self.config.version, process_id = self.process_id)
            self.agents[0].conversation = current_conversations[0]
        elif self.config.version and len(self.agents) > 1:
            for agent_idx in range(len(self.agents)):
                current_state, current_conversations[agent_idx], parent_id, depth = await self.db.get_resume_state(
                    resume_version = self.config.version, process_id = self.process_id, agent_idx = agent_idx
                )
                self.agents[agent_idx].conversation = current_conversations[agent_idx]
            
        if not current_state:
            current_state = self.config.task.starting_game_state
            depth = 0
            for agent_idx in range(len(self.agents)):
                self.evaluators[agent_idx].instance.reset(current_state)
                entities = self.evaluators[agent_idx].instance.namespace.get_entities()
                current_conversations[agent_idx] = Conversation(messages=[
                    Message(role="system", content=self.config.agents[agent_idx].system_prompt),
                    Message(role="assistant", content="print(f'Inventory: {inspect_inventory()}')\n"
                                                  "print(f'Entities: {get_entities()}')\n"),
                    Message(role="user", content=f"1: ('Inventory: {current_state.inventory.__dict__}')\n"
                                                f"2: ('Entities: {entities}')"),
                ])
                self.agents[agent_idx].conversation = current_conversations[agent_idx]
                parent_id = None

        last_response = None
        # Run trajectory
        for iteration, agent_idx in product(range(depth, self.config.task.trajectory_length), range(len(self.agents))):
            iteration_start = time.time()
            time.sleep(COURTESY_SLEEP) # courtesy sleep
            
            try:
                instance_param = -1 if len(self.agents) == 1 else agent_idx
                program = await self._generate_program(self.agents[agent_idx].conversation, last_response, self.evaluators[agent_idx].instance.namespace, instance=instance_param)

                print(f"Generated program {multiprocessing.current_process().name} - "
                      f"Model: {self.config.agents[agent_idx].model} - "
                      f"Iteration {iteration}/{self.config.task.trajectory_length}")

                if not program:
                    print(f"Program generation failed for agent {agent_idx} at iteration {iteration}")
                    continue

                program.parent_id = parent_id

                # Evaluate program
                instance = self.evaluators[agent_idx].instance
                instance.reset(current_state)
                evaluated_program, task_verification_response = await self.evaluators[agent_idx].evaluate(program, current_state, self.config.task)
                print(program.code + "\n"+"="*50)
                print("\033[1m\n".join(['>>>\t'+line for line in program.response.strip().replace('\\n', '\n\t').split('\n')]).strip()+"\033[0m")
                print(f"Evaluated program {multiprocessing.current_process().name} - "
                      f"Model: {self.config.agents[agent_idx].model} - "
                      f"Iteration {iteration}/{self.config.task.trajectory_length} - "
                      f"Agent #{agent_idx}")

                if not evaluated_program:
                    print(f"Evaluation failed for agent {agent_idx} at iteration {iteration}")
                    continue

                program = evaluated_program
                self.agents[agent_idx].conversation = program.conversation
                program.meta["task_key"] = self.config.task.task_key
                last_response = Response(
                    code=program.code,
                    created_at=program.created_at,
                    score=program.value,
                    achievements=program.achievements,
                    step=depth,
                    ticks = program.ticks,
                    flows = program.flows,
                    response=program.response,
                    task=task_verification_response
                )

                # Save program
                saved_program = await self.db.create_program(program)
                print(f"Saved program {multiprocessing.current_process().name} - "
                      f"Model: {self.config.agents[agent_idx].model} - "
                      f"Iteration {iteration}/{self.config.task.trajectory_length}")

                parent_id = saved_program.id

                # Update state for next iteration
                if program.state:
                    current_state = program.state
                    current_conversations[agent_idx] = program.conversation

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
                    
                if task_verification_response.success and self.config.exit_on_task_success:
                    print(f"Task verification success: {task_verification_response.success}")
                    completion_result = CompletionResult(step = iteration, 
                                                         reason = CompletionReason.SUCCESS)
                    for agent in self.agents:
                        await agent.end(program.conversation, completion_result)
                    break 
            except Exception as e:
                print(f"Error in iteration {iteration}: {e}")
                continue


def create_factorio_instance(instance_id: int, agent_idx: int = 0) -> FactorioInstance:
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
        player_index=agent_idx + 1  # +1 because lua is 1-indexed
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
    instances = []
    evaluators = []
    for agent_idx in range(len(config.agents)):
        instances.append(create_factorio_instance(process_id, agent_idx))
        evaluators.append(SimpleFactorioEvaluator(
            db_client=db_client,
            instance=instances[agent_idx],
            value_accrual_time=1,
            error_penalty=0
        ))

    # setup the instance
    task = config.task
    for instance in instances:
        task.setup(instance)
    runner = TrajectoryRunner(config.agents, db_client, evaluators, config, process_id)
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

