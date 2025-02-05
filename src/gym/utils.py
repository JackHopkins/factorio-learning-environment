import time
from functools import wraps
from typing import Tuple

import numpy
import numpy as np
from PIL import Image as Img
from skimage.util.shape import view_as_windows as viewW

def print_timing(func):
    '''
    create a timing decorator function
    use
    @print_timing
    just above the function you want to time
    '''
    @wraps(func)  # improves debugging
    def wrapper(*arg):
        start = time.perf_counter()  # needs python3.3 or higher
        result = func(*arg)
        end = time.perf_counter()
        fs = '{} took {:.3f} microseconds'
        print(fs.format(func.__name__, (end - start)*1000000))
        return result
    return wrapper

def render_images(factorio):

    for key, val in factorio.minimaps.items():
        data = np.uint8(np.clip(val, 0, 255))
        img = Img.fromarray(data, 'L')
        # img = Image.fromarray(factorio.minimaps['all'], 'RGB')
        img.save(f'logs/{key}.png')
        #img.show()

def stitch(rolled_grid: np.array, added_row: np.array, movement_vector: Tuple[int, int]):
    if movement_vector[0] == 0:
        if movement_vector[1] > 0:
            concatenated = numpy.concatenate([rolled_grid, added_row], axis=0)
            snipped = np.delete(concatenated, 0, 0)
        elif movement_vector[1] < 0:
            concatenated = numpy.concatenate([added_row, rolled_grid], axis=0)
            snipped = np.delete(concatenated, -1, 0)
    elif movement_vector[1] == 0:
        if movement_vector[0] > 0:
            concatenated = numpy.concatenate([rolled_grid, added_row.T], axis=1)
            snipped = np.delete(concatenated, 0, 1)
        elif movement_vector[0] < 0:
            concatenated = numpy.concatenate([added_row.T, rolled_grid], axis=1)
            snipped = np.delete(concatenated, -1, 1)
    else:
        raise Exception("Cannot stitch multiple axes simulateously")

    return snipped

def roll(grid: np.array, movement_vector: Tuple[int, int]):
    # If no X axis movement is happening
    if movement_vector[0] == 0:
        # Roll opposite direction
        return np.roll(grid, movement_vector[1], 0)
        # If no Y axis movement is happening
    elif movement_vector[1] == 0:
        # If both axes are moving
        return np.roll(grid, movement_vector[0], 1)
    else:
        roll_X = np.roll(grid, movement_vector[0], 1)
        return np.roll(roll_X, movement_vector[1], 0)

def strided_indexing_roll(a, r):
    # Concatenate with sliced to cover all rolls
    a_ext = np.concatenate((a, a[:, :-1]), axis=1)

    # Get sliding windows; use advanced-indexing to select appropriate ones
    n = a.shape[1]
    return viewW(a_ext, (1, n))[np.arange(len(r)), (n - r) % n, 0]


def indep_roll(arr, shifts, axis=1):
    """Apply an independent roll for each dimensions of a single axis.

    Parameters
    ----------
    arr : np.ndarray
        Array of any shape.

    shifts : np.ndarray
        How many shifting to use for each dimension. Shape: `(arr.shape[axis],)`.

    axis : int
        Axis along which elements are shifted.
    """
    arr = np.swapaxes(arr,axis,-1)
    all_idcs = np.ogrid[[slice(0,n) for n in arr.shape]]

    # Convert to a positive shift
    shifts[shifts < 0] += arr.shape[-1]
    all_idcs[-1] = all_idcs[-1] - shifts[:, np.newaxis]