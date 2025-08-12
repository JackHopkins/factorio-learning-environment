import datetime
import pickle
import time
from typing import Any, Dict, List, Optional, Tuple

from a2a.types import AgentCard

from fle.agents.models import Response
from fle.commons.models.program import Program
from fle.env.a2a_instance import A2AFactorioInstance
from fle.env.a2a_namespace import A2AFactorioNamespace
from fle.env.game.config import GameConfig
from fle.env.game.factorio_client import FactorioClient
from fle.env.game.game_state import GameState
from fle.env.game.instance import FactorioInstance, AgentInstance
from fle.env.game.namespace import FactorioNamespace
from fle.env.models.action import Action
from fle.env.models.observation import (
    AgentMessage,
    GameInfo,
    Observation,
    ProductionFlows,
    TaskResponse,
)
from fle.env.utils.profits import get_achievements
from fle.services.docker.config import DockerConfig
from fle.services.docker.docker_manager import (
    FactorioHeadlessClusterManager,
    FactorioHeadlessServer,
)
from fle.services.db.db_client import DBClient, create_db_client


class AgentSession:
    """High-level facade over a single Factorio agent instance."""

    steps: int
    namespace: FactorioNamespace | A2AFactorioNamespace
    agent_instance: AgentInstance
    last_message_timestamp: float
    last_observation: Optional[Observation]
    _last_production_flow: Optional[ProductionFlows]
    version: int
    version_description: str
    db_client: DBClient

    class EvalResults:
        def __init__(
            self, result: str, initial_score: float, score: float, eval_time: float
        ):
            self.result = result
            self.initial_score = initial_score
            self.score = score
            self.eval_time = eval_time

        @property
        def error_occurred(self) -> bool:
            return (
                "error" in self.result.lower() or "exception: " in self.result.lower()
            )

        @property
        def current_flows(self) -> ProductionFlows:
            return ProductionFlows.from_dict(self.namespace._get_production_stats())

    def __init__(
        self, agent_idx: int, agent_instance: AgentInstance, db_client: DBClient
    ):
        self.agent_idx = agent_idx
        self.steps = 0
        self.agent_instance = agent_instance
        self.namespace = agent_instance.namespace
        self.db_client = db_client
        self.reset()

    @property
    def version(self) -> int:
        return self.db_client.get_largest_version()

    @property
    def version_description(self) -> str:
        return self.db_client.get_version_description(self.version)

    def get_observation(self, response: Optional[Response] = None) -> Observation:
        """Convert the current game state into an observation"""
        # Get entity observations
        entities = self.namespace.get_entities()
        entity_obs = [str(e) for e in entities]

        # Get inventory observations
        inventory_obs = self.namespace.inspect_inventory()

        # Get research observations
        research_obs = self.namespace._save_research_state()

        # Get game info
        game_info = GameInfo(
            tick=self.namespace.instance.get_elapsed_ticks(),
            time=self.namespace.instance.get_elapsed_ticks() / 60,
            speed=self.namespace.instance._speed,
        )

        # Get flows
        flows = self.namespace._get_production_stats()
        flows_obs = ProductionFlows.from_dict(flows)

        # Get messages
        messages = self.namespace.get_messages()
        messages_obs = []
        latest_timestamp = self.last_message_timestamp

        for msg in messages:
            if msg["timestamp"] > self.last_message_timestamp:
                messages_obs.append(
                    AgentMessage(
                        sender=msg["sender"],
                        content=msg["message"],
                        timestamp=msg["timestamp"],
                    )
                )
                latest_timestamp = max(latest_timestamp, msg["timestamp"])

        # Update last message timestamp
        if messages_obs:
            self.last_message_timestamp = latest_timestamp

        # Get task verification if available
        task_verification = None
        if response and hasattr(response, "task"):
            task_verification = TaskResponse(
                success=response.task.success,
                meta=response.task.meta if hasattr(response.task, "meta") else {},
            )

        # Get serialized functions
        serialized_functions = []
        for func in self.namespace.get_functions():
            serialized_functions.append(
                {"name": func.name, "pickled_function": pickle.dumps(func).hex()}
            )

        observation = Observation(
            raw_text=response.response if response else "",
            entities=entity_obs,  # Convert entities to strings
            inventory=inventory_obs,
            research=research_obs,
            game_info=game_info,
            score=response.score if response else 0.0,
            flows=flows_obs,
            task_verification=task_verification,
            messages=messages_obs,
            serialized_functions=serialized_functions,
        )

        # Store observation for next step
        self.last_observation = observation

        return observation

    async def _initialize_trajectory_state(
        self, version: int, process_id: int
    ) -> Tuple[GameState, List[int]]:
        """Initialize trajectory state, either from resume or fresh start

        Returns:
            Tuple of (current_state, agent_steps)
        """
        current_state = None

        if version and self.db_client is None:
            return None, 0

        (
            current_state,
            agent_conversation,
            parent_id,
            depth,
        ) = await self.db_client.get_resume_state(
            resume_version=version,
            process_id=process_id,
            agent_idx=self.agent_idx,
        )
        if current_state:
            self.steps = depth

        if not current_state:
            current_state = self.config.task.starting_game_state

        return current_state, agent_conversation

    def action_from_code(self, code: str) -> Action:
        """Create an Action object from a Policy"""
        return Action(
            agent_idx=self.agent_idx,
            code=code,
            game_state=self.last_observation.state,
        )

    def eval(self, code: str) -> EvalResults:
        if self.last_observation.state:
            self.reset_instance(self.last_observation.state)

        # Use last post_production_flows as pre_production_flows if available
        start_production_flows = ProductionFlows.from_dict(
            self._last_production_flows.get(self.agent_idx)
            or self.namespace._get_production_stats()
        )
        initial_score, _ = self.namespace.score()

        # Execute the action
        score, eval_time, result = self.agent_instance.eval(code, timeout=60)
        # return result, initial_score, score, eval_time
        return self.EvalResults(result, initial_score, score, eval_time)

    def get_achievements(self, eval_results: EvalResults) -> List[str]:
        return get_achievements(
            self.start_production_flows.__dict__, eval_results.current_flows.__dict__
        )

    def reset(self) -> None:
        self.namespace.reset()
        self.last_observation = None
        self.last_message_timestamp = 0.0
        self._last_production_flow = None


class GameSession:
    """High-level facade over a single Factorio headless server instance.

    Encapsulates: client, instance, namespaces, and access to server lifecycle
    via the cluster manager. Provides convenience methods that pool low-level
    usage behind a consistent API suitable for gym runners and registries.
    """

    server: FactorioHeadlessServer
    instance: FactorioInstance | A2AFactorioInstance
    agent_sessions: Dict[int, AgentSession]
    game_state: Optional[GameState]

    def __init__(
        self,
        instance_id: int,
        instance: FactorioInstance,
        server: FactorioHeadlessServer,
    ):
        self.instance_id = instance_id
        self.instance = instance
        self.server = server
        self.agent_sessions = self._make_agent_sessions()
        self.game_state = None

    def _make_agent_sessions(self) -> Dict[int, AgentSession]:
        return {
            i: AgentSession(i, self.instance.agent_instances[i], self.db_client)
            for i in range(self.instance.num_agents)
        }
    
    def reinitialize_instance(self) -> None:
        if isinstance(self.instance, A2AFactorioInstance):
            self.instance: A2AFactorioInstance
            self.instance.initialise()
        else:
            self.instance: FactorioInstance
            self.instance.initialise()
    
    async def restart_from_latest_save(self) -> None:
        await self.server.restart()
        self.reinitialize_instance()

    async def restart_from_save(self, save_name: str) -> None:
        await self.server.restart(save_name)
        self.reinitialize_instance()
        
    @property
    def speed(self) -> int:
        return self.instance.get_speed()

    @speed.setter 
    def speed(self, value: int) -> None:
        self.instance.set_speed(value)

    def reset_instance(self, state: Optional[GameState] = None) -> None:
        """Reset the Factorio instance to a given state or initial state.

        Args:
            state: Optional[GameState] to reset to. If None, resets to initial state.
        """
        self.instance.reset(state)
        for session in self.agent_sessions:
            session.reset()

    def reset(
        self, options: Optional[Dict[str, Any]] = None, seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """Reset the environment to initial state

        Args:
            options: dict containing 'game_state' key with Optional[GameState] value to reset to
            seed: Not used
        """
        if options is None:
            options = {}
        game_state = options.get("game_state")
        self.reset_instance(game_state)

        for session in self.agent_sessions:
            session.reset()

        # Convert observation to dictionary to match gym standards
        observation = self.agent_sessions[0].get_observation().to_dict()
        return observation, {}  # Return observation for first agent

    def cleanup(self) -> None:
        self.instance.cleanup()
