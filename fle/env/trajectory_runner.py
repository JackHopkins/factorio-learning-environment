import time
from itertools import product
from typing import Dict, List, Optional, Tuple

from fle.agents import CompletionReason, CompletionResult
from fle.agents.gym_agent import GymAgent
from fle.commons.models.conversation import Conversation
from fle.commons.models.program import Program
from fle.env.environment import FactorioGymEnv
from fle.env.game.game_state import GameState
from fle.env.gym_env.config import GymEvalConfig
from fle.env.gym_env.trajectory_logger import TrajectoryLogger
from fle.env.models.action import Action
from fle.env.models.observation import Observation
from fle.env.session import GameSession, AgentSession
from fle.env.session_manager import GameSessionManager


class GymTrajectoryRunner:
    """Handles program generation and evaluation for a single trajectory in the gym environment"""

    config: GymEvalConfig
    gym_env: FactorioGymEnv
    process_id: int
    agents: Dict[int, GymAgent]

    def __init__(
        self,
        config: GymEvalConfig,
        gym_env: FactorioGymEnv,
        process_id: int,
        log_dir: Optional[str] = None,
    ):
        self.config = config
        self.agents = config.agents
        self.gym_env = gym_env
        self.process_id = process_id
        self.start_time = time.time()
        self.logger = TrajectoryLogger(
            start_time=self.start_time,
            trajectory_length=self.config.task.trajectory_length,
            log_dir=log_dir,
        )
        self.max_steps = self.config.task.trajectory_length

    def _log_trajectory_state(
        self,
        iteration_start: float,
        agent: GymAgent,
        agent_idx: int,
        agent_step: int,
        program: Program,
        observation: Observation,
    ):
        """Consolidate all trajectory logging operations

        Args:
            iteration_start: Start time of the iteration
            agent: The agent instance
            agent_idx: Index of the agent
            agent_step: Current step for this agent
            program: The program to log
            observation: The observation to log
        """
        # Record iteration time
        iteration_time = time.time() - iteration_start
        self.logger.add_iteration_time(iteration_time)

        # Log progress every 10 steps
        if agent_step % 10 == 0:
            self.logger.log_progress(agent, agent_step, program.value)

        # Log observation and program
        self.logger.log_observation_and_program(
            agent, agent_idx, agent_step, observation, program
        )

    async def _initialize_trajectory_state(self) -> Tuple[GameState, List[int]]:
        """Initialize trajectory state, either from resume or fresh start

        Returns:
            Tuple of (current_state, agent_steps)
        """
        game_session = self.gym_env.game_session
        await game_session.initialise()
        first_idx = list(game_session.agent_sessions.keys())[0]
        current_state, agent_conversation = (
            await game_session.get_agent_session_resume_state(first_idx, self.process_id)
        )
        if agent_conversation:
            self.agents[first_idx].reset(agent_conversation)

        self.gym_env.reset(options={"game_state": current_state})
        # Initialize agent conversations
        for agent_idx in self.agents:
            agent = self.agents[agent_idx]
            agent_session = game_session.agent_sessions[agent_idx]
            conversation = Conversation()
            initial_obs = agent_session.get_partial_observation(
                game_session.current_game_info
            )
            formatted_obs = agent.observation_formatter.format(initial_obs).raw_str
            conversation.add_user_message(formatted_obs)
            agent.reset(conversation)

        return current_state

    async def _run_trajectory_step(self, agent: GymAgent, agent_session: AgentSession, current_state: GameState):
        iteration_start = time.time()
        agent_idx = agent_session.agent_idx
        # Loop while the agent is not completed yet
        while not agent.agent_completed and agent_session.steps < self.max_steps:
            # Generate policy using agent's method
            policy = await agent.generate_policy()
            agent_session.steps += 1
            if not policy:
                print(
                    f"Policy generation failed for agent {agent_idx} at iteration {agent_session.steps}"
                )
                break

            # Execute step in the environment
            action = Action(agent_idx=agent_idx, code=policy.code, game_state=current_state)
            obs_dict, reward, terminated, truncated, info = self.gym_env.step(action)
            observation = Observation.from_dict(obs_dict)
            output_game_state: GameState = info["output_game_state"]
            done = terminated or truncated

            # Create program from policy with environment results
            program = Program.from_policy(
                agent_idx=agent_idx,
                policy=policy,
                reward=reward,
                response=obs_dict["raw_text"],
                error_occurred=info["error_occurred"],
                game_state=output_game_state,
                process_id=self.process_id,
                model=agent.model,
                version=agent_session.version,
                version_description=agent_session.version_description,
            )

            program = await agent_session.save_program(program)

            # Update agent's conversation with the program and its results
            await agent.update_conversation(observation, previous_program=program)

            # Consolidate all trajectory logging operations
            self._log_trajectory_state(
                iteration_start,
                agent,
                agent_idx,
                agent_session.steps,
                program,
                observation,
            )

            # Get the agent_completed flag from the agent
            agent.agent_completed, update_state = agent.check_step_completion(
                observation
            )
            if update_state:
                current_state = output_game_state

            # Check if done and exit if configured
            if done and self.config.exit_on_task_success:
                completion_result = CompletionResult(
                    step=agent_session.steps, reason=CompletionReason.SUCCESS
                )
                for agent in self.agents:
                    await agent.end(completion_result)
                return

    async def run_sequential(self):
        """Run a single sequential trajectory"""

        # Initialize state based on resume or fresh start
        game_session = self.gym_env.game_session
        current_state = await self._initialize_trajectory_state()

        # Save system prompts for all agents at the start
        for agent_idx, agent in self.agents.items():
            self.logger.save_system_prompt(agent, agent_idx)

        # Run trajectory
        # Example: if max_steps=3 and self.agents has 2 agents (keys 0,1), this will run:
        # (step=0,agent=0), (step=0,agent=1), (step=1,agent=0), (step=1,agent=1), (step=2,agent=0), (step=2,agent=1)
        # Total iterations = max_steps * num_agents = 3 * 2 = 6 iterations
        # Note: This leads to sequential execution of multiple agents. (Not parallel)
        for _, agent_idx in product(range(self.max_steps), self.agents.keys()):
            try:
                agent = self.agents[agent_idx]
                agent_session = game_session.agent_sessions[agent_idx]
                await self._run_trajectory_step(agent, agent_session, current_state)
            except Exception as e:
                print(
                    f"Error in trajectory runner iteration {agent_session.steps}: {e}"
                )
                continue
