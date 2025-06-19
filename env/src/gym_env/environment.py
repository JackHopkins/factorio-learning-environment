import asyncio
import time
import gym
import numpy as np
from gym import spaces
from typing import Dict, List, Optional, Tuple, Union, Any
import pickle
import datetime
import string

from env.src.instance import FactorioInstance
from env.src.models.game_state import GameState
from env.src.models.achievements import ProductionFlows
from env.src.entities import EntityStatus
from env.src.utils.profits import get_achievements
from agents import Response, TaskResponse
from env.src.gym_env.observation import (
    Observation, 
    GameInfo, 
    AgentMessage,
)
from eval.tasks.task_abc import TaskABC

# need to do this since gym doesn't work with numpy>=2.0 otherwise.
np.bool8 = np.dtype(np.bool)


class AllCharText(gym.spaces.Text):
    def __init__(self, max_length: int):
        # Use all printable characters except whitespace (or include whitespace if needed)
        charset = string.ascii_letters + string.digits + string.punctuation + ' \n\t'
        super().__init__(max_length=max_length, min_length=0, charset=charset)


class FactorioGymEnv(gym.Env):
    """OpenAI Gym environment for Factorio"""
    
    def __init__(self,
                 instance: FactorioInstance,
                 task: Optional[TaskABC] = None,
                 value_accrual_time: int = 10,
                 error_penalty: float = 10.0):
        super().__init__()
        
        self.instance = instance
        self.task = task
        self.value_accrual_time = value_accrual_time
        self.error_penalty = error_penalty
        
        # Define action space - a dictionary containing agent index and code
        self.action_space = spaces.Dict({
            'agent_idx': spaces.Discrete(instance.num_agents),  # Index of the agent taking the action
            'game_state': AllCharText(max_length=1000000),  # The game state to reset to before running code (GameState.to_raw() str)
            'code': AllCharText(max_length=10000)  # The Python code to execute
        })
        
        # Define observation space with expanded fields
        self.observation_space = spaces.Dict({
            # Raw text output from the last action
            'raw_text': AllCharText(max_length=10000),
            
            # Entities on the map - now as text representations
            'entities': spaces.Sequence(AllCharText(max_length=1000)),  # Each entity's repr string
            
            # Current inventory state
            'inventory': spaces.Sequence(spaces.Dict({
                'type': AllCharText(max_length=200),
                'quantity': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.int32),
            })),
            
            # Research state
            'research': spaces.Dict({
                'technologies': spaces.Sequence(spaces.Dict({
                    'name': AllCharText(max_length=200),
                    'researched': spaces.Discrete(2),  # 0 or 1
                    'enabled': spaces.Discrete(2),  # 0 or 1
                    'level': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.int32),
                    'research_unit_count': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.int32),
                    'research_unit_energy': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float32),
                    'prerequisites': spaces.Sequence(AllCharText(max_length=200)),
                    'ingredients': spaces.Sequence(spaces.Dict({
                        'item': AllCharText(max_length=200),
                        'amount': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.int32),
                    })),
                })),
                'current_research': AllCharText(max_length=200),
                'research_progress': spaces.Box(low=0, high=1, shape=(), dtype=np.float32),
                'research_queue': spaces.Sequence(AllCharText(max_length=200)),
                'progress': spaces.Sequence(spaces.Dict({
                    'name': AllCharText(max_length=200),
                    'value': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float32),
                })),
            }),
            
            # Game information
            'game_info': spaces.Dict({
                'tick': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.int32),
                'time': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float32),
                'speed': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float32),
            }),
            
            # Current score
            'score': spaces.Box(low=-np.inf, high=np.inf, shape=(), dtype=np.float32),
            
            # Production flows
            'flows': spaces.Dict({
                'input': spaces.Sequence(spaces.Dict({
                    'type': AllCharText(max_length=200),
                    'rate': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float32),
                })),
                'output': spaces.Sequence(spaces.Dict({
                    'type': AllCharText(max_length=200),
                    'rate': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float32),
                })),
                'crafted': spaces.Sequence(spaces.Dict({
                    'crafted_count': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.int32),
                    'inputs': spaces.Dict({
                        'type': AllCharText(max_length=200),
                        'amount': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float32),
                    }),
                    'outputs': spaces.Dict({
                        'type': AllCharText(max_length=200),
                        'amount': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float32),
                    }),
                })),
                'harvested': spaces.Sequence(spaces.Dict({
                    'type': AllCharText(max_length=200),
                    'amount': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float32),
                })),
                'price_list': spaces.Sequence(spaces.Dict({
                    'type': AllCharText(max_length=200),
                    'price': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float32),
                })),
                'static_items': spaces.Sequence(spaces.Dict({
                    'type': AllCharText(max_length=200),
                    'value': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float32),
                })),
            }),
            
            # Task verification status
            'task_verification': spaces.Dict({
                'success': spaces.Discrete(2),  # 0 or 1
                'meta': spaces.Sequence(spaces.Dict({
                    'key': AllCharText(max_length=200),
                    'value': AllCharText(max_length=1000),
                })),
            }),
            
            # Messages from other agents
            'messages': spaces.Sequence(spaces.Dict({
                'sender': AllCharText(max_length=200),
                'content': AllCharText(max_length=1000),
                'timestamp': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float32),
            })),
            
            # Serialized functions
            'serialized_functions': spaces.Sequence(spaces.Dict({
                'name': AllCharText(max_length=200),
                'pickled_function': AllCharText(max_length=10000),  # Pickled function as hex string
            })),
        })
        
        self.current_state = None
        self.initial_score = 0
        self.last_observation = None
        # Track last message timestamp for each agent
        self.last_message_timestamps = {i: 0.0 for i in range(instance.num_agents)}
     
    def get_observation(self, agent_idx: int = 0, response: Optional[Response] = None) -> Observation:
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
            speed=self.instance._speed
        )
        
        # Get flows
        flows = namespace._get_production_stats()
        flows_obs = ProductionFlows.from_dict(flows)
        
        # Get messages
        messages = namespace.get_messages()
        messages_obs = []
        latest_timestamp = self.last_message_timestamps[agent_idx]

        for msg in messages:
            if msg['timestamp'] > self.last_message_timestamps[agent_idx]:
                messages_obs.append(AgentMessage(
                    sender=msg['sender'],
                    content=msg['message'],
                    timestamp=msg['timestamp']
                ))
                latest_timestamp = max(latest_timestamp, msg['timestamp'])

        # Update last message timestamp
        if messages_obs:
            self.last_message_timestamps[agent_idx] = latest_timestamp
        
        # Get task verification if available
        task_verification = None
        if response and hasattr(response, 'task'):
            task_verification = TaskResponse(
                success=response.task.success,
                meta=response.task.meta if hasattr(response.task, 'meta') else {}
            )
        
        # Get serialized functions
        serialized_functions = []
        for func in namespace.get_functions():
            serialized_functions.append({
                'name': func.name,
                'pickled_function': pickle.dumps(func).hex()
            })
        
        observation = Observation(
            raw_text=response.response if response else '',
            entities=entity_obs,  # Convert entities to strings
            inventory=inventory_obs,
            research=research_obs,
            game_info=game_info,
            score=response.score if response else 0.0,
            flows=flows_obs,
            task_verification=task_verification,
            messages=messages_obs,
            serialized_functions=serialized_functions
        )
        
        # Store observation for next step
        self.last_observation = observation
        
        return observation
        
    def step(self, action: Dict[str, Any]) -> Tuple[Dict[str, Any], float, bool, Dict[str, Any]]:
        """
        Execute one step in the environment
        
        Args:
            action: Dictionary containing:
                - agent_idx: int - Index of the agent taking the action
                - game_state: GameState - GameState to reset to before executing the action
                - code: str - Python code string to execute
            
        Returns:
            observation: The new observation as a dictionary matching the observation space
            reward: The reward for this step
            done: Whether the episode is done
            info: Additional information
        """
        agent_idx = action['agent_idx']
        code = action['code']
        game_state_raw = action['game_state']
        if game_state_raw == '':
            # Use the current game state from the instance if empty string is provided
            game_state = GameState.from_instance(self.instance)
        else:
            game_state = GameState.parse_raw(game_state_raw)
        
        self.reset_instance(game_state)
        # Get initial state information
        namespace = self.instance.namespaces[agent_idx]
        start_production_flows = ProductionFlows.from_dict(namespace._get_production_stats())
        initial_score, _ = namespace.score()
        
        # Execute the action
        score, eval_time, result = self.instance.eval(code, agent_idx=agent_idx, timeout=60)
        
        # Check for errors
        error_occurred = "error" in result.lower() or "exception: " in result.lower()
        
        # Calculate reward
        if error_occurred:
            reward = -self.error_penalty
        else:
            # Wait for value accrual
            time.sleep(self.value_accrual_time)
            reward = score - initial_score
        
        # Get task verification if task exists
        task_response = task_success = None
        done = False
        if self.task:
            # First get the raw verification
            task_success = self.task.verify(reward, self.instance, step_statistics={})
            # Then enhance the response with task output
            task_response = self.task.enhance_response_with_task_output(result, task_success)
            done = task_success.success

        # Get post-execution flows and calculate achievements
        current_flows = ProductionFlows.from_dict(namespace._get_production_stats())
        achievements = get_achievements(start_production_flows.__dict__, current_flows.__dict__)
            
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
            program_id=None
        )
        
        # Get observation for the acting agent
        observation = self.get_observation(agent_idx, response)
        
        # Get additional info
        info = {
            'error_occurred': error_occurred,
            'result': result,
            'ticks': self.instance.get_elapsed_ticks(),
            'flows': response.flows,
            'agent_idx': agent_idx,
            'last_message_timestamp': self.last_message_timestamps[agent_idx],
            'task_verification': task_response
        }
        
        return observation.to_dict(), reward, done, info

    def reset_instance(self, state: Optional[GameState] = None) -> None:
        """Reset the Factorio instance to a given state or initial state.
        
        Args:
            state: Optional GameState to reset to. If None, resets to initial state.
        """
        self.instance.reset(state)

    def reset(self, options: Dict[str, Any], seed: Optional[int] = None) -> Dict[str, Any]:
        """Reset the environment to initial state"""
        game_state = options.get('state', None)
        self.reset_instance(game_state)
        self.initial_score, _ = self.instance.namespaces[0].score()
        self.last_observation = None  # Reset last observation
        # Reset message timestamps
        self.last_message_timestamps = {i: 0.0 for i in range(self.instance.num_agents)}
        # Convert observation to dictionary to match gym standards
        observation = self.get_observation(0).to_dict()
        return observation, {} # Return observation for first agent
        
    def close(self):
        """Clean up resources"""
        self.instance.cleanup()
