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
from env.src.models.program import Program
from env.src.models.achievements import ProductionFlows
from env.src.entities import Entity, EntityStatus, Direction, Position, Dimensions, TileDimensions
from env.src.models.technology_state import TechnologyState
from env.src.models.research_state import ResearchState
from agents import Response, TaskResponse
from env.src.gym_env.observation import (
    Observation, 
    GameInfo, 
    StateChanges, 
    Achievement, 
    AgentMessage,
    EntityChange,
    InventoryChange
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
            
            # Any errors that occurred
            'errors': spaces.Sequence(spaces.Text(max_length=2000)),
            
            # Entities on the map
            'entities': spaces.Sequence(spaces.Dict({
                'name': spaces.Text(max_length=200),
                'direction': spaces.Discrete(8),  # 8 possible directions
                'position': spaces.Box(low=-np.inf, high=np.inf, shape=(2,), dtype=np.float32),
                'energy': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float32),
                'dimensions': spaces.Dict({
                    'width': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float32),
                    'height': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float32),
                }),
                'tile_dimensions': spaces.Dict({
                    'tile_width': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float32),
                    'tile_height': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float32),
                }),
                'health': spaces.Box(low=0, high=1, shape=(), dtype=np.float32),
                'status': spaces.Discrete(len(EntityStatus)),  # Number of possible status values
                'warnings': spaces.Sequence(spaces.Text(max_length=200)),
                'id': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.int32),
                'type': spaces.Text(max_length=200),
            })),
            
            # Current inventory state
            'inventory': spaces.Dict({
                'type': spaces.Text(max_length=200),
                'quantity': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.int32),
            }),
            
            # Research state
            'research': spaces.Dict({
                'technologies': spaces.Dict({
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
                }),
                'current_research': spaces.Text(max_length=200),
                'research_progress': spaces.Box(low=0, high=1, shape=(), dtype=np.float32),
                'research_queue': spaces.Sequence(spaces.Text(max_length=200)),
                'progress': spaces.Dict({
                    'name': spaces.Text(max_length=200),
                    'value': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float32),
                }),
            }),
            
            # Game information
            'game_info': spaces.Dict({
                'tick': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.int32),
                'time': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float32),
                'speed': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float32),
            }),
            
            # State changes since last step
            'state_changes': spaces.Dict({
                'inventory_changes': spaces.Sequence(spaces.Dict({
                    'item': spaces.Text(max_length=200),
                    'change': spaces.Box(low=-np.inf, high=np.inf, shape=(), dtype=np.int32),
                })),
                'entity_changes': spaces.Sequence(spaces.Dict({
                    'entity': spaces.Text(max_length=200),
                    'change': spaces.Box(low=-np.inf, high=np.inf, shape=(), dtype=np.int32),
                })),
            }),
            
            # Current score
            'score': spaces.Box(low=-np.inf, high=np.inf, shape=(), dtype=np.float32),
            
            # Achievements
            'achievements': spaces.Dict({
                'name': spaces.Text(max_length=200),
                'progress': spaces.Box(low=0, high=1, shape=(), dtype=np.float32),
            }),
            
            # Production flows
            'flows': spaces.Dict({
                'input': spaces.Dict({
                    'type': spaces.Text(max_length=200),
                    'rate': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float32),
                }),
                'output': spaces.Dict({
                    'type': spaces.Text(max_length=200),
                    'rate': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float32),
                }),
                'crafted': spaces.Sequence(spaces.Dict({
                    'name': spaces.Text(max_length=200),
                    'count': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.int32),
                })),
                'harvested': spaces.Dict({
                    'type': spaces.Text(max_length=200),
                    'amount': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float32),
                }),
                'price_list': spaces.Dict({
                    'type': spaces.Text(max_length=200),
                    'price': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float32),
                }),
                'static_items': spaces.Dict({
                    'type': spaces.Text(max_length=200),
                    'value': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float32),
                }),
            }),
            
            # Task verification status
            'task_verification': spaces.Dict({
                'success': spaces.Discrete(2),  # 0 or 1
                'message': spaces.Text(max_length=200),
                'meta': spaces.Dict({
                    'key': spaces.Text(max_length=200),
                    'value': spaces.Text(max_length=1000),
                }),
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
        
        # Get entities
        entities = namespace.get_entities()
        entity_obs = [
            Entity(
                name=entity.type,
                direction=Direction(entity.direction.value if hasattr(entity, 'direction') else 0),
                position=Position(x=entity.position.x, y=entity.position.y),
                energy=entity.energy if hasattr(entity, 'energy') else 0.0,
                dimensions=Dimensions(
                    width=entity.dimensions.width if hasattr(entity, 'dimensions') else 1.0,
                    height=entity.dimensions.height if hasattr(entity, 'dimensions') else 1.0
                ),
                tile_dimensions=TileDimensions(
                    tile_width=entity.tile_dimensions.tile_width if hasattr(entity, 'tile_dimensions') else 1.0,
                    tile_height=entity.tile_dimensions.tile_height if hasattr(entity, 'tile_dimensions') else 1.0
                ),
                prototype=None,
                health=entity.health if hasattr(entity, 'health') else 1.0,
                status=entity.status if hasattr(entity, 'status') else EntityStatus.NORMAL,
                warnings=entity.warnings if hasattr(entity, 'warnings') else [],
                id=entity.id if hasattr(entity, 'id') else None,
                type=entity.type
            )
            for entity in entities
        ]
            
        # Get inventory
        inventory = namespace.inspect_inventory()
        inventory_obs = inventory  # Now we can use the Inventory object directly
        
        # Get research state
        research_state = namespace._save_research_state()
        research_obs = ResearchState(
            technologies={
                name: TechnologyState(
                    name=name,
                    researched=tech_state.researched,
                    enabled=tech_state.enabled,
                    level=tech_state.level,
                    research_unit_count=tech_state.research_unit_count,
                    research_unit_energy=tech_state.research_unit_energy,
                    prerequisites=tech_state.prerequisites,
                    ingredients=tech_state.ingredients
                )
                for name, tech_state in research_state.technologies.items()
            },
            current_research=research_state.current_research,
            research_progress=research_state.research_progress,
            research_queue=research_state.research_queue,
            progress=research_state.progress
        )
        
        # Get game info
        game_info = GameInfo(
            tick=self.instance.get_elapsed_ticks(),
            time=self.instance.get_elapsed_ticks() / 60,
            speed=self.instance._speed
        )
        
        # Get production flows
        flows = namespace._get_production_stats()
        flows_obs = ProductionFlows(
            input=flows.get('inputs', {}),
            output=flows.get('outputs', {}),
            crafted=flows.get('crafted', []),
            harvested=flows.get('harvested', {}),
            price_list=flows.get('price_list'),
            static_items=flows.get('static_items')
        )
        
        # Get messages and update timestamp
        messages = namespace.get_messages()
        message_obs = []
        latest_timestamp = self.last_message_timestamps[agent_idx]
        
        for msg in messages:
            if msg['timestamp'] > self.last_message_timestamps[agent_idx]:
                message_obs.append(AgentMessage(
                    sender=str(msg['sender']),
                    content=msg['message'],
                    timestamp=msg['timestamp']
                ))
                latest_timestamp = max(latest_timestamp, msg['timestamp'])
        
        # Update last message timestamp
        if message_obs:
            self.last_message_timestamps[agent_idx] = latest_timestamp
        
        # Get task verification if available
        task_verification = None
        if response and hasattr(response, 'task'):
            task_verification = TaskResponse(
                success=response.task.success,
                message=response.task.message,
                meta=response.task.meta if hasattr(response.task, 'meta') else {}
            )
        
        # Get achievements if available
        achievements = None
        if response and hasattr(response, 'achievements'):
            achievements = Achievement(
                name=response.achievements.name,
                progress=response.achievements.progress
            )
        
        # Get state changes by comparing with last observation
        state_changes = StateChanges(
            inventory_changes=[],
            entity_changes=[]
        )
        if self.last_observation:
            # Compare entities
            last_entities = {e.name: e for e in self.last_observation.entities}
            current_entities = {e.name: e for e in entity_obs}
            
            # Aggregate entity changes by type
            entity_changes = {}
            for entity_name in current_entities:
                if entity_name not in last_entities:
                    entity_changes[entity_name] = entity_changes.get(entity_name, 0) + 1
            for entity_name in last_entities:
                if entity_name not in current_entities:
                    entity_changes[entity_name] = entity_changes.get(entity_name, 0) - 1
                    
            # Add non-zero changes to state_changes
            for entity_name, change in entity_changes.items():
                if change != 0:  # Only include non-zero changes
                    state_changes.entity_changes.append(EntityChange(entity=entity_name, change=change))
            
            # Compare inventory
            last_inv = self.last_observation.inventory
            current_inv = inventory_obs
            for item, quantity in current_inv.items():
                if item not in last_inv or quantity != last_inv[item]:
                    state_changes.inventory_changes.append(InventoryChange(
                        item=item,
                        change=quantity - last_inv.get(item, 0)
                    ))
        
        # Get serialized functions
        serialized_functions = []
        for func in namespace.get_functions():
            serialized_functions.append({
                'name': func.name,
                'pickled_function': pickle.dumps(func).hex()
            })

        # Parse logging results from response
        logging_results = {}
        if response and response.response:
            for line in response.response.split('\n'):
                if ':' in line:
                    try:
                        line_num, value = line.split(':', 1)
                        line_num = int(line_num.strip())
                        value = value.strip()
                        if line_num not in logging_results:
                            logging_results[line_num] = []
                        logging_results[line_num].append((line_num, value))
                    except ValueError:
                        print(f"Error parsing logging result: {line}")
                        continue
        
        observation = Observation(
            raw_text=response.response if response else '',
            errors=[str(e) for e in response.errors] if response and hasattr(response, 'errors') else [],
            entities=entity_obs,
            inventory=inventory_obs,
            research=research_obs,
            game_info=game_info,
            state_changes=state_changes,
            score=response.score if response else 0.0,
            achievements=achievements,
            flows=flows_obs,
            task_verification=task_verification,
            messages=message_obs,
            serialized_functions=serialized_functions,
            logging_results=logging_results
        )
        
        # Store current observation for next state change comparison
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
        try:
            agent_idx = action['agent_idx']
            code = action['code']
            
            # Get initial state information
            namespace = self.instance.namespaces[agent_idx]
            start_production_flows = namespace._get_production_stats()
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
                # asyncio.run(asyncio.sleep(self.value_accrual_time))
                time.sleep(self.value_accrual_time)
                reward = score - initial_score
            
            # Get task verification if task exists
            task_response = None
            done = False
            if self.task:
                # First get the raw verification
                task_success = self.task.verify(reward, self.instance, step_statistics={})
                # Then enhance the response with task output
                task_response = self.task.enhance_response_with_task_output(result, task_success)
                done = task_success

            current_flows = ProductionFlows.from_dict(namespace._get_production_stats())
                
            # Create response object for observation
            response = Response(
                code=f"```python\n{code}\n```",
                created_at=datetime.datetime.now(),
                score=reward,
                achievements={},  # Empty dict instead of None
                step=0,
                ticks=self.instance.get_elapsed_ticks(),
                flows=ProductionFlows.from_dict(start_production_flows).get_new_flows(current_flows),
                response=result,
                task=TaskResponse(success=task_success if self.task else False, meta={}) if not isinstance(task_response, TaskResponse) else task_response,
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
            
        except Exception as e:
            print(f"Error in step: {str(e)}")
            raise e

    def reset_instance(self, state: Optional[GameState] = None) -> None:
        """Reset the Factorio instance to a given state or initial state.
        
        Args:
            state: Optional GameState to reset to. If None, resets to initial state.
        """
        self.instance.reset(state)

    def eval(self, code: str, agent_idx: int, timeout: int = 60) -> Tuple[float, float, str]:
        """Execute code in the Factorio instance.
        
        Args:
            code: Python code string to execute
            agent_idx: Index of the agent executing the code
            timeout: Maximum time in seconds to wait for execution
            
        Returns:
            Tuple of (reward, time, result)
        """
        return self.instance.eval(code, agent_idx=agent_idx, timeout=timeout)

            
    def reset(self, state: Optional[GameState] = None) -> Dict[str, Any]:
        """Reset the environment to initial state"""
        self.reset_instance(state)
        self.initial_score, _ = self.instance.namespaces[0].score()
        self.last_observation = None  # Reset last observation
        # Reset message timestamps
        self.last_message_timestamps = {i: 0.0 for i in range(self.instance.num_agents)}
        # Convert observation to dictionary to match gym standards
        return self.get_observation(0).to_dict()  # Return observation for first agent
        
    def close(self):
        """Clean up resources"""
        self.instance.cleanup()
