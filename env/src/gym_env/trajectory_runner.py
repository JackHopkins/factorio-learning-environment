import asyncio
import time
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass

from agents.agent_abc import AgentABC
from agents.gym_agent import GymAgent
from env.src.models.program import Program
from env.src.models.game_state import GameState
from env.src.instance import FactorioInstance
from env.src.gym_env.environment import FactorioGymEnv
from env.src.gym_env.observation import Observation, BasicObservationFormatter
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
                 agents: List[GymAgent],
                 instance: FactorioInstance,
                 config: GymEvalConfig,
                 process_id: int,
                 value_accrual_time: float = 1.0,
                 error_penalty: float = 0.0):
        self.agents = agents
        self.instance = instance
        self.gym_env = FactorioGymEnv(
            instance,
            task=config.task,
            value_accrual_time=value_accrual_time,
            error_penalty=error_penalty
        )
        self.config = config
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

    async def run(self):
        """Run a single trajectory"""
        self.start_time = time.time()
        
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
                print(f"Starting iteration at {iteration_start}")
                
                # try:
                # Get observation from environment
                print("Getting observation from environment...")
                observation_dict = self.gym_env.get_observation(agent_idx)
                print(f"Got observation for agent {agent_idx}")
                
                # Generate program using agent's method
                print("Generating program...")
                program = await agent.generate_program(
                    agent_idx,
                    self.config.version,
                    self.config.version_description,
                    self.process_id
                )
                print("Program generation complete")
                
                if not program:
                    print("No valid program generated, continuing to next iteration")
                    continue
                
                # Execute step in the environment
                print("Resetting instance and executing step...")
                self.gym_env.reset_instance(current_state)
                observation_dict, reward, done, info = self.gym_env.step({
                    'agent_idx': agent_idx,
                    'code': program.code
                })
                print(f"Step executed with reward: {reward}")
                
                # Update program with results
                print("Updating program state...")
                program.value = reward
                program.state = current_state = GameState.from_instance(self.instance)
                program.meta["error_occurred"] = info.get('error_occurred', False)
                print(f"Program state updated, error occurred: {program.meta['error_occurred']}")
                
                # Update agent's conversation with the program and its results
                print("Updating agent conversation...")
                observation = Observation.from_dict(observation_dict)
                await agent.update_conversation(program, observation)
                self.iteration_times.append(time.time() - iteration_start)
                print("Agent conversation updated")
                
                if iteration % 10 == 0:
                    self._log_progress(agent, iteration, program.value)
                    print("Progress logged")
                
                # Check if done and exit if configured
                if done and self.config.exit_on_task_success:
                    print("Task completed successfully!")
                    return
                
                # except Exception as e:
                #     print(f"Error in iteration {iteration}: {e}")
                #     continue
