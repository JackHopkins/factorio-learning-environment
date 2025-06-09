import asyncio
from itertools import product
import time
import os
import json
import multiprocessing
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass

from agents.agent_abc import AgentABC
from agents.gym_agent import GymAgent
from agents import Policy, CompletionResult, CompletionReason
from env.src.models.program import Program
from env.src.models.game_state import GameState
from env.src.models.conversation import Conversation
from env.src.models.message import Message
from env.src.instance import FactorioInstance
from env.src.gym_env.environment import FactorioGymEnv
from env.src.gym_env.observation import Observation
from eval.tasks.task_abc import TaskABC
from eval.open.db_client import PostgresDBClient
from a2a.types import AgentCard

@dataclass
class GymEvalConfig:
    """Configuration for gym evaluation"""
    agents: List[GymAgent]
    version: int
    version_description: str
    exit_on_task_success: bool
    task: Optional[TaskABC] = None
    agent_cards: Optional[List[AgentCard]] = None

    def __post_init__(self):
        if self.task is None and hasattr(self.agents[0], 'task'):
            self.task = self.agents[0].task

class GymTrajectoryRunner:
    """Handles program generation and evaluation for a single trajectory in the gym environment"""

    def __init__(self,
                 config: GymEvalConfig,
                 instance: FactorioInstance,
                 process_id: int,
                 db_client: Optional[PostgresDBClient],
                 value_accrual_time: float = 1.0,
                 error_penalty: float = 0.0):
        self.config = config
        self.agents = config.agents
        self.instance = instance
        self.db_client = db_client
        self.gym_env = FactorioGymEnv(
            instance,
            task=config.task,
            value_accrual_time=value_accrual_time,
            error_penalty=error_penalty
        )
        self.process_id = process_id
        self.iteration_times = []

    def get_eta(self, current_iteration: int) -> str:
        """Calculate estimated time remaining"""
        if not self.iteration_times:
            return "calculating..."

        self.iteration_times = self.iteration_times[-50:]
        avg_iteration_time = sum(self.iteration_times) / len(self.iteration_times)
        remaining_iterations = self.config.task.trajectory_length - current_iteration
        seconds_remaining = avg_iteration_time * remaining_iterations

        # Convert to hours:minutes:seconds
        hours = int(seconds_remaining // 3600)
        minutes = int((seconds_remaining % 3600) // 60)
        seconds = int(seconds_remaining % 60)

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def _log_progress(self, agent: GymAgent, iteration: int, program_value: float):
        """Log progress of the trajectory run"""
        elapsed = time.time() - self.start_time
        elapsed_str = f"{int(elapsed // 3600):02d}:{int((elapsed % 3600) // 60):02d}:{int(elapsed % 60):02d}"
        eta = self.get_eta(iteration)
        print(f"\033[92m Process {multiprocessing.current_process().name} - "
              f"Model: {agent.model} - "
              f"Iteration {iteration}/{self.config.task.trajectory_length} - "
              f"Value: {program_value:.2f} - "
              f"Elapsed: {elapsed_str} - "
              f"ETA: {eta}\033[0m")

    def _log_observation_and_program(self, agent: GymAgent, agent_idx: int, iteration: int, observation: Observation, program: Program, log_dir: str):
        """Log observation and program to console and files
        
        Args:
            agent: The agent instance
            agent_idx: Index of the agent
            iteration: Current iteration number
            observation: The observation to log
            program: The program to log
            log_dir: Directory to save the log files
        """
        # Log observation
        formatted_obs = agent.observation_formatter.format(observation).raw_str
        print(f"\nObservation for agent {agent_idx} at iteration {iteration}:")
        print(formatted_obs)
        
        obs_file = os.path.join(log_dir, f"agent{agent_idx}_iter{iteration}_observation.txt")
        with open(obs_file, 'w') as f:
            f.write(formatted_obs)
        
        # Log program
        print(f"\nProgram for agent {agent_idx} at iteration {iteration}:")
        print(program.code)
        
        prog_file = os.path.join(log_dir, f"agent{agent_idx}_iter{iteration}_program.py")
        with open(prog_file, 'w') as f:
            f.write(program.code)

    async def create_program_from_policy(self, policy, agent_idx: int, reward: float, response: str, error_occurred: bool) -> Program:
        """Create a Program object from a Policy and environment results
        
        Args:
            policy: The Policy object to convert
            agent_idx: Index of the agent in the multi-agent setup
            reward: The reward from the environment step
            response: The raw text response from the environment
            error_occurred: Whether an error occurred during execution
            
        Returns:
            Program object with all necessary metadata and results
        """
        messages = policy.input_conversation.model_dump()['messages']
        depth = len(messages) - 2
        game_state = GameState.from_instance(self.instance)
        
        # Create program from policy with environment results
        program = Program(
            code=policy.code,
            conversation=policy.input_conversation,
            response=response,
            token_usage=policy.meta.total_tokens,
            completion_token_usage=policy.meta.output_tokens,
            prompt_token_usage=policy.meta.input_tokens,
            version=self.config.version,
            instance=agent_idx,
            model=self.agents[agent_idx].model,
            version_description=self.config.version_description,
            value=reward,
            state=game_state,
            meta={
                "model": self.agents[agent_idx].model,
                "process_id": self.process_id,
                "error_occurred": error_occurred
            },
            depth=depth
        )
        if self.config.version and self.db_client is not None:
            saved_program = await self.db_client.create_program(program)
            program.id = saved_program.id

        return program

    async def run(self):
        """Run a single trajectory"""
        self.start_time = time.time()
        
        # Create version-specific directory for logging
        log_dir = f"trajectory_logs_v{self.config.version}"
        os.makedirs(log_dir, exist_ok=True)
        
        # Initialize state based on resume or fresh start
        current_state = None
        current_conversations = [None] * len(self.agents)
        agent_steps = [0] * len(self.agents)
        
        if self.config.version and self.db_client is not None:
            for agent_idx in range(len(self.agents)):
                current_state, current_conversations[agent_idx], parent_id, depth = await self.db_client.get_resume_state(
                    resume_version=self.config.version, process_id=self.process_id, agent_idx=agent_idx
                )
                agent_steps[agent_idx] = depth if depth is not None else 0
        
        if not current_state:
            current_state = self.config.task.starting_game_state
            self.gym_env.reset(current_state)
            
            # Initialize agent conversations
            for agent_idx, agent in enumerate(self.agents):
                agent.reset(self.gym_env.get_observation(agent_idx))
        
        # Run trajectory
        for iteration, agent_idx in product(range(self.config.task.trajectory_length), range(len(self.agents))):
            agent = self.agents[agent_idx]
            iteration_start = time.time()
            agent_completed = False
            try:
                # Loop while the agent is not completed yet
                while not agent_completed and agent_steps[agent_idx] < self.config.task.trajectory_length:
                    # Generate policy using agent's method
                    policy = await agent.generate_policy()
                    agent_steps[agent_idx] += 1
                    if not policy:
                        print(f"Policy generation failed for agent {agent_idx} at iteration {agent_steps[agent_idx]}")
                        break

                    # Execute step in the environment
                    self.gym_env.reset_instance(current_state)
                    observation_dict, reward, done, info = self.gym_env.step({
                        'agent_idx': agent_idx,
                        'code': policy.code
                    })

                    # Create program from policy with environment results
                    program = await self.create_program_from_policy(
                        policy=policy,
                        agent_idx=agent_idx,
                        reward=reward,
                        response=observation_dict['raw_text'],
                        error_occurred=info.get('error_occurred', False)
                    )

                    # Record iteration time
                    iteration_time = time.time() - iteration_start
                    self.iteration_times.append(iteration_time)

                    if agent_steps[agent_idx] % 10 == 0:
                        self._log_progress(agent, agent_steps[agent_idx], program.value)

                    # Update agent's conversation with the program and its results
                    observation = Observation.from_dict(observation_dict)
                    await agent.update_conversation(program, observation)

                    # Log observation and program
                    self._log_observation_and_program(agent, agent_idx, agent_steps[agent_idx], observation, program, log_dir)

                    # Get the agent_completed flag from the agent
                    agent_completed, update_state = agent.check_completion(observation)
                    if update_state:
                        current_state = program.state

                    # Check if done and exit if configured
                    if done and self.config.exit_on_task_success:
                        completion_result = CompletionResult(step=agent_steps[agent_idx], 
                                                           reason=CompletionReason.SUCCESS)
                        for agent in self.agents:
                            await agent.end(agent.get_conversation(), completion_result)
                        return
                        
            except Exception as e:
                print(f"Error in iteration {agent_steps[agent_idx]}: {e}")
                continue
