import datetime
import pickle
import string
import time
from typing import Any, Dict, Optional, Tuple

import gym
import numpy as np
from gym import spaces

from fle.agents import Response, TaskResponse
from fle.commons.models.achievements import ProductionFlows
from fle.env.game.game_state import GameState

# from fle.env.game import FactorioInstance
from fle.env.models.action import Action
from fle.env.models.observation import (
    AgentMessage,
    GameInfo,
    Observation,
    ProductionFlows,
    TaskResponse,
)
from fle.env.tasks import TaskABC
from fle.env.utils.profits import get_achievements
from fle.env.session import AgentSession, GameSession

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
        game_session: GameSession,
        value_accrual_time: int = 10,
        error_penalty: float = 10.0,
    ):
        super().__init__()

        self.game_session = game_session
        self.value_accrual_time = value_accrual_time
        self.error_penalty = error_penalty

        # Define action space - a dictionary containing agent index and code
        self.action_space = spaces.Dict(
            {
                "agent_idx": spaces.Discrete(
                    game_session.num_agents
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
        agent_idx = action.agent_idx
        game_result = self.game_session.eval_agent_with_snapshot(
            agent_idx=agent_idx,
            code=action.code,
            value_accrual_time=self.value_accrual_time,
        )

        # Calculate reward
        reward = (
            -self.error_penalty
            if game_result.error_occurred
            else game_result.score_delta
        )
        reward = float(reward)  # Ensure reward is always a float

        # Get task verification if task exists
        task_response = None
        terminated = truncated = False

        if self.game_session.task:
            game_result = self.game_session.verify_task(reward, game_result)
            # verify_task mutates game_result.result to be a TaskResponse
            if isinstance(game_result.result, TaskResponse):
                task_response = game_result.result
                terminated = bool(task_response.success)

        # Get observation for the acting agent
        observation = game_result.partial_observation.add_response(
            game_result.result, reward, task_response
        )

        # Get additional info
        info = {
            "agent_idx": agent_idx,
            "ticks": game_result.post.game_info.tick,
            "error_occurred": game_result.error_occurred,
            "result": game_result.result,
            "flows": game_result.flows_delta,
            "last_message_timestamp": observation.last_message_timestamp,
            "task_verification": task_response,
            "output_game_state": game_result.post.game_state,
        }

        return observation.to_dict(), reward, terminated, truncated, info

    def reset(
        self, *, seed: Optional[int] = None, options: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Gymnasium-compatible reset that delegates to the game session.

        Returns (observation, info).
        """
        # Gym API requires calling super().reset(seed=seed)
        super().reset(seed=seed)
        obs, info = self.game_session.reset(options=options, seed=seed)
        return obs, info

    def close(self):
        """Clean up resources"""
        self.game_session.cleanup()
