from gym.utils.env_checker import check_env
from fle.env.gym_env.environment import FactorioGymEnv
from fle.env import FactorioInstance
# from fle.env.gym_env.validation import validate_observation
from fle.env.entities import Position, Direction
from fle.env.game_types import Prototype

def test_reset_observation(instance):
    env = FactorioGymEnv(instance)
    observation, info = env.reset()
    # validate_observation(observation, env.observation_space)

def test_inventory_observation(instance):
    """Test that inventory changes are reflected in observations."""
    # Set up initial inventory
    instance.initial_inventory = {
        'coal': 50,
        'iron-chest': 1,
        'iron-plate': 5,
    }
    instance.reset()
    
    env = FactorioGymEnv(instance)
    observation, info = env.reset()
    
    # Verify initial inventory in observation
    inventory_items = {item['type']: item['quantity'] for item in observation['inventory']}
    assert inventory_items['coal'] == 50
    assert inventory_items['iron-chest'] == 1
    assert inventory_items['iron-plate'] == 5
    
    # Place a chest and insert items
    chest = instance.namespace.place_entity(Prototype.IronChest, position=Position(x=2.5, y=2.5))
    chest = instance.namespace.insert_item(Prototype.Coal, chest, quantity=10)
    
    # Get new observation using a no-op action
    no_op_action = {
        'agent_idx': 0,
        'code': 'pass'  # No-op Python code
    }
    observation, reward, done, info = env.step(no_op_action)
    
    # Verify chest in observation
    chest_entities = [e for e in observation['entities'] if 'iron-chest' in e]
    assert len(chest_entities) == 1
    # Verify the chest string representation contains the expected information
    chest_str = chest_entities[0]
    assert 'iron-chest' in chest_str
    assert 'x=2.5, y=2.5' in chest_str

def test_entity_placement_observation(instance):
    """Test that entity placement is reflected in observations."""
    instance.initial_inventory = {
        'stone-furnace': 1,
        'coal': 50,
        'iron-ore': 10
    }
    instance.reset()
    
    env = FactorioGymEnv(instance)
    observation, info = env.reset()
    
    # Verify initial state
    assert len(observation['entities']) == 0
    
    # Place a furnace
    furnace = instance.namespace.place_entity(
        Prototype.StoneFurnace,
        direction=Direction.UP,
        position=Position(x=2.5, y=2.5)
    )
    
    # Get new observation using a no-op action
    no_op_action = {
        'agent_idx': 0,
        'code': 'pass'  # No-op Python code
    }
    observation, reward, done, info = env.step(no_op_action)
    
    # Verify furnace in observation
    furnace_entities = [e for e in observation['entities'] if 'stone-furnace' in e]
    assert len(furnace_entities) == 1
    furnace_str = furnace_entities[0]
    # Verify the furnace string representation contains the expected information
    assert 'stone-furnace' in furnace_str
    assert 'x=3.0, y=3.0' in furnace_str
    assert 'Direction.UP' in furnace_str

