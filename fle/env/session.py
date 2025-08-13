import datetime
from dataclasses import dataclass
import pickle
import time
from typing import Any, Dict, List, Optional, Tuple

from a2a.types import AgentCard

from fle.agents.models import Response
from fle.commons.models.conversation import Conversation
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
from fle.services.docker.docker_manager import FactorioHeadlessServer
from fle.services.db.db_client import DBClient
from fle.env.tasks import TaskABC
from fle.services.db.db_client import create_db_client


class AgentSession:
    """High-level facade over a single Factorio agent instance."""

    @dataclass
    class Snapshot:
        score: float
        flows: ProductionFlows
        tick: int
        timestamp: float
        observation: Optional[Observation] = None

    class AgentResult:
        pre: "AgentSession.Snapshot"
        post: Optional["AgentSession.Snapshot"]
        result: str

        def __init__(
            self,
            pre: "AgentSession.Snapshot",
            post: Optional["AgentSession.Snapshot"],
            result: str,
        ):
            self.pre = pre
            self.post = post
            self.result = result

        def set_post(self, post: "AgentSession.Snapshot") -> None:
            self.post = post

        @property
        def error_occurred(self) -> bool:
            return (
                "error" in self.result.lower() or "exception: " in self.result.lower()
            )

        @property
        def score_delta(self) -> float:
            return self.post.score - self.pre.score

        @property
        def flows_delta(self) -> ProductionFlows:
            return self.post.flows.get_new_flows(self.pre.flows)

    steps: int
    namespace: FactorioNamespace | A2AFactorioNamespace
    agent_instance: AgentInstance
    last_message_timestamp: float
    last_observation: Optional[Observation]
    _last_production_flow: Optional[ProductionFlows]
    version: int
    version_description: str
    db_client: DBClient

    def __init__(
        self,
        agent_idx: int,
        agent_instance: AgentInstance,
        db_client: DBClient,
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

    def get_partial_observation(
        self,
        game_info: GameInfo,
    ) -> Observation:
        """Convert the current game state into an observation"""
        # Get entity observations
        entities = self.namespace.get_entities()
        entity_obs = [str(e) for e in entities]

        # Get inventory observations
        inventory_obs = self.namespace.inspect_inventory()

        # Get research observations
        research_obs = self.namespace._save_research_state()

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

        # Get serialized functions
        serialized_functions = []
        for func in self.namespace.get_functions():
            serialized_functions.append(
                {"name": func.name, "pickled_function": pickle.dumps(func).hex()}
            )

        observation = Observation(
            raw_text="",
            entities=entity_obs,  # Convert entities to strings
            inventory=inventory_obs,
            research=research_obs,
            game_info=game_info,
            score=0.0,
            flows=flows_obs,
            task_verification=None,
            messages=messages_obs,
            serialized_functions=serialized_functions,
        )

        # Store observation for next step
        self.last_observation = observation

        return observation
    
    async def save_program(self, program: Program) -> Program:
        program = await self.db_client.create_program(program)
        program.update_program_id(program.id)
        return program

    async def get_resume_state(self, process_id: int) -> Tuple[GameState, Conversation]:
        (
            current_state,
            agent_conversation,
            parent_id,
            depth,
        ) = await self.db_client.get_resume_state(
            resume_version=self.version,
            process_id=process_id,
            agent_idx=self.agent_idx,
        )
        return current_state, agent_conversation, parent_id, depth

    @property
    def current_score(self) -> float:
        return self.namespace.score()[0]

    @property
    def current_production_flows(self) -> ProductionFlows:
        """Get the current production flows"""
        return ProductionFlows.from_dict(self.namespace._get_production_stats())

    def _snapshot(self, observation: Optional[Observation] = None) -> Snapshot:
        return self.Snapshot(
            score=self.current_score,
            flows=self.current_production_flows,
            timestamp=time.time(),
            observation=observation,
        )

    def eval_with_snapshot(self, code: str, value_accrual_time: float = 0) -> AgentResult:

        initial_snapshot = self._snapshot()

        # Execute the action
        score, eval_time, result = self.agent_instance.eval(code, timeout=60)

        eval_results = self.AgentResult(
            pre=initial_snapshot,
            result=result,
        )

        if eval_results.error_occurred:
            eval_results.set_post(initial_snapshot)
            return eval_results

        time.sleep(value_accrual_time)

        eval_results.set_post(self._snapshot())

        return eval_results

    def get_achievements(self, eval_results: AgentResult) -> List[str]:
        return get_achievements(
            self.start_production_flows.__dict__, eval_results.current_flows.__dict__
        )

    def reset(self) -> None:
        self.namespace.reset()
        self.last_observation = None
        self.last_message_timestamp = 0.0


class GameSession:
    """High-level facade over a single Factorio headless server instance.

    Encapsulates: client, instance, namespaces, and access to server lifecycle
    via the cluster manager. Provides convenience methods that pool low-level
    usage behind a consistent API suitable for gym runners and registries.
    """

    config: GameConfig
    server: FactorioHeadlessServer
    instance: FactorioInstance | A2AFactorioInstance
    agent_sessions: Dict[int, AgentSession]
    current_game_state: Optional[GameState]
    task: Optional[TaskABC]

    @dataclass
    class Snapshot:
        game_state: GameState
        game_info: GameInfo

    @dataclass
    class GameResult:
        post: "GameSession.Snapshot"
        agent_result: AgentSession.AgentResult
        partial_observation: Observation

        def __init__(
            self,
            post: "GameSession.Snapshot",
            result: AgentSession.AgentResult,
            partial_observation: Observation,
        ):
            self.post = post
            self.agent_result = result
            self.partial_observation = partial_observation

        @property
        def result(self) -> str:
            return self.agent_result.result
        
        @result.setter
        def result(self, value: str) -> None:
            self.agent_result.result = value
            
        @property
        def score_delta(self) -> float:
            return self.agent_result.score_delta
        
        @property
        def error_occurred(self) -> bool:
            return self.agent_result.error_occurred
        
        @property
        def flows_delta(self) -> ProductionFlows:
            return self.agent_result.flows_delta

    def __init__(
        self,
        instance_id: int,
        instance: FactorioInstance,
        server: FactorioHeadlessServer,
        config: GameConfig,
        task: Optional[TaskABC] = None,
    ) -> None:
        self.instance_id = instance_id
        self.instance = instance
        self.server = server
        self.config = config
        self.task = task

    async def initialise(self) -> None:
        self.agent_sessions = await self._make_agent_sessions()

    @property
    def num_agents(self) -> int:
        return self.config.num_agents

    @property
    def elapsed_ticks(self) -> int:
        return self.instance.get_elapsed_ticks()

    @property
    def current_game_state(self) -> GameState:
        return GameState.from_instance(self.instance)

    @property
    def current_game_info(self) -> GameInfo:
        return GameInfo(
            tick=self.elapsed_ticks,
            time=self.elapsed_ticks / 60,
            speed=self.speed,
        )

    def _snapshot(self) -> "GameSession.Snapshot":
        return self.Snapshot(
            self.current_game_state,
            self.current_game_info,
        )

    async def get_agent_session_resume_state(self, agent_idx: int, process_id: int) -> Tuple[GameState, Conversation]:
        agent_session = self.agent_sessions[agent_idx]
        current_state, agent_conversation, parent_id, depth = await agent_session.get_resume_state(process_id=process_id)
        if current_state:
            agent_session.steps = depth
        if not current_state and self.task:
            current_state = self.task.starting_game_state
        return current_state, agent_conversation

    def eval_agent_with_snapshot(
        self, agent_idx: int, code: str, value_accrual_time: int
    ):
        agent_session = self.agent_sessions[agent_idx]
        if agent_session.last_observation:
            self.reset_instance(agent_session.last_observation.state)

        agent_eval_results = agent_session.eval_with_snapshot(
            code=code, value_accrual_time=value_accrual_time
        )
        post_snapshot = self._snapshot()
        partial_observation = agent_session.get_partial_observation(post_snapshot.game_info)

        return self.GameResult(
            post=post_snapshot,
            agent_result=agent_eval_results,
            partial_observation=partial_observation,
        )

    def verify_task(
        self, reward: float, game_result: GameResult, step_statistics: Dict[str, Any] = {}
    ) -> TaskResponse:
        if not self.task:
            print(f"[WARN] No task to verify, instance: {self.instance_id}")
            return None
        # First get the raw verification
        task_success = self.task.verify(reward, self.instance, step_statistics)
        # Then enhance the response with task output
        task_response = self.task.enhance_response_with_task_output(
            game_result.result, task_success
        )
        game_result.result = task_response
        return game_result
    
    async def _make_agent_sessions(self) -> Dict[int, AgentSession]:
        return {
            i: AgentSession(i, self.instance.agent_instances[i], await create_db_client())
            for i in range(self.instance.num_agents)
        }

    def reinitialize_instance(self) -> None:
        if isinstance(self.instance, A2AFactorioInstance):
            # TODO: Add a2a specific reinitialization, if any
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
        observation = self.agent_sessions[0].get_partial_observation().to_dict()
        return observation, {}  # Return observation for first agent

    def cleanup(self) -> None:
        self.instance.cleanup()
