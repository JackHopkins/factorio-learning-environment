import os
import json
from typing import Any, Tuple, Optional

from fle.agents.llm.api_factory import APIFactory
from fle.commons.models.game_state import GameState
from fle.env import FactorioInstance


class PlanSampler:
    def __init__(
        self, model: str, system_prompt_path: str, starting_scenarios_folder: str
    ):
        self.model = model
        self.system_prompt_path = system_prompt_path
        self.llm_factory = APIFactory(model)
        self.starting_scenarios_folder = starting_scenarios_folder
        self.planning_addition_for_prompt = """
First bring out a thorough step-by-step plan how you can achieve this task and then create the python script to achieve the task.
For your plan, follow this structure:
1) What entities are needed for the task
2) What entities do we have on the map, in different entity inventories or in our inventory
3) What entities are we missing for the task
4) Execution -- Taking into account 1,2 and 3, what steps do we need to take to successfully carry out the task

Create the python script based on your plan.
"""

    def get_game_state(
        self, instance: FactorioInstance, scenario: str
    ) -> Optional[GameState]:
        """Load a scenario and return the corresponding game state"""
        try:
            # Reset instance to clean state
            instance.reset()

            # Look for scenario configuration files
            scenario_path = os.path.join(self.starting_scenarios_folder, scenario)
            if not os.path.exists(scenario_path):
                return None

            # Try to load scenario configuration
            config_file = os.path.join(scenario_path, "config.json")
            if os.path.exists(config_file):
                with open(config_file, "r") as f:
                    config = json.load(f)

                # Set inventory if specified
                if "inventory" in config:
                    instance.set_inventory(config["inventory"])

                # Run setup script if specified
                if "setup_script" in config:
                    setup_script_path = os.path.join(
                        scenario_path, config["setup_script"]
                    )
                    if os.path.exists(setup_script_path):
                        with open(setup_script_path, "r") as f:
                            setup_code = f.read()
                        instance.eval(setup_code, timeout=30)

            # Capture the game state after setup
            return GameState.from_instance(instance)

        except Exception as e:
            print(f"Error loading scenario {scenario}: {str(e)}")
            return None

    async def __call__(
        self, instance: FactorioInstance, game_state: GameState
    ) -> Tuple[str, Any]:
        """Generate an objective/plan for the given game state"""
        try:
            # Load system prompt
            with open(self.system_prompt_path, "r") as f:
                system_prompt = f.read()

            # Create messages for the LLM call
            inventory_info = f"Current inventory: {game_state.inventories[0]}"

            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"{inventory_info}\n\n{self.planning_addition_for_prompt}",
                },
            ]

            # Generate plan using LLM
            response = await self.llm_factory.acall(
                messages=messages, temperature=0.7, max_tokens=1024
            )

            # Extract content based on response type
            if hasattr(response, "choices"):
                objective = response.choices[0].message.content
            elif hasattr(response, "content"):
                objective = (
                    response.content[0].text
                    if hasattr(response.content[0], "text")
                    else response.content
                )
            else:
                objective = str(response)

            return objective.strip(), response

        except Exception as e:
            print(f"Error generating plan: {str(e)}")
            return "", None
