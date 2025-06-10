import asyncio
import time
import gym
import numpy as np
from gym import spaces
from typing import Dict, List, Optional, Tuple, Union, Any
import pickle
import datetime

from env.src.instance import FactorioInstance
from env.src.models.game_state import GameState
from env.src.models.achievements import ProductionFlows
from env.src.entities import EntityStatus
from env.src.utils.profits import get_achievements
from agents import Response, TaskResponse
from env.src.gym_env.observation import (
    Observation, 
    GameInfo, 
    Achievement, 
    AgentMessage,
)
from eval.tasks.task_abc import TaskABC


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
            'code': spaces.Text(max_length=10000)  # The Python code to execute
        })
        
        # Define observation space with expanded fields
        self.observation_space = spaces.Dict({
            # Raw text output from the last action
            'raw_text': spaces.Text(max_length=10000),
            
            # Entities on the map - now as text representations
            'entities': spaces.Sequence(spaces.Text(max_length=1000)),  # Each entity's repr string
            
            # Current inventory state
            'inventory': spaces.Sequence(spaces.Dict({
                'type': spaces.Text(max_length=200),
                'quantity': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.int32),
            })),
            
            # Research state
            'research': spaces.Dict({
                'technologies': spaces.Sequence(spaces.Dict({
                    'name': spaces.Text(max_length=200),
                    'researched': spaces.Discrete(2),  # 0 or 1
                    'enabled': spaces.Discrete(2),  # 0 or 1
                    'level': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.int32),
                    'research_unit_count': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.int32),
                    'research_unit_energy': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float32),
                    'prerequisites': spaces.Sequence(spaces.Text(max_length=200)),
                    'ingredients': spaces.Sequence(spaces.Dict({
                        'item': spaces.Text(max_length=200),
                        'amount': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.int32),
                    })),
                })),
                'current_research': spaces.Text(max_length=200),
                'research_progress': spaces.Box(low=0, high=1, shape=(), dtype=np.float32),
                'research_queue': spaces.Sequence(spaces.Text(max_length=200)),
                'progress': spaces.Sequence(spaces.Dict({
                    'name': spaces.Text(max_length=200),
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
            
            # Achievements
            'achievements': spaces.Sequence(spaces.Dict({
                'static': spaces.Dict({
                    'type': spaces.Text(max_length=200),
                    'value': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float32),
                }),
                'dynamic': spaces.Dict({
                    'type': spaces.Text(max_length=200),
                    'value': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float32),
                }),
            })),
            
            # Production flows
            'flows': spaces.Dict({
                'input': spaces.Sequence(spaces.Dict({
                    'type': spaces.Text(max_length=200),
                    'rate': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float32),
                })),
                'output': spaces.Sequence(spaces.Dict({
                    'type': spaces.Text(max_length=200),
                    'rate': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float32),
                })),
                'crafted': spaces.Sequence(spaces.Dict({
                    'crafted_count': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.int32),
                    'inputs': spaces.Dict({
                        'type': spaces.Text(max_length=200),
                        'amount': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float32),
                    }),
                    'outputs': spaces.Dict({
                        'type': spaces.Text(max_length=200),
                        'amount': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float32),
                    }),
                })),
                'harvested': spaces.Sequence(spaces.Dict({
                    'type': spaces.Text(max_length=200),
                    'amount': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float32),
                })),
                'price_list': spaces.Sequence(spaces.Dict({
                    'type': spaces.Text(max_length=200),
                    'price': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float32),
                })),
                'static_items': spaces.Sequence(spaces.Dict({
                    'type': spaces.Text(max_length=200),
                    'value': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float32),
                })),
            }),
            
            # Task verification status
            'task_verification': spaces.Dict({
                'success': spaces.Discrete(2),  # 0 or 1
                'meta': spaces.Sequence(spaces.Dict({
                    'key': spaces.Text(max_length=200),
                    'value': spaces.Text(max_length=1000),
                })),
            }),
            
            # Messages from other agents
            'messages': spaces.Sequence(spaces.Dict({
                'sender': spaces.Text(max_length=200),
                'content': spaces.Text(max_length=1000),
                'timestamp': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float32),
            })),
            
            # Serialized functions
            'serialized_functions': spaces.Sequence(spaces.Dict({
                'name': spaces.Text(max_length=200),
                'pickled_function': spaces.Text(max_length=10000),  # Pickled function as hex string
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
        
        # Get achievements if available
        achievements = []
        if response and hasattr(response, 'achievements'):
            achievements.append(Achievement.from_dict(response.achievements))
        
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
            achievements=achievements,
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
                - agent_idx: Index of the agent taking the action
                - code: Python code string to execute
            
        Returns:
            observation: The new observation as a dictionary matching the observation space
            reward: The reward for this step
            done: Whether the episode is done
            info: Additional information
        """
        agent_idx = action['agent_idx']
        code = action['code']
        
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
            'task_verification': task_response,
            'achievements': achievements  # Add achievements to info
        }
        
        return observation.to_dict(), reward, done, info

    def reset_instance(self, state: Optional[GameState] = None) -> None:
        """Reset the Factorio instance to a given state or initial state.
        
        Args:
            state: Optional GameState to reset to. If None, resets to initial state.
        """
        self.instance.reset(state)

    def reset(self, state: Optional[GameState] = None) -> Dict[str, Any]:
        """Reset the environment to initial state"""
        self.reset_instance(state)
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
