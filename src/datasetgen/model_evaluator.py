
import os
import ast
import json
from typing import List, Dict, Any
from dotenv import load_dotenv
from factorio_instance import FactorioInstance
import random
from skills.bottoms_up_sampler import eval_program_with_result_trace, get_mining_setup
load_dotenv()
from llm_factory import LLMFactory
from dataset_utils import instantiate_the_map, initialise_starting_scenario
class ModelEvaluator:
    def __init__(self, model_path, system_prompt_path, save_path, starting_scenarios_folder):
        
        self.model_path = model_path
        self.system_prompt_path = system_prompt_path
        self.llm_factory = LLMFactory(model_path)
        self.save_path = save_path
        self.starting_scenarios_folder = starting_scenarios_folder
        self.planning_addition_for_prompt = """
First bring out a thorough step-by-step plan how you can achieve this task and then create the python script to achieve the task.
For your plan, follow this structure:
1) What entities are needed for the task
2) What entities do we have on the map, in different entity inventories or in our inventory
3) What entities are we missing for the task
4) Execution -- Taking into account 1,2 and 3, what steps do we need to take to successfully carry out the task
"""


    def run_unsupervised_episode(self, instance, length: int, include_plan: bool = False):
        """
        Runs the traces, adds the plan to the prompt and saves the traces to the save path
        """
        traces = []
        for i in range(length):
            messages = [{"role": "system", "content": self.system_prompt}]
            starting_inventory = instance.inspect_inventory()
            mining_setup = get_mining_setup(instance)
            user_message = f"Your starting inventory is {starting_inventory}. Your initial mining setup is: {mining_setup}. Create a useful task that you can carry out in the current game and the python script to achieve the task"
            if include_plan:
                user_message += f"\n{self.planning_addition_for_prompt}"
                user_message = user_message.strip()
            messages.append({"role": "user", "content": user_message})
            response = self.llm_factory.call(messages=messages,
                                            temperature=0.7,
                                            max_tokens=4096)
            full_output = response.choices[0].message.content
            if "```python" in full_output:
                program = full_output.split("```python")[1]
                program = program.split("```")[0]
            else:
                print(f"Missing python code in response: {full_output}")
                continue
            output_list, result = eval_program_with_result_trace(instance, program)
            inventory_dict = {}
            for item in starting_inventory:
                if isinstance(item, tuple):
                    inventory_dict[item[0]] = starting_inventory[item]
                else:
                    inventory_dict[item] = starting_inventory[item]
            traces.append({"program": program, "output": output_list, "result": result,
                            "starting_inventory": inventory_dict, "mining_setup": mining_setup,
                            "messages": messages, "planning": include_plan,
                            "full_output": full_output, 
                            "success": "error" not in result.lower()
                            })
            if "error" in result.lower():
                print(f"Error in program: {result}")
            else:
                print(f"Succcess")
        
        # save the traces to the save path
        unsupervised_save_path = os.path.join(self.save_path, "unsupervised_traces")
        # first get the number of folders in unsupervised_save_path
        num_folders = len([name for name in os.listdir(unsupervised_save_path) if os.path.isdir(os.path.join(unsupervised_save_path, name))])
        # create a new folder for the traces
        save_folder = os.path.join(unsupervised_save_path, f"trace_{num_folders}")
        os.makedirs(save_folder)
        with open(os.path.join(save_folder, "trace.jsonl"), "w") as f:
            for trace in traces:
                f.write(json.dumps(trace) + "\n")
        for idx, trace in enumerate(traces):
            # save the the program and output to a file
            with open(os.path.join(save_folder, f"program_{idx}_{trace['success']}.py"), "w") as f:
                f.write(trace["program"])

    def run_supervised_episode(self, tries: int, task, include_plan: bool = False):
        """
        Run the supervised task
        Need to implement saving the successful trace
        """
        instance = FactorioInstance(address='localhost',
                                bounding_box=200,
                                tcp_port=27015,
                                fast=True,
                                #cache_scripts=False,
                                inventory={})
        self.init_system_prompt(instance)
        for i in range(tries):
            messages = [{"role": "system", "content": self.system_prompt}]
            starting_inventory = instance.inspect_inventory()
            mining_setup = get_mining_setup(instance)
            user_message = f"Your starting inventory is {starting_inventory}. Your initial mining setup is: {mining_setup}. Create a python script that achieves the following task\n{task}"
            if include_plan:
                user_message += f"\n{self.planning_addition_for_prompt}"
                user_message = user_message.strip()
            messages.append({"role": "user", "content": user_message})
            response = self.llm_factory.call(messages=messages,
                                            temperature=0.7,
                                            max_tokens=2048)
            full_output = response.choices[0].message.content
            if "```python" in full_output:
                program = full_output.split("```python")[1]
                program = program.split("```")[0]
            else:
                print(f"Missing python code in response: {program}")
                continue
            output_list, result = eval_program_with_result_trace(instance, program)
            if "error" in result.lower():
                print(f"Error in program: {result}")
                continue
            break

    def init_system_prompt(self, instance):
        api_description = instance.get_system_prompt()
        system_prompt_path = self.system_prompt_path
        # read in the system prompt
        with open(system_prompt_path, "r") as f:
            system_prompt = f.read()
        self.system_prompt = system_prompt.format(schema=api_description)
        # change all " marks to '
        #self.system_prompt.replace('"', "'")

    def run_simulations_from_starting_scenarios(self, list_of_starting_scenario_folders: List[str], 
                                                num_episodes: int, episode_length: int, include_plan: bool = False):
        """
        Runs the simulations from the starting scenarios
        args:
        list_of_starting_scenario_folders: List[str] -- the list of starting scenario folders to run the simulations from
        num_episodes: int -- the number of episodes to run
        episode_length: int -- the length of each episode
        include_plan: bool -- whether to get the LLM to generate a plan before the task or only the policy
        """
        # start the factorio instance
        instance = FactorioInstance(address='localhost',
                                bounding_box=200,
                                tcp_port=27015,
                                fast=True,
                                #cache_scripts=False,
                                inventory={})
        self.init_system_prompt(instance) # Inits the system prompt
        for starting_scenario_folder in list_of_starting_scenario_folders:
            starting_scenario_path = os.path.join(self.starting_scenarios_folder, starting_scenario_folder)
            for i in range(num_episodes):
                starting_scenario = initialise_starting_scenario(starting_scenario_path) # Gets the starting scenario details
                # instantiate the map
                result = instantiate_the_map(starting_scenario, instance, self.starting_scenarios_folder)
                if not result["success"]:
                    print(f"Error in starting scenario: {result['error']}")
                    continue
                # runs the actual episode
                self.run_unsupervised_episode(instance, episode_length, include_plan)

def get_all_folders_in_path(path):
    return [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]


if __name__ == "__main__":
    model_path = r"ft:gpt-4o-2024-08-06:paperplane-ai:fact-self-gen-planning:AQzcPI91"
    evaluator = ModelEvaluator(model_path, 
                               r"prompts\bottoms_up_prompts\finetuning_prompts\system_message_policy_self_gen.md",
                               save_path = r"datasets\finetuned_model_gen", # Where to save the traces
                               starting_scenarios_folder=r"skills\data_scenarios\starting_scenarios" # Where the starting scenarios are stored
                               )
    supervised_trace = True
    if supervised_trace:
        starting_scenarios = ["ft_random_chest_furnace_placement_with_mining_entities"]
        #starting_scenarios = get_all_folders_in_path(r"skills\data_scenarios\starting_scenarios")
        #starting_scenarios = ["multiple_entiti_environment"]
        evaluator.run_simulations_from_starting_scenarios(starting_scenarios, 2, 2, include_plan=True)
    else:
       objective = "Get 1 offshore pump"
       evaluator.run_supervised_episode(5, objective, include_plan=True)
