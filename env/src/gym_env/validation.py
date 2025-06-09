from typing import Dict, Any
import numpy as np
from gym import spaces

def validate_observation(observation: Dict[str, Any], observation_space: spaces.Space, method: str = "unknown", path: str = "") -> None:
    """
    Validate an observation against the environment's observation space.
    
    Args:
        observation: The observation to validate.
        observation_space: The space to validate against.
        method (str): The method that generated the observation (e.g., 'reset', 'step').
        path (str): The current path in the observation tree for error reporting.
    
    Raises:
        AssertionError: If the observation does not conform to the observation space.
    """
    if not isinstance(observation, dict):
        raise AssertionError(
            f"Observation from {method} at {path} is invalid: "
            f"got type {type(observation)}, expected dict for {observation_space}"
        )

    # Validate top-level Dict space
    if not isinstance(observation_space, spaces.Dict):
        raise AssertionError(
            f"Observation space at {path} is not a Dict space: "
            f"got {observation_space}"
        )

    # Check for unexpected keys
    for key in observation:
        if key not in observation_space.spaces:
            raise AssertionError(
                f"Observation from {method} at {path} contains unexpected key: {key}"
            )

    # Check each field in the observation space
    for key, space in observation_space.spaces.items():
        new_path = f"{path}.{key}" if path else key
        if key not in observation:
            raise AssertionError(
                f"Observation from {method} at {new_path} is missing required key: {key}"
            )
        value = observation[key]

        # Handle Text space
        if isinstance(space, spaces.Text):
            if not isinstance(value, str):
                raise AssertionError(
                    f"Observation from {method} at {new_path} has invalid type: "
                    f"got {type(value)}, expected str for {space}"
                )
            if len(value) > space.max_length:
                raise AssertionError(
                    f"Observation from {method} at {new_path} exceeds max length: "
                    f"got length {len(value)}, expected <= {space.max_length} for {space}"
                )

        # Handle Sequence space
        elif isinstance(space, spaces.Sequence):
            if not isinstance(value, (list, tuple)):
                raise AssertionError(
                    f"Observation from {method} at {new_path} has invalid type: "
                    f"got {type(value)}, expected list or tuple for {space}"
                )
            for i, item in enumerate(value):
                item_path = f"{new_path}[{i}]"
                # Recursively validate each item in the sequence
                if isinstance(space.feature_space, spaces.Text):
                    if not isinstance(item, str):
                        raise AssertionError(
                            f"Observation from {method} at {item_path} has invalid type: "
                            f"got {type(item)}, expected str for {space.feature_space}"
                        )
                    if len(item) > space.feature_space.max_length:
                        raise AssertionError(
                            f"Observation from {method} at {item_path} exceeds max length: "
                            f"got length {len(item)}, expected <= {space.feature_space.max_length} for {space.feature_space}"
                        )
                elif isinstance(space.feature_space, spaces.Dict):
                    if not isinstance(item, dict):
                        raise AssertionError(
                            f"Observation from {method} at {item_path} has invalid type: "
                            f"got {type(item)}, expected dict for {space.feature_space}"
                        )
                    # Recursively validate nested Dict
                    validate_dict(item, space.feature_space, method, item_path)
                elif isinstance(space.feature_space, spaces.Box):
                    if not isinstance(item, (np.ndarray, float, int)):
                        raise AssertionError(
                            f"Observation from {method} at {item_path} has invalid type: "
                            f"got {type(item)}, expected array-like or scalar for {space.feature_space}"
                        )
                    # Convert scalar to array for scalar Box spaces
                    value_array = np.asarray(item, dtype=space.feature_space.dtype)
                    if space.feature_space.shape == ():
                        expected_shape = ()
                    else:
                        expected_shape = space.feature_space.shape
                    if value_array.shape != expected_shape:
                        raise AssertionError(
                            f"Observation from {method} at {item_path} has invalid shape: "
                            f"got {value_array.shape}, expected {expected_shape} for {space.feature_space}"
                        )
                    if value_array.dtype != space.feature_space.dtype:
                        raise AssertionError(
                            f"Observation from {method} at {item_path} has invalid dtype: "
                            f"got {value_array.dtype}, expected {space.feature_space.dtype} for {space.feature_space}"
                        )
                    # Check bounds (skip if infinite)
                    if not (np.all(np.isinf(space.feature_space.low)) and np.all(np.isinf(space.feature_space.high))):
                        if not np.all((value_array >= space.feature_space.low) & (value_array <= space.feature_space.high)):
                            raise AssertionError(
                                f"Observation from {method} at {item_path} out of bounds: "
                                f"got {value_array}, expected values in "
                                f"[{space.feature_space.low}, {space.feature_space.high}] for {space.feature_space}"
                            )
                else:
                    raise AssertionError(
                        f"Unsupported sequence subspace at {item_path}: {space.feature_space}"
                    )

        # Handle Dict space
        elif isinstance(space, spaces.Dict):
            if not isinstance(value, dict):
                raise AssertionError(
                    f"Observation from {method} at {new_path} has invalid type: "
                    f"got {type(value)}, expected dict for {space}"
                )
            validate_dict(value, space, method, new_path)

        # Handle Box space
        elif isinstance(space, spaces.Box):
            if not isinstance(value, (np.ndarray, float, int)):
                raise AssertionError(
                    f"Observation from {method} at {new_path} has invalid type: "
                    f"got {type(value)}, expected array-like or scalar for {space}"
                )
            # Convert scalar to array for scalar Box spaces
            value_array = np.asarray(value, dtype=space.dtype)
            if space.shape == ():
                expected_shape = ()
            else:
                expected_shape = space.shape
            if value_array.shape != expected_shape:
                raise AssertionError(
                    f"Observation from {method} at {new_path} has invalid shape: "
                    f"got {value_array.shape}, expected {expected_shape} for {space}"
                )
            if value_array.dtype != space.dtype:
                raise AssertionError(
                    f"Observation from {method} at {new_path} has invalid dtype: "
                    f"got {value_array.dtype}, expected {space.dtype} for {space}"
                )
            # Check bounds (skip if infinite)
            if not (np.all(np.isinf(space.low)) and np.all(np.isinf(space.high))):
                if not np.all((value_array >= space.low) & (value_array <= space.high)):
                    raise AssertionError(
                        f"Observation from {method} at {new_path} out of bounds: "
                        f"got {value_array}, expected values in "
                        f"[{space.low}, {space.high}] for {space}"
                    )

        # Handle Discrete space
        elif isinstance(space, spaces.Discrete):
            if not isinstance(value, (int, np.integer)):
                raise AssertionError(
                    f"Observation from {method} at {new_path} has invalid type: "
                    f"got {type(value)}, expected int for {space}"
                )
            if value < 0 or value >= space.n:
                raise AssertionError(
                    f"Observation from {method} at {new_path} out of range: "
                    f"got {value}, expected [0, {space.n-1}] for {space}"
                )

        else:
            raise AssertionError(
                f"Unsupported space type at {new_path}: {space}"
            )

def validate_dict(observation: Dict[str, Any], space: spaces.Dict, method: str, path: str) -> None:
    """
    Validate a dictionary observation against a Dict space.
    
    Args:
        observation: The dictionary to validate.
        space: The Dict space to validate against.
        method: The method that generated the observation.
        path: The current path in the observation tree.
    """
    if not isinstance(observation, dict):
        raise AssertionError(
            f"Observation from {method} at {path} has invalid type: "
            f"got {type(observation)}, expected dict for {space}"
        )
    for key in observation:
        if key not in space.spaces:
            raise AssertionError(
                f"Observation from {method} at {path} contains unexpected key: {key}"
            )
    for key, subspace in space.spaces.items():
        new_path = f"{path}.{key}" if path else key
        if key not in observation:
            raise AssertionError(
                f"Observation from {method} at {new_path} is missing required key: {key}"
            )
        value = observation[key]
        
        # Handle nested spaces
        if isinstance(subspace, spaces.Text):
            if not isinstance(value, str):
                raise AssertionError(
                    f"Observation from {method} at {new_path} has invalid type: "
                    f"got {type(value)}, expected str for {subspace}"
                )
            if len(value) > subspace.max_length:
                raise AssertionError(
                    f"Observation from {method} at {new_path} exceeds max length: "
                    f"got length {len(value)}, expected <= {subspace.max_length} for {subspace}"
                )
        elif isinstance(subspace, spaces.Box):
            if not isinstance(value, (np.ndarray, float, int)):
                raise AssertionError(
                    f"Observation from {method} at {new_path} has invalid type: "
                    f"got {type(value)}, expected array-like or scalar for {subspace}"
                )
            value_array = np.asarray(value, dtype=subspace.dtype)
            if subspace.shape == ():
                expected_shape = ()
            else:
                expected_shape = subspace.shape
            if value_array.shape != expected_shape:
                raise AssertionError(
                    f"Observation from {method} at {new_path} has invalid shape: "
                    f"got {value_array.shape}, expected {expected_shape} for {subspace}"
                )
            if value_array.dtype != subspace.dtype:
                raise AssertionError(
                    f"Observation from {method} at {new_path} has invalid dtype: "
                    f"got {value_array.dtype}, expected {subspace.dtype} for {subspace}"
                )
            if not (np.all(np.isinf(subspace.low)) and np.all(np.isinf(subspace.high))):
                if not np.all((value_array >= subspace.low) & (value_array <= subspace.high)):
                    raise AssertionError(
                        f"Observation from {method} at {new_path} out of bounds: "
                        f"got {value_array}, expected values in "
                        f"[{subspace.low}, {subspace.high}] for {subspace}"
                    )
        elif isinstance(subspace, spaces.Discrete):
            if not isinstance(value, (int, np.integer)):
                raise AssertionError(
                    f"Observation from {method} at {new_path} has invalid type: "
                    f"got {type(value)}, expected int for {subspace}"
                )
            if value < 0 or value >= subspace.n:
                raise AssertionError(
                    f"Observation from {method} at {new_path} out of range: "
                    f"got {value}, expected [0, {subspace.n-1}] for {subspace}"
                )
        elif isinstance(subspace, spaces.Dict):
            validate_dict(value, subspace, method, new_path)
        elif isinstance(subspace, spaces.Sequence):
            if not isinstance(value, (list, tuple)):
                raise AssertionError(
                    f"Observation from {method} at {new_path} has invalid type: "
                    f"got {type(value)}, expected list or tuple for {subspace}"
                )
            for i, item in enumerate(value):
                item_path = f"{new_path}[{i}]"
                if isinstance(subspace.feature_space, spaces.Text):
                    if not isinstance(item, str):
                        raise AssertionError(
                            f"Observation from {method} at {item_path} has invalid type: "
                            f"got {type(item)}, expected str for {subspace.feature_space}"
                        )
                    if len(item) > subspace.feature_space.max_length:
                        raise AssertionError(
                            f"Observation from {method} at {item_path} exceeds max length: "
                            f"got length {len(item)}, expected <= {subspace.feature_space.max_length} for {subspace.feature_space}"
                        )
                elif isinstance(subspace.feature_space, spaces.Dict):
                    if not isinstance(item, dict):
                        raise AssertionError(
                            f"Observation from {method} at {item_path} has invalid type: "
                            f"got {type(item)}, expected dict for {subspace.feature_space}"
                        )
                    validate_dict(item, subspace.feature_space, method, item_path)
                elif isinstance(subspace.feature_space, spaces.Box):
                    if not isinstance(item, (np.ndarray, float, int)):
                        raise AssertionError(
                            f"Observation from {method} at {item_path} has invalid type: "
                            f"got {type(item)}, expected array-like or scalar for {subspace.feature_space}"
                        )
                    # Convert scalar to array for scalar Box spaces
                    value_array = np.asarray(item, dtype=subspace.feature_space.dtype)
                    if subspace.feature_space.shape == ():
                        expected_shape = ()
                    else:
                        expected_shape = subspace.feature_space.shape
                    if value_array.shape != expected_shape:
                        raise AssertionError(
                            f"Observation from {method} at {item_path} has invalid shape: "
                            f"got {value_array.shape}, expected {expected_shape} for {subspace.feature_space}"
                        )
                    if value_array.dtype != subspace.feature_space.dtype:
                        raise AssertionError(
                            f"Observation from {method} at {item_path} has invalid dtype: "
                            f"got {value_array.dtype}, expected {subspace.feature_space.dtype} for {subspace.feature_space}"
                        )
                    # Check bounds (skip if infinite)
                    if not (np.all(np.isinf(subspace.feature_space.low)) and np.all(np.isinf(subspace.feature_space.high))):
                        if not np.all((value_array >= subspace.feature_space.low) & (value_array <= subspace.feature_space.high)):
                            raise AssertionError(
                                f"Observation from {method} at {item_path} out of bounds: "
                                f"got {value_array}, expected values in "
                                f"[{subspace.feature_space.low}, {subspace.feature_space.high}] for {subspace.feature_space}"
                            )
                else:
                    raise AssertionError(
                        f"Unsupported sequence subspace at {item_path}: {subspace.feature_space}"
                    )
        else:
            raise AssertionError(
                f"Unsupported subspace type at {new_path}: {subspace}"
            ) 