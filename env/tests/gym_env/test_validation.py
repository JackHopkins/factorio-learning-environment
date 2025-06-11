import pytest
import numpy as np
from gym import spaces
from env.src.gym_env.validation import validate_observation, validate_dict

def test_validate_text_space():
    """Test validation of Text spaces."""
    space = spaces.Dict({
        'text': spaces.Text(max_length=10)
    })
    
    # Valid observation
    valid_obs = {'text': 'hello'}
    validate_observation(valid_obs, space)
    
    # Invalid type
    with pytest.raises(AssertionError, match="expected str"):
        validate_observation({'text': 123}, space)
    
    # Too long
    with pytest.raises(AssertionError, match="exceeds max length"):
        validate_observation({'text': 'a' * 11}, space)

def test_validate_box_space():
    """Test validation of Box spaces."""
    space = spaces.Dict({
        'scalar': spaces.Box(low=0, high=1, shape=(), dtype=np.float32),
        'vector': spaces.Box(low=-1, high=1, shape=(2,), dtype=np.float32),
        'matrix': spaces.Box(low=0, high=1, shape=(2, 2), dtype=np.float32)
    })
    
    # Valid observations
    valid_obs = {
        'scalar': 0.5,
        'vector': np.array([0.5, -0.5], dtype=np.float32),
        'matrix': np.array([[0.5, 0.5], [0.5, 0.5]], dtype=np.float32)
    }
    validate_observation(valid_obs, space)
    
    # Invalid scalar type
    with pytest.raises(AssertionError, match="expected array-like or scalar"):
        validate_observation({'scalar': '0.5', 'vector': valid_obs['vector'], 'matrix': valid_obs['matrix']}, space)
    
    # Invalid vector shape
    with pytest.raises(AssertionError, match="invalid shape"):
        validate_observation({'scalar': 0.5, 'vector': np.array([0.5], dtype=np.float32), 'matrix': valid_obs['matrix']}, space)
    
    # Out of bounds
    with pytest.raises(AssertionError, match="out of bounds"):
        validate_observation({'scalar': 2.0, 'vector': valid_obs['vector'], 'matrix': valid_obs['matrix']}, space)

def test_validate_discrete_space():
    """Test validation of Discrete spaces."""
    space = spaces.Dict({
        'action': spaces.Discrete(3)  # Valid values: 0, 1, 2
    })
    
    # Valid observation
    validate_observation({'action': 1}, space)
    
    # Invalid type
    with pytest.raises(AssertionError, match="expected int"):
        validate_observation({'action': 1.5}, space)
    
    # Out of range
    with pytest.raises(AssertionError, match="out of range"):
        validate_observation({'action': 3}, space)

def test_validate_sequence_space():
    """Test validation of Sequence spaces."""
    space = spaces.Dict({
        'strings': spaces.Sequence(spaces.Text(max_length=5)),
        'numbers': spaces.Sequence(spaces.Box(low=0, high=1, shape=(), dtype=np.float32))
    })
    
    # Valid observation
    valid_obs = {
        'strings': ['hello', 'world'],
        'numbers': [0.5, 0.7]
    }
    validate_observation(valid_obs, space)
    
    # Invalid sequence type
    with pytest.raises(AssertionError, match="expected list or tuple"):
        validate_observation({'strings': 'hello', 'numbers': valid_obs['numbers']}, space)
    
    # Invalid item type in sequence
    with pytest.raises(AssertionError, match="expected str"):
        validate_observation({'strings': [123], 'numbers': valid_obs['numbers']}, space)

def test_validate_nested_dict_space():
    """Test validation of nested Dict spaces."""
    space = spaces.Dict({
        'player': spaces.Dict({
            'position': spaces.Box(low=-10, high=10, shape=(2,), dtype=np.float32),
            'health': spaces.Box(low=0, high=100, shape=(), dtype=np.float32),
            'inventory': spaces.Sequence(spaces.Dict({
                'item': spaces.Text(max_length=20),
                'quantity': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.int32)
            }))
        })
    })
    
    # Valid observation
    valid_obs = {
        'player': {
            'position': np.array([5.0, -3.0], dtype=np.float32),
            'health': 75.0,
            'inventory': [
                {'item': 'sword', 'quantity': 1},
                {'item': 'potion', 'quantity': 5}
            ]
        }
    }
    validate_observation(valid_obs, space)
    
    # Missing required key
    with pytest.raises(AssertionError, match="missing required key"):
        validate_observation({'player': {'position': valid_obs['player']['position']}}, space)
    
    # Invalid nested value
    with pytest.raises(AssertionError, match="out of bounds"):
        validate_observation({
            'player': {
                'position': np.array([20.0, 0.0], dtype=np.float32),
                'health': valid_obs['player']['health'],
                'inventory': valid_obs['player']['inventory']
            }
        }, space)

def test_validate_complex_space():
    """Test validation of a complex space with multiple nested structures."""
    space = spaces.Dict({
        'game_state': spaces.Dict({
            'score': spaces.Box(low=0, high=np.inf, shape=(), dtype=np.float32),
            'entities': spaces.Sequence(spaces.Dict({
                'type': spaces.Text(max_length=20),
                'position': spaces.Box(low=-100, high=100, shape=(2,), dtype=np.float32),
                'status': spaces.Discrete(3),
                'properties': spaces.Dict({
                    'health': spaces.Box(low=0, high=1, shape=(), dtype=np.float32),
                    'energy': spaces.Box(low=0, high=100, shape=(), dtype=np.float32)
                })
            })),
            'messages': spaces.Sequence(spaces.Text(max_length=100))
        })
    })
    
    # Valid observation
    valid_obs = {
        'game_state': {
            'score': 1000.0,
            'entities': [
                {
                    'type': 'player',
                    'position': np.array([10.0, 20.0], dtype=np.float32),
                    'status': 1,
                    'properties': {
                        'health': 0.8,
                        'energy': 75.0
                    }
                }
            ],
            'messages': ['Game started', 'Player moved']
        }
    }
    validate_observation(valid_obs, space)
    
    # Invalid nested structure
    with pytest.raises(AssertionError, match="has invalid type"):
        validate_observation({
            'game_state': {
                'score': 1000.0,
                'entities': [
                    {
                        'type': 'player',
                        'position': 'invalid',  # Should be numpy array
                        'status': 1,
                        'properties': {
                            'health': 0.8,
                            'energy': 75.0
                        }
                    }
                ],
                'messages': ['Game started']
            }
        }, space)
    
    # Invalid value in nested sequence
    with pytest.raises(AssertionError, match="out of range"):
        validate_observation({
            'game_state': {
                'score': 1000.0,
                'entities': [
                    {
                        'type': 'player',
                        'position': np.array([10.0, 20.0], dtype=np.float32),
                        'status': 3,  # Should be 0, 1, or 2
                        'properties': {
                            'health': 0.8,
                            'energy': 75.0
                        }
                    }
                ],
                'messages': ['Game started']
            }
        }, space)
