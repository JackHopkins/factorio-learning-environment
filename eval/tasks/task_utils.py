from eval.tasks.throughput_task import ThroughputTask
from eval.tasks.open_play_task import OpenPlayTask

def initiate_task_configs(input_task):
    if input_task["task_type"] == "populated_lab_play":
        return ThroughputTask(**input_task["config"])
    
    elif input_task["task_type"] == "open_ended_play":
        return OpenPlayTask(**input_task["config"])
    else:
        raise ValueError("Task type not supported")

def initialise_starting_state(instance, task):
    # reset the game state but with the new inventory
    task.setup(instance)
    return task

