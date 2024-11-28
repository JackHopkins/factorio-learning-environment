import os
from skills.bottoms_up_sampler import eval_program_with_result_trace, get_mining_setup
import json
import numpy as np

def instantiate_the_map(input_scenario, instance, starting_scenarios_folder):
        instance.reset()
        instance.initial_inventory = input_scenario["starting_inventory"]
        instance.reset()
        # here need to run the starting scenario as well
        starting_scenario_code = input_scenario["starting_scenario_code"]
        output_list, result, error = eval_program_with_result_trace(instance, starting_scenario_code)
        if error:
            return {"success": False, "error": result}

        initial_mining_setup = get_mining_setup(instance)
        return {"success": True, "mining_setup": initial_mining_setup}



def initialise_starting_scenario(starting_scenario_path, random_chance_int = 4):
    starting_scenario = {}
    
    starting_scenario["starting_inventory"] = get_starting_inventory_from_scenario_folder(starting_scenario_path, random_chance_int)
    starting_scenario["starting_scenario_code"] = get_starting_code_from_scenario_folder(starting_scenario_path)
    return starting_scenario


def get_starting_code_from_scenario_folder(starting_scenario_path):
    with open(f"{starting_scenario_path}/starting_snippet.py", "r") as f:
        starting_snippet = f.read()
    return starting_snippet

def get_starting_inventory_from_scenario_folder(starting_scenario_path, random_chance_int = 4):
    # read in the details.json from the starting_scenario_folder
    with open(f"{starting_scenario_path}/details.json", "r") as f:
        starting_details = json.load(f)

    starting_inventory = starting_details["fixed_inventory"]
    random_inventory = starting_details["random_inventory"]
    for key, value in random_inventory.items():
        # get a 0 or a 1 to add this item to the inventory
        if np.random.randint(0, random_chance_int) != 0:
            starting_inventory[key] = np.random.randint(value[0], value[1]+1)
    
    # legacy
    if "additional_inventory_for_starting_scenario" in starting_details:
        additional_inv = starting_details["additional_inventory_for_starting_scenario"]
        for key, value in additional_inv.items():
            if key in starting_inventory:
                starting_inventory[key] += value
            else:
                starting_inventory[key] = value
    
    # remove all items that have a value of 0
    starting_inventory = {k: v for k, v in starting_inventory.items() if v != 0}
    return starting_inventory