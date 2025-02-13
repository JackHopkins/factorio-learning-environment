from eval.tasks.throughput_task import ThroughputTask, LAB_PLAY_POPULATED_STARTING_INVENTORY

def initiate_task_configs(input_task):
    if input_task["task_type"] == "populated_lab_play":
        input_task["config"]["starting_inventory"] = LAB_PLAY_POPULATED_STARTING_INVENTORY
        return ThroughputTask(**input_task["config"])
    task_config = ThroughputTask(**input_task["config"])
    return task_config

def initialise_starting_state(instance, task):
    # reset the game state but with the new inventory
    task.setup(instance)
    return task

