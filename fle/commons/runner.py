from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Generic, TypeVar
import time
from dataclasses import dataclass
from fle.services.db.db_client import DBClient
from fle.commons.models.program import Program
from fle.env.game.game_state import GameState
from fle.commons.models.conversation import Conversation
from fle.agents import CompletionResult, CompletionReason
from fle.env.tasks import TaskABC

# Generic types for flexibility
ConfigType = TypeVar("ConfigType")
AgentType = TypeVar("AgentType")
EnvironmentType = TypeVar("EnvironmentType")
ObservationType = TypeVar("ObservationType")
ActionType = TypeVar("ActionType")


@dataclass
class RunnerConfig(ABC):
    """Base configuration for all runners"""

    agents: List[Any]
    version: int
    version_description: str
    exit_on_task_success: bool
    task: TaskABC


class AbstractTrajectoryRunner(ABC, Generic[ConfigType, AgentType, EnvironmentType]):
    """Abstract base class for trajectory runners"""

    def __init__(
        self,
        config: ConfigType,
        environment: EnvironmentType,
        db_client: Optional[DBClient],
        process_id: int,
        log_dir: Optional[str] = None,
    ):
        self.config = config
        self.environment = environment
        self.agents = config.agents
        self.db_client = db_client
        self.process_id = process_id
        self.start_time = time.time()
        self.log_dir = log_dir

        # Common state tracking
        self.iteration_times = []
        self.agent_steps = [0] * len(self.agents)

        # Initialize logging
        self._initialize_logging()

    # Abstract methods that must be implemented by subclasses

    @abstractmethod
    async def _initialize_environment(
        self, initial_state: Optional[GameState] = None
    ) -> None:
        """Initialize the environment with the given state"""
        pass

    @abstractmethod
    async def _generate_policy(self, agent_idx: int, conversation: Conversation) -> Any:
        """Generate a policy/program for the given agent"""
        pass

    @abstractmethod
    async def _execute_step(
        self, agent_idx: int, policy: Any, current_state: GameState
    ) -> Tuple[ObservationType, float, bool, Dict[str, Any]]:
        """Execute a single step in the environment"""
        pass

    @abstractmethod
    async def _create_program_from_policy(
        self, policy: Any, agent_idx: int, **kwargs
    ) -> Program:
        """Create a Program object from a policy"""
        pass

    @abstractmethod
    async def _update_agent_conversation(
        self, agent_idx: int, observation: ObservationType, program: Program
    ) -> None:
        """Update the agent's conversation with the step results"""
        pass

    @abstractmethod
    def _check_step_completion(
        self, agent_idx: int, observation: ObservationType
    ) -> Tuple[bool, bool]:
        """Check if the agent step is complete and if state should be updated"""
        pass

    @abstractmethod
    async def _get_initial_observation(self, agent_idx: int) -> ObservationType:
        """Get the initial observation for an agent"""
        pass

    # Template methods - common patterns with some customization points

    async def _initialize_trajectory_state(
        self,
    ) -> Tuple[GameState, List[Conversation]]:
        """Initialize trajectory state, handling resume or fresh start"""
        current_state = None
        conversations = [None] * len(self.agents)

        # Check for resume state
        if self.config.version and self.db_client is not None:
            current_state, conversations = await self._load_resume_state()

        # Initialize fresh if no resume state
        if not current_state:
            current_state = self.config.task.starting_game_state
            conversations = await self._initialize_fresh_conversations()

        # Initialize environment
        await self._initialize_environment(current_state)

        return current_state, conversations

    async def _load_resume_state(
        self,
    ) -> Tuple[Optional[GameState], List[Conversation]]:
        """Load resume state from database"""
        current_state = None
        conversations = [None] * len(self.agents)

        for agent_idx in range(len(self.agents)):
            state, conversation, parent_id, depth = (
                await self.db_client.get_resume_state(
                    resume_version=self.config.version,
                    process_id=self.process_id,
                    agent_idx=agent_idx,
                )
            )
            if state:
                current_state = state
                conversations[agent_idx] = conversation
                self.agent_steps[agent_idx] = depth

        return current_state, conversations

    async def _initialize_fresh_conversations(self) -> List[Conversation]:
        """Initialize fresh conversations for all agents"""
        conversations = []
        for agent_idx in range(len(self.agents)):
            conversation = Conversation()
            initial_obs = await self._get_initial_observation(agent_idx)
            # Add initial system message and observation
            conversation.add_system_message(self.agents[agent_idx].system_prompt)
            conversation.add_user_message(self._format_initial_observation(initial_obs))
            conversations.append(conversation)
        return conversations

    def _format_initial_observation(self, observation: ObservationType) -> str:
        """Format initial observation for conversation - can be overridden"""
        return str(observation)

    def _initialize_logging(self) -> None:
        """Initialize logging system - can be overridden"""
        pass

    def _log_progress(self, agent_idx: int, step: int, value: float) -> None:
        """Log progress - can be overridden"""
        if step % 10 == 0:
            elapsed = time.time() - self.start_time
            elapsed_str = f"{int(elapsed // 3600):02d}:{int((elapsed % 3600) // 60):02d}:{int(elapsed % 60):02d}"
            eta = self._calculate_eta(step)
            print(
                f"Process {self.process_id} - Agent {agent_idx} - "
                f"Step {step}/{self.config.task.trajectory_length} - "
                f"Value: {value:.2f} - Elapsed: {elapsed_str} - ETA: {eta}"
            )

    def _calculate_eta(self, current_step: int) -> str:
        """Calculate estimated time remaining"""
        if not self.iteration_times:
            return "calculating..."

        # Use recent iterations for better accuracy
        recent_times = self.iteration_times[-50:]
        avg_time = sum(recent_times) / len(recent_times)
        remaining_steps = self.config.task.trajectory_length - current_step
        seconds_remaining = avg_time * remaining_steps

        hours = int(seconds_remaining // 3600)
        minutes = int((seconds_remaining % 3600) // 60)
        seconds = int(seconds_remaining % 60)

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    # Main run method - implements the common trajectory execution pattern

    async def run(self) -> None:
        """Main trajectory execution loop"""
        # Initialize state
        current_state, conversations = await self._initialize_trajectory_state()
        max_steps = self.config.task.trajectory_length

        # Main execution loop
        from itertools import product

        for _, agent_idx in product(range(max_steps), range(len(self.agents))):
            if self.agent_steps[agent_idx] >= max_steps:
                continue

            iteration_start = time.time()
            agent_completed = False

            try:
                # Agent execution loop
                while not agent_completed and self.agent_steps[agent_idx] < max_steps:
                    # Generate policy
                    policy = await self._generate_policy(
                        agent_idx, conversations[agent_idx]
                    )
                    self.agent_steps[agent_idx] += 1

                    if not policy:
                        print(f"Policy generation failed for agent {agent_idx}")
                        break

                    # Execute step
                    observation, reward, done, info = await self._execute_step(
                        agent_idx, policy, current_state
                    )

                    # Create program
                    program = await self._create_program_from_policy(
                        policy,
                        agent_idx,
                        reward=reward,
                        observation=observation,
                        info=info,
                    )

                    # Update conversation
                    await self._update_agent_conversation(
                        agent_idx, observation, program
                    )

                    # Save program if database available
                    if self.db_client:
                        await self._save_program(program)

                    # Log progress
                    self._log_step_completion(iteration_start, agent_idx, program)

                    # Check completion
                    agent_completed, update_state = self._check_step_completion(
                        agent_idx, observation
                    )
                    if update_state:
                        current_state = info.get("output_game_state", current_state)

                    # Check for early termination
                    if done and self.config.exit_on_task_success:
                        await self._handle_early_termination(agent_idx)
                        return

            except Exception as e:
                print(
                    f"Error in trajectory runner iteration {self.agent_steps[agent_idx]}: {e}"
                )
                continue

    async def _save_program(self, program: Program) -> None:
        """Save program to database"""
        if self.db_client:
            saved_program = await self.db_client.create_program(program)
            program.id = saved_program.id

    def _log_step_completion(
        self, iteration_start: float, agent_idx: int, program: Program
    ) -> None:
        """Log completion of a step"""
        iteration_time = time.time() - iteration_start
        self.iteration_times.append(iteration_time)

        # Keep only recent iterations
        if len(self.iteration_times) > 50:
            self.iteration_times = self.iteration_times[-50:]

        self._log_progress(agent_idx, self.agent_steps[agent_idx], program.value)

    async def _handle_early_termination(self, agent_idx: int) -> None:
        """Handle early termination due to task success"""
        completion_result = CompletionResult(
            step=self.agent_steps[agent_idx], reason=CompletionReason.SUCCESS
        )
        for agent in self.agents:
            await agent.end(completion_result)
