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

@dataclass
class GymEvalConfig:
    """Configuration for gym evaluation"""
    agents: List[GymAgent]
    version: int
    version_description: str
    exit_on_task_success: bool
    task: Optional[TaskABC] = None

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
        self.formatter = BasicObservationFormatter()

    async def run(self):
        """Run a single trajectory"""
        self.start_time = time.time()
        
        # Initialize state
        current_state = self.config.task.starting_game_state
        self.gym_env.reset_instance(current_state)
        
        # Initialize agent conversations
        for agent in self.agents:
            agent.conversation = agent.create_initial_conversation()
        
        # Run trajectory
        for iteration in range(self.config.task.trajectory_length):
            for agent_idx, agent in enumerate(self.agents):
                iteration_start = time.time()
                
                try:
                    # Get observation from environment
                    observation_dict = self.gym_env._get_observation(agent_idx)
                    
                    # Generate program using agent's method
                    program = await agent.generate_program(
                        observation_dict,
                        agent_idx,
                        self.config.version,
                        self.config.version_description,
                        self.process_id
                    )
                    
                    if not program:
                        print(f"Program generation failed for agent {agent_idx} at iteration {iteration}")
                        continue
                    
                    # Execute step in the environment
                    observation_dict, reward, done, info = self.gym_env.step({
                        'agent_idx': agent_idx,
                        'code': program.code
                    })
                    
                    # Update program with results
                    program.value = reward
                    program.state = GameState.from_instance(self.instance)
                    program.meta["error_occurred"] = info.get('error_occurred', False)
                    
                    # Format the observation for the agent's conversation
                    observation = Observation.from_dict(observation_dict)
                    formatted_obs = self.formatter.format(observation)
                    
                    # Update agent's conversation with the program and its results
                    agent.conversation.add_result(
                        program=program.code,
                        response=formatted_obs.raw_str,
                    )
                    
                    # Record iteration time
                    iteration_time = time.time() - iteration_start
                    self.iteration_times.append(iteration_time)
                    
                    # Keep only last 50 iterations for moving average
                    if len(self.iteration_times) > 50:
                        self.iteration_times = self.iteration_times[-50:]
                    
                    # Print progress
                    if iteration % 10 == 0:
                        elapsed = time.time() - self.start_time
                        elapsed_str = f"{int(elapsed // 3600):02d}:{int((elapsed % 3600) // 60):02d}:{int(elapsed % 60):02d}"
                        print(f"Process {self.process_id} - "
                              f"Model: {agent.model} - "
                              f"Iteration {iteration}/{self.config.task.trajectory_length} - "
                              f"Value: {program.value:.2f} - "
                              f"Elapsed: {elapsed_str}")
                    
                    # Check if done and exit if configured
                    if done and self.config.exit_on_task_success:
                        print("Task completed successfully!")
                        return
                
                except Exception as e:
                    print(f"Error in iteration {iteration}: {e}")
                    continue
