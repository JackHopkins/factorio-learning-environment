from typing import Any

from llm_factory import LLMFactory
from search.auto_curriculum.dataset_utils import instantiate_the_map, initialise_starting_scenario
from search.mcts.model.game_state import GameState


class PlanSampler():
    def __init__(self, model, system_prompt_path, starting_scenarios_folder):
        
        self.model = model
        self.system_prompt_path = system_prompt_path
        self.llm_factory = LLMFactory(model)
        self.starting_scenarios_folder = starting_scenarios_folder
        self.planning_addition_for_prompt = """
First bring out a thorough step-by-step plan how you can achieve this task and then create the python script to achieve the task.
For your plan, follow this structure:
1) What entities are needed for the task
2) What entities do we have on the map, in different entity inventories or in our inventory
3) What entities are we missing for the task
4) Execution -- Taking into account 1,2 and 3, what steps do we need to take to successfully carry out the task

The format should look like this:

'''
Objective: XXX

Planning:
1) Entities needed for the task:
...

2) Entities we have:
From the initial inventory:
...

Entities on the map:
...

3) Entities we are missing:
...

4) Execution steps:
- ...
- ...
etc...
'''

"""
        
    
    def get_unsupervised_objective(self, instance):
        """
        Runs the traces, adds the plan to the prompt and saves the traces to the save path
        """
        starting_inventory = instance.inspect_inventory()
        self.init_system_prompt(instance)
        mining_setup = self.get_mining_setup(instance)
        messages = [{"role": "system", "content": self.system_prompt}]
        user_message = f"Your starting inventory is {starting_inventory}. Your initial mining setup is: {mining_setup}. Create a useful task that you can carry out in the current game and the python script to achieve the task"
        user_message += f"\n{self.planning_addition_for_prompt}"
        messages.append({"role": "user", "content": user_message})
        response = self.llm_factory.call(messages=messages,
                                         model = self.model,
                                        temperature=0.7,
                                        max_tokens=512,
                                        stop_sequences = ["```"])
        
        try:
            full_output = response.choices[0].message.content
        except:
            full_output = response.content[0].text.strip()
        full_output = full_output.strip()
        new_line_idx = full_output.rfind("\n")
        full_output = full_output[:new_line_idx].replace("Sure!", "").strip()
        #full_output = f'"""\n{full_output}\n"""'
        return full_output, response
    
    def get_mining_setup(self, instance):
        mining_setup = instance.get_entities()
        if len(mining_setup) == 0:
            mining_setup = "There are no entities on the map"
        else:
            mining_setup = f"The following entities are on the map and can be used: {mining_setup}"
        return mining_setup
    
    def init_system_prompt(self, instance):
        api_description = instance.get_system_prompt()
        system_prompt_path = self.system_prompt_path
        # read in the system prompt
        with open(system_prompt_path, "r") as f:
            system_prompt = f.read()
        self.system_prompt = system_prompt.format(schema=api_description)


    def __call__(self, instance, game_state_str) -> Any:
        instance.reset(game_state_str)
        objective, response = self.get_unsupervised_objective(instance)
        try:
            return objective.split("'''")[1].strip(), response
        except:
            try:
                return objective.split('"""')[2].strip(), response
            except:
                return objective.strip(), response

    def get_game_state(self, instance, starting_scenario_path):
        # gets starting scenario details
        #starting_scenario_path = os.path.join(self.starting_scenarios_folder, starting_scenario_name)
        starting_scenario = initialise_starting_scenario(starting_scenario_path)  # Gets the starting scenario details
        # instantiate the map
        result = instantiate_the_map(starting_scenario, instance, self.starting_scenarios_folder)
        if not result["success"]:
            print(f"Error in starting scenario: {result['error']}")
            return False
        # get the game state
        game_state = GameState.from_instance(instance)
        return game_state



# if __name__ == "__main__":
#         prompt_path = "../../prompts/bottoms_up_prompts/finetuning_prompts/system_message_policy_self_gen.md"
#         model_path = "ft:gpt-4o-2024-08-06:paperplane-ai:fact-self-gen-planning:AQzcPI91"
#         starting_scenario_folder = "../../skills/data_scenarios/starting_scenarios"
#         sampler = PlanSampler(model_path, prompt_path, starting_scenario_folder)
#         starting_scenario = "ft_random_chest_furnace_placement_with_mining_entities"
#         instance = FactorioInstance(address='localhost',
#                                     bounding_box=200,
#                                     tcp_port=27015,
#                                     fast=True,
#                                     #cache_scripts=False,
#                                     inventory={})
#
#         game_state = sampler.get_game_state(instance, starting_scenario)
#         objective = sampler(instance, game_state)
#
#         program = Program(code=objective,
#                           conversation=Conversation(messages=[]),
#                           value=10,
#                           raw_reward=10,
#                           response="")
#         pass