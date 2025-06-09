import asyncio
import time
import os
import json
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass

from agents.agent_abc import AgentABC
from agents.gym_agent import GymAgent
from env.src.models.program import Program
from env.src.models.game_state import GameState
from env.src.instance import FactorioInstance
from env.src.gym_env.environment import FactorioGymEnv
from env.src.gym_env.observation import Observation
from eval.tasks.task_abc import TaskABC
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
                 value_accrual_time: float = 1.0,
                 error_penalty: float = 0.0):
        self.config = config
        self.agents = config.agents
        self.instance = instance
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
        print(f"Process {self.process_id} - "
              f"Model: {agent.model} - "
              f"Iteration {iteration}/{self.config.task.trajectory_length} - "
              f"Value: {program_value:.2f} - "
              f"Elapsed: {elapsed_str} - "
              f"ETA: {eta}")

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

    async def run(self):
        """Run a single trajectory"""
        self.start_time = time.time()
        
        # Create version-specific directory for logging
        log_dir = f"trajectory_logs_v{self.config.version}"
        os.makedirs(log_dir, exist_ok=True)
        
        # Initialize state
        current_state = self.config.task.starting_game_state
        self.gym_env.reset(current_state)
        
        # Initialize agent conversations
        for agent_idx, agent in enumerate(self.agents):
            agent.reset(self.gym_env.get_observation(agent_idx))
        
        # Run trajectory
        for iteration in range(self.config.task.trajectory_length):
            for agent_idx, agent in enumerate(self.agents):
                iteration_start = time.time()
                #try:
                # Generate program using agent's method
                program = await agent.generate_program(
                    agent_idx,
                    self.config.version,
                    self.config.version_description,
                    self.process_id
                )
                
                if not program:
                    continue
                
                # Execute step in the environment
                self.gym_env.reset_instance(current_state)
                observation_dict, reward, done, info = self.gym_env.step({
                    'agent_idx': agent_idx,
                    'code': program.code
                })
                
                # Update program with results
                program.value = reward
                program.state = current_state = GameState.from_instance(self.instance)
                program.meta["error_occurred"] = info.get('error_occurred', False)
                
                # Update agent's conversation with the program and its results
                observation = Observation.from_dict(observation_dict)
                await agent.update_conversation(program, observation)
                self.iteration_times.append(time.time() - iteration_start)

                # Log observation and program
                self._log_observation_and_program(agent, agent_idx, iteration, observation, program, log_dir)
                
                if iteration % 10 == 0:
                    self._log_progress(agent, iteration, program.value)
                
                # Check if done and exit if configured
                if done and self.config.exit_on_task_success:
                    print("Task completed successfully!")
                    return
                
                #except Exception as e:
                #    print(f"Error in iteration {iteration}: {e}")
                #    continue
