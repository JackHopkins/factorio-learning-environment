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

    result = arr[tuple(all_idcs)]
    arr = np.swapaxes(result,-1,axis)
    return arr



def eval_program_with_achievements(instance, program):
        pre_production_flows = instance.get_production_stats()
        # evaluate the step
        try:
            score, goal, result = instance.eval_with_error(program, timeout=300)
            error = False
        except Exception as e:
            result = e
            # get the error message
            result = str(e)
            error = True
        # split result by newlines
        output_list = result.splitlines()
        post_production_flows = instance.get_production_stats()
        achievements = get_achievements(pre_production_flows, post_production_flows)
        return output_list, result, error, achievements

def get_achievements(pre_production_flows, post_production_flows):
        """
        Calculate the dynamic production flows between two states
        """
        achievements = {"static": {}, "dynamic": {}}
        if not isinstance(pre_production_flows, dict) or not isinstance(post_production_flows, dict):
            return achievements
        if "output" not in pre_production_flows or "output" not in post_production_flows:
            return achievements
        
        # merge the crafted and harvested dicts to one dict
        post_production_flows["static_items"] = get_updated_static_items(pre_production_flows, post_production_flows)
        
        achievements = process_achievements(pre_production_flows, post_production_flows, achievements)
        return achievements

def get_updated_static_items(pre_production_flows, post_production_flows, static_keys = ["crafted", "harvested"]):
    static_items = {}
    for static_flow_key in static_keys:
        for item, value in post_production_flows[static_flow_key].items():
            pre_crafted_item_value = pre_production_flows[static_flow_key][item] if item in pre_production_flows[static_flow_key] else 0
            created_item_value = value - pre_crafted_item_value
            if created_item_value > 0:
                static_items[item] = created_item_value
    return static_items

def process_achievements(pre_sleep_production_flows, post_sleep_production_flows, achievements):
    for item_key in post_sleep_production_flows["output"]:
        post_output_value = post_sleep_production_flows["output"][item_key]
        pre_output_value = pre_sleep_production_flows["output"][item_key] if item_key in pre_sleep_production_flows["output"] else 0
        # check if new items have been created
        if post_output_value > pre_output_value:
            created_value = post_output_value - pre_output_value
            # We need to look if its dynamic or static added value
            # if static greater than 0, we add it to static
            # we add the rest to dynamic
            static_value = post_sleep_production_flows["static_items"][item_key] if item_key in post_sleep_production_flows["static_items"] else 0
            if static_value > 0:
                achievements["static"][item_key] = static_value
            if created_value > static_value:
                achievements["dynamic"][item_key] = created_value - static_value
    return achievements