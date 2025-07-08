import time
import gym
import numpy as np
from gym import spaces
from typing import Dict, Optional, Tuple, Any
import pickle
import datetime
import string

from fle.env import FactorioInstance
from fle.commons.models.game_state import GameState
from fle.env.gym_env.action import Action
from fle.commons.models.achievements import ProductionFlows
from fle.env.utils.profits import get_achievements
from fle.agents import Response, TaskResponse
from fle.env.gym_env.observation import (
    Observation,
    GameInfo,
    AgentMessage,
)
from fle.eval.tasks import TaskABC

# need to do this since gym doesn't work with numpy>=2.0 otherwise.
np.bool8 = np.dtype(np.bool)


class AllCharText(gym.spaces.Text):
    def __init__(self, max_length: int):
        # Use all printable characters except whitespace (or include whitespace if needed)
        charset = string.ascii_letters + string.digits + string.punctuation + " \n\t"
        super().__init__(max_length=max_length, min_length=0, charset=charset)


# Common space objects to reduce code duplication
class ObsSpaces:
    """Common space objects used throughout the observation space"""

    # Text spaces with common lengths
    SHORT_TEXT = AllCharText(max_length=200)
    LONG_TEXT = AllCharText(max_length=10000)
    VERY_LONG_TEXT = AllCharText(max_length=1000000)

    # Numeric spaces
    POSITIVE_INT = spaces.Box(low=0, high=np.inf, shape=(), dtype=np.int32)
    POSITIVE_FLOAT = spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float32)
    SCORE_FLOAT = spaces.Box(low=-np.inf, high=np.inf, shape=(), dtype=np.float32)
    PROGRESS_FLOAT = spaces.Box(low=0, high=1, shape=(), dtype=np.float32)

    # Boolean space
    BOOLEAN = spaces.Discrete(2)  # 0 or 1

    # Common item structure with type and quantity
    ITEM_WITH_QUANTITY = spaces.Dict(
        {
            "type": SHORT_TEXT,
            "quantity": POSITIVE_INT,
        }
    )

    # Common item structure with type and amount (float)
    ITEM_WITH_AMOUNT = spaces.Dict(
        {
            "type": SHORT_TEXT,
            "amount": POSITIVE_FLOAT,
        }
    )

    # Common item structure with type and rate
    ITEM_WITH_RATE = spaces.Dict(
        {
            "type": SHORT_TEXT,
            "rate": POSITIVE_FLOAT,
        }
    )

    # Common item structure with type and value
    ITEM_WITH_VALUE = spaces.Dict(
        {
            "type": SHORT_TEXT,
            "value": POSITIVE_FLOAT,
        }
    )

    # Common item structure with type and price
    ITEM_WITH_PRICE = spaces.Dict(
        {
            "type": SHORT_TEXT,
            "price": POSITIVE_FLOAT,
        }
    )

    # Common key-value pair structure
    KEY_VALUE_PAIR = spaces.Dict(
        {
            "key": SHORT_TEXT,
            "value": LONG_TEXT,
        }
    )

    # Common name-value pair structure
    NAME_VALUE_PAIR = spaces.Dict(
        {
            "name": SHORT_TEXT,
            "value": POSITIVE_FLOAT,
        }
    )

    # Technology ingredients structure
    TECHNOLOGY_INGREDIENT = spaces.Dict(
        {
            "item": SHORT_TEXT,
            "amount": POSITIVE_INT,
        }
    )

    # Crafted item structure
    CRAFTED_ITEM = spaces.Dict(
        {
            "crafted_count": POSITIVE_INT,
            "inputs": ITEM_WITH_AMOUNT,
            "outputs": ITEM_WITH_AMOUNT,
        }
    )

    # Message structure
    MESSAGE = spaces.Dict(
        {
            "sender": SHORT_TEXT,
            "content": LONG_TEXT,
            "timestamp": POSITIVE_FLOAT,
        }
    )

    # Serialized function structure
    SERIALIZED_FUNCTION = spaces.Dict(
        {
            "name": SHORT_TEXT,
            "pickled_function": LONG_TEXT,
        }
    )

    # Technology structure
    TECHNOLOGY = spaces.Dict(
        {
            "name": SHORT_TEXT,
            "researched": BOOLEAN,
            "enabled": BOOLEAN,
            "level": POSITIVE_INT,
            "research_unit_count": POSITIVE_INT,
            "research_unit_energy": POSITIVE_FLOAT,
            "prerequisites": spaces.Sequence(SHORT_TEXT),
            "ingredients": spaces.Sequence(TECHNOLOGY_INGREDIENT),
        }
    )

    # Research structure
    RESEARCH = spaces.Dict(
        {
            "technologies": spaces.Sequence(TECHNOLOGY),
            "current_research": SHORT_TEXT,
            "research_progress": PROGRESS_FLOAT,
            "research_queue": spaces.Sequence(SHORT_TEXT),
            "progress": spaces.Sequence(NAME_VALUE_PAIR),
        }
    )

    # Game info structure
    GAME_INFO = spaces.Dict(
        {
            "tick": POSITIVE_INT,
            "time": POSITIVE_FLOAT,
            "speed": POSITIVE_FLOAT,
        }
    )

    # Flows structure
    FLOWS = spaces.Dict(
        {
            "input": spaces.Sequence(ITEM_WITH_RATE),
            "output": spaces.Sequence(ITEM_WITH_RATE),
            "crafted": spaces.Sequence(CRAFTED_ITEM),
            "harvested": spaces.Sequence(ITEM_WITH_AMOUNT),
            "price_list": spaces.Sequence(ITEM_WITH_PRICE),
            "static_items": spaces.Sequence(ITEM_WITH_VALUE),
        }
    )

    # Task verification structure
    TASK_VERIFICATION = spaces.Dict(
        {
            "success": BOOLEAN,
            "meta": spaces.Sequence(KEY_VALUE_PAIR),
        }
    )


class FactorioGymEnv(gym.Env):
    """OpenAI Gym environment for Factorio"""

    def __init__(
        self,
        instance: FactorioInstance,
        task: Optional[TaskABC] = None,
        value_accrual_time: int = 10,
        error_penalty: float = 10.0,
    ):
        super().__init__()

        self.instance = instance
        self.task = task
        self.value_accrual_time = value_accrual_time
        self.error_penalty = error_penalty

        # Define action space - a dictionary containing agent index and code
        self.action_space = spaces.Dict(
            {
                "agent_idx": spaces.Discrete(
                    instance.num_agents
                ),  # Index of the agent taking the action
                "game_state": ObsSpaces.VERY_LONG_TEXT,  # The game state to reset to before running code (GameState.to_raw() str)
                "code": ObsSpaces.LONG_TEXT,  # The Python code to execute
            }
        )

        # Define observation space with expanded fields
        self.observation_space = spaces.Dict(
            {
                # Raw text output from the last action
                "raw_text": ObsSpaces.LONG_TEXT,
                # Entities on the map - now as text representations
                "entities": spaces.Sequence(
                    ObsSpaces.LONG_TEXT
                ),  # Each entity's repr string
                # Current inventory state
                "inventory": spaces.Sequence(ObsSpaces.ITEM_WITH_QUANTITY),
                # Research state
                "research": ObsSpaces.RESEARCH,
                # Game information
                "game_info": ObsSpaces.GAME_INFO,
                # Current score
                "score": ObsSpaces.SCORE_FLOAT,
                # Production flows
                "flows": ObsSpaces.FLOWS,
                # Task verification status
                "task_verification": ObsSpaces.TASK_VERIFICATION,
                # Messages from other agents
                "messages": spaces.Sequence(ObsSpaces.MESSAGE),
                # Serialized functions
                "serialized_functions": spaces.Sequence(ObsSpaces.SERIALIZED_FUNCTION),
            }
        )

        self.current_state = None
        self.initial_score = 0
        self.last_observation = None
        # Track last message timestamp for each agent
        self.last_message_timestamps = {i: 0.0 for i in range(instance.num_agents)}

    def get_observation(
        self, agent_idx: int = 0, response: Optional[Response] = None
    ) -> Observation:
        """Convert the current game state into a gym observation"""
        namespace = self.instance.namespaces[agent_idx]
        # Get entity observations
        entities = namespace.get_entities()
        entity_obs = [str(e) for e in entities]

        # Get inventory observations
        inventory_obs = namespace.inspect_inventory()

        # Get research observations
        research_obs = namespace._save_research_state()

        # Get game info
        game_info = GameInfo(
            tick=self.instance.get_elapsed_ticks(),
            time=self.instance.get_elapsed_ticks() / 60,
            speed=self.instance._speed,
        )

        # Get flows
        flows = namespace._get_production_stats()
        flows_obs = ProductionFlows.from_dict(flows)

        # Get messages
        messages = namespace.get_messages()
        messages_obs = []
        latest_timestamp = self.last_message_timestamps[agent_idx]

        for msg in messages:
            if msg["timestamp"] > self.last_message_timestamps[agent_idx]:
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
            self.last_message_timestamps[agent_idx] = latest_timestamp

        # Get task verification if available
        task_verification = None
        if response and hasattr(response, "task"):
            task_verification = TaskResponse(
                success=response.task.success,
                meta=response.task.meta if hasattr(response.task, "meta") else {},
            )

        # Get serialized functions
        serialized_functions = []
        for func in namespace.get_functions():
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

    def step(
        self, action: Action
    ) -> Tuple[Dict[str, Any], float, bool, bool, Dict[str, Any]]:
        """
        Execute one step in the environment

        Args:
            action: Action object

        Returns:
            observation: The new observation as a dictionary matching the observation space
            reward: The reward for this step
            terminated: Whether the episode is done
            truncated: Whether the episode is truncated
            info: Additional information
        """
        assert isinstance(action, Action)
        action = action.to_dict()
        agent_idx = action["agent_idx"]
        code = action["code"]
        game_state_raw = action["game_state"]
        if game_state_raw:
            self.reset_instance(GameState.parse_raw(game_state_raw))

        namespace = self.instance.namespaces[agent_idx]
        start_production_flows = ProductionFlows.from_dict(
            namespace._get_production_stats()
        )
        initial_score, _ = namespace.score()

        # Execute the action
        score, eval_time, result = self.instance.eval(
            code, agent_idx=agent_idx, timeout=60
        )

        # Check for errors
        error_occurred = "error" in result.lower() or "exception: " in result.lower()

        # Calculate reward
        if error_occurred:
            reward = -self.error_penalty
        else:
            # Wait for value accrual
            time.sleep(self.value_accrual_time)
            reward = score - initial_score
        reward = float(reward)  # Ensure reward is always a float

        # Get task verification if task exists
        task_response = task_success = None
        terminated = truncated = False
        output_game_state = GameState.from_instance(self.instance)
        if self.task:
            # First get the raw verification
            task_success = self.task.verify(reward, self.instance, step_statistics={})
            # Then enhance the response with task output
            task_response = self.task.enhance_response_with_task_output(
                result, task_success
            )
            terminated = task_success.success

        # Get post-execution flows and calculate achievements
        current_flows = ProductionFlows.from_dict(namespace._get_production_stats())
        achievements = get_achievements(
            start_production_flows.__dict__, current_flows.__dict__
        )

        # Create response object for observation
        response = Response(
            code=f"```python\n{code}\n```",
            created_at=datetime.datetime.now(),
            score=reward,
            achievements=achievements,
            step=0,
            ticks=self.instance.get_elapsed_ticks(),
            flows=start_production_flows.get_new_flows(current_flows),
            response=task_response if task_response else result,
            task=task_success if task_success else TaskResponse(success=False, meta={}),
            error=error_occurred,
            program_id=None,
        )

        # Get observation for the acting agent
        observation = self.get_observation(agent_idx, response)

        # Get additional info
        info = {
            "error_occurred": error_occurred,
            "result": result,
            "ticks": self.instance.get_elapsed_ticks(),
            "flows": response.flows,
            "agent_idx": agent_idx,
            "last_message_timestamp": self.last_message_timestamps[agent_idx],
            "task_verification": task_response,
            "output_game_state": output_game_state,
        }

        return observation.to_dict(), reward, terminated, truncated, info

    def reset_instance(self, state: Optional[GameState] = None) -> None:
        """Reset the Factorio instance to a given state or initial state.

        Args:
            state: Optional[GameState] to reset to. If None, resets to initial state.
        """
        self.instance.reset(state)

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

        self.initial_score, _ = self.instance.namespaces[0].score()
        self.last_observation = None  # Reset last observation
        # Reset message timestamps
        self.last_message_timestamps = {i: 0.0 for i in range(self.instance.num_agents)}
        # Convert observation to dictionary to match gym standards
        observation = self.get_observation(0).to_dict()
        return observation, {}  # Return observation for first agent

    def close(self):
        """Clean up resources"""
        self.instance.cleanup()
