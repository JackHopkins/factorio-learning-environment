import os
import time
from itertools import product
from typing import Any, List, Dict, Optional, Tuple

from fle.agents import CompletionReason, CompletionResult
from fle.agents.gym_agent import GymAgent
from fle.commons.db_client import DBClient
from fle.commons.models.conversation import Conversation
from fle.commons.models.game_state import GameState
from fle.commons.models.program import Program

from fle.env.gym_env.action import Action
from fle.env.gym_env.config import GymEvalConfig
from fle.env.gym_env.environment import FactorioGymEnv
from fle.env.gym_env.observation import Observation
from fle.env.gym_env.trajectory_logger import TrajectoryLogger

try:
    from fle.eval.analysis import WandBLogger

    WANDB_ANALYSIS_AVAILABLE = True
except ImportError:
    WANDB_ANALYSIS_AVAILABLE = False


class GymTrajectoryRunner:
    """Handles program generation and evaluation for a single trajectory in the gym environment"""

    def __init__(
        self,
        config: GymEvalConfig,
        gym_env: FactorioGymEnv,
        process_id: int,
        db_client: Optional[DBClient],
        log_dir: Optional[str] = None,
        reset_states: bool = False,
        wandb_logger: Optional["WandBLogger"] = None,
    ):
        self.config = config
        self.agents = config.agents
        self.gym_env = gym_env
        self.instance = gym_env.unwrapped.instance  # Get instance from gym environment
        self.db_client = db_client
        self.process_id = process_id
        self.start_time = time.time()
        self.reset_states = reset_states  # Whether to reset the state after each step
        self.wandb_logger = wandb_logger

        # Initialize trajectory logger
        self.logger = TrajectoryLogger(
            start_time=self.start_time,
            trajectory_length=self.config.task.trajectory_length,
            log_dir=log_dir,
        )

    def _log_trajectory_state(
        self,
        iteration_start: float,
        agent: GymAgent,
        agent_idx: int,
        agent_step: int,
        production_score: float,
        program: Program,
        observation: Observation,
    ):
        """Consolidate all trajectory logging operations

        Args:
            iteration_start: Start time of the iteration
            agent: The agent instance
            agent_idx: Index of the agent
            agent_step: Current step for this agent
            production_score: Current production score
            program: The program to log
            observation: The observation to log
        """
        # Record iteration time
        iteration_time = time.time() - iteration_start
        self.logger.add_iteration_time(iteration_time)

        # Log progress, observation and program
        self.logger.log_progress(agent, agent_step, program.value, production_score)
        self.logger.log_observation_and_program(
            agent, agent_idx, agent_step, observation, program
        )

        # Log to WandB if available
        if self.wandb_logger and WANDB_ANALYSIS_AVAILABLE:
            try:
                # Extract task name from version description
                task_name = "unknown_task"
                if (
                    self.config.version_description
                    and "type:" in self.config.version_description
                ):
                    task_name = (
                        self.config.version_description.split("type:")[1]
                        .split("\n")[0]
                        .strip()
                    )

                elapsed_time = time.time() - self.start_time

                self.wandb_logger.log_trajectory_progress(
                    version=self.config.version,
                    instance=self.process_id,
                    step=agent_step,
                    reward=program.value,
                    production_score=production_score,
                    model=agent.model,
                    task=task_name,
                    elapsed_time=elapsed_time,
                    tokens_used=program.token_usage,
                )

            except Exception as e:
                print(f"Warning: Failed to log to WandB: {e}")

    async def create_program_from_policy(
        self,
        policy,
        agent_idx: int,
        reward: float,
        response: str,
        error_occurred: bool,
        achievements: Dict[str, Any],
        game_state: GameState,
    ) -> Program:
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
        messages = policy.input_conversation.model_dump()["messages"]
        depth = len(messages) - 2

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
            achievements=achievements,
            meta={
                "model": self.agents[agent_idx].model,
                "process_id": self.process_id,
                "error_occurred": error_occurred,
                "sweep_id": os.getenv("FLE_SWEEP_ID", "unknown"),
            },
            depth=depth,
        )
        if self.config.version and self.db_client is not None:
            saved_program = await self.db_client.create_program(program)
            program.id = saved_program.id

        return program

    async def _initialize_trajectory_state(self) -> Tuple[GameState, List[int]]:
        """Initialize trajectory state, either from resume or fresh start

        Returns:
            Tuple of (current_state, agent_steps)
        """
        current_state = None
        agent_steps = [0] * len(self.agents)

        if self.config.version and self.db_client is not None:
            for agent_idx in range(len(self.agents)):
                (
                    current_state,
                    agent_conversation,
                    parent_id,
                    depth,
                ) = await self.db_client.get_resume_state(
                    resume_version=self.config.version,
                    process_id=self.process_id,
                    agent_idx=agent_idx,
                )
                if current_state:
                    agent_steps[agent_idx] = depth
                    self.agents[agent_idx].reset(agent_conversation)

        if not current_state:
            current_state = self.config.task.starting_game_state

        self.gym_env.reset(options={"game_state": current_state})
        # Initialize agent conversations
        for agent_idx, agent in enumerate(self.agents):
            conversation = Conversation()
            initial_obs = self.gym_env.unwrapped.get_observation(agent_idx)
            formatted_obs = agent.observation_formatter.format(initial_obs).raw_str
            conversation.add_user_message(formatted_obs)
            agent.reset(conversation)

        return current_state, agent_steps

    async def run(self):
        """Run a single trajectory"""

        # Initialize state based on resume or fresh start
        max_steps = self.config.task.trajectory_length
        current_state, agent_steps = await self._initialize_trajectory_state()

        # Save system prompts for all agents at the start
        for agent_idx, agent in enumerate(self.agents):
            self.logger.save_system_prompt(agent, agent_idx)

        # Run trajectory
        for _, agent_idx in product(range(max_steps), range(len(self.agents))):
            agent = self.agents[agent_idx]
            iteration_start = time.time()
            agent_completed = False
            try:
                # Loop while the agent is not completed yet
                while not agent_completed and agent_steps[agent_idx] < max_steps:
                    # Generate policy using agent's method
                    policy = await agent.generate_policy()
                    agent_steps[agent_idx] += 1
                    if not policy:
                        print(
                            f"Policy generation failed for agent {agent_idx} at iteration {agent_steps[agent_idx]}"
                        )
                        break

                    # Execute step in the environment
                    action = Action(
                        code=policy.code,
                        agent_idx=agent_idx,
                        game_state=current_state if self.reset_states else None,
                    )
                    obs_dict, reward, terminated, truncated, info = self.gym_env.step(
                        action
                    )
                    observation = Observation.from_dict(obs_dict)
                    output_game_state = info["output_game_state"]
                    production_score = info["production_score"]
                    done = terminated or truncated

                    # Create program from policy with environment results
                    program = await self.create_program_from_policy(
                        policy=policy,
                        agent_idx=agent_idx,
                        reward=reward,
                        response=obs_dict["raw_text"],
                        error_occurred=info["error_occurred"],
                        achievements=info["achievements"],
                        game_state=output_game_state,
                    )

                    # Update agent's conversation with the program and its results
                    await agent.update_conversation(
                        observation, previous_program=program
                    )

                    # Consolidate all trajectory logging operations
                    self._log_trajectory_state(
                        iteration_start,
                        agent,
                        agent_idx,
                        agent_steps[agent_idx],
                        production_score,
                        program,
                        observation,
                    )

                    # Get the agent_completed flag from the agent
                    if self.reset_states:
                        agent_completed, update_state = agent.check_step_completion(
                            observation
                        )
                        if update_state:
                            current_state = output_game_state

                    # Check if done and exit if configured
                    if done:
                        completion_result = CompletionResult(
                            step=agent_steps[agent_idx], reason=CompletionReason.SUCCESS
                        )
                        for agent in self.agents:
                            await agent.end(completion_result)
                        return

            except Exception as e:
                print(
                    f"Error in trajectory runner iteration {agent_steps[agent_idx]}: {e}"
                )
                continue
