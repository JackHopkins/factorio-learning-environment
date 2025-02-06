import json
import logging
import os

from entities import Position
from trace import Trace
from typing import List
from venv import logger

from eval.open.auto_curriculum.curricula import CurriculumStrategy, RecipeBasedCurriculum
from eval.open.auto_curriculum.model_evaluator import ModelEvaluator
from instance import FactorioInstance
from skills.bottoms_up_sampler import eval_program_with_result_trace, get_mining_setup
from prompts import TASK_GENERATION_PROMPT, USER_TASK_PROMPT, RECENT_TASK_HISTORY_PROMPT


class AutoCurriculumEvaluatorSingle(ModelEvaluator):
    def __init__(self, *args,
                 curriculum_strategy: CurriculumStrategy = None,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.task_history: List[Trace] = []
        self.task_history_window = 5
        self._load_curriculum_traces()
        self.curriculum_strategy = curriculum_strategy

    def _execute_task(self, instance, task_description, target_pl, include_plan) -> Trace:
        starting_inventory = instance.inspect_inventory()
        mining_setup = get_mining_setup(instance)

        messages = self._prepare_messages(
            task_description,
            target_pl,
            include_plan,
            starting_inventory,
            mining_setup
        )

        program, full_output = self._get_program(messages)

        # Reset position
        instance.move_to(Position(x=0, y=0))

        output_list, result = eval_program_with_result_trace(instance, program)
        achieved_pl = instance._production_stats()

        if "error" in result.lower():
            print(f"Error in program: {result}")

        return Trace(
            program=program,
            output=output_list,
            result=result,
            starting_inventory=self._convert_inventory(starting_inventory),
            mining_setup=mining_setup,
            messages=messages,
            planning=include_plan,
            full_output=full_output,
            success="error" not in result.lower(),
            target_pl=target_pl,
            task_description=task_description,
            achieved_pl=achieved_pl
        )

    def _prepare_messages(self, task_description, target_pl, include_plan, starting_inventory, mining_setup):
        messages = [{"role": "system", "content": self.system_prompt}]

        user_message = USER_TASK_PROMPT.format(
            inventory=starting_inventory,
            mining_setup=mining_setup,
            task_description=task_description,
            target_quantities=self._format_pl_for_prompt(target_pl)
        )

        if include_plan:
            user_message += f"\n{self.planning_addition_for_prompt}"

        messages.append({"role": "user", "content": user_message})
        return messages

    def _get_program(self, messages):
        # Get and execute the program
        response = self.llm_factory.call(messages=messages,
                                         temperature=0.7,
                                         max_tokens=4096)

        full_output = response.choices[0].message.content
        program = self.parse_program(full_output)
        return program, full_output

    def run_curriculum_episode(self, instance: FactorioInstance, num_tasks: int = 5, include_plan: bool = True):
        """Runs an episode with automatically increasing difficulty based on production stats"""
        self.init_system_prompt(instance)
        for task_num in range(num_tasks):
            instance.reset()

            # Get current task based on history
            task_description, target_pl = self.curriculum_strategy.generate_next_task(
                self.task_history, instance
            )

            # Reset production stats before task
            instance._production_stats()

            # Generate and execute program
            trace: Trace = self._execute_task(
                instance,
                task_description,
                target_pl,
                include_plan
            )
            trace.task_number = task_num

            # Update curriculum strategy
            self.curriculum_strategy.update_task_history(trace)

            # Save trace
            self.task_history.append(trace)

            self._save_curriculum_trace(trace)

    def _convert_inventory(self, inventory):
        """Convert inventory to consistent dictionary format"""
        inventory_dict = {}
        for item in inventory:
            if isinstance(item, tuple):
                inventory_dict[item[0]] = inventory[item]
            else:
                inventory_dict[item] = inventory[item]
        return inventory_dict

    def _format_dict(self, d: dict) -> str:
        """Format dictionary for prompt"""
        return "\n".join(f"- {k}: {v}" for k, v in d.items())

    def _generate_task_description(self, target_pl: dict) -> str:
        """
        Generate a task description using LLM based on target P/L and history
        """
        # Get recent successful tasks for context
        recent_tasks = [t for t in self.task_history if t.success][-self.task_history_window:]

        # Format history for prompt
        history_str = ""
        for task in recent_tasks:
            history_str += RECENT_TASK_HISTORY_PROMPT.format(input=self._format_dict(task.achieved_pl['input']),
                                                             output=self._format_dict(task.achieved_pl['output']),
                                                             previous_task=task.get('task_description', 'Unknown'))
        recent_task_history_string = f'Recent task history:\n{history_str}' if history_str else 'No previous task history.'
        prompt = TASK_GENERATION_PROMPT.format(
            input_resources=self._format_dict(target_pl["input"]),
            output_resources=self._format_dict(target_pl["output"]),
            recent_task_history=recent_task_history_string
        )

        messages = [
            {"role": "system", "content": "You are an expert Factorio automation curriculum designer."},
            {"role": "user", "content": prompt}
        ]

        response = self.llm_factory.call(
            messages=messages,
            temperature=0.7,
            max_tokens=100  # Keep it concise
        )

        task_description = response.choices[0].message.content.strip()

        # Store the task description for future context
        #self.task_history[-1]["task_description"] = task_description

        return task_description

    def _format_pl_for_prompt(self, pl: dict) -> str:
        """Format P/L stats for LLM prompt"""
        result = "Resources to gather/consume:\n"
        for item, count in pl["input"].items():
            result += f"- {item}: {count}\n"

        result += "\nItems to produce:\n"
        for item, count in pl["output"].items():
            result += f"- {item}: {count}\n"

        return result

    def get_curriculum_save_path(self):
        curriculum_save_path = os.path.join(self.save_path, "curriculum_traces")
        os.makedirs(curriculum_save_path, exist_ok=True)
        return curriculum_save_path

    def _save_curriculum_trace(self, trace: Trace):
        """Save curriculum trace to disk"""
        curriculum_save_path = self.get_curriculum_save_path()

        subdir = "success" if trace.success else "failure"

        task_dir = self.curriculum_strategy.get_task_dir(trace)

        # Create trace directory
        if task_dir:
            trace_dir = os.path.join(curriculum_save_path, task_dir, subdir)
        else:
            trace_dir = os.path.join(curriculum_save_path, subdir)
        try:
            os.makedirs(trace_dir)
        except FileExistsError:
            pass

        # Get next trace number
        existing_traces = 1
        for f in os.listdir(trace_dir):
            existing_traces += 1

        # Save trace data
        with open(os.path.join(curriculum_save_path, "trace.jsonl"), "a") as f:
            f.write(json.dumps(trace.__dict__) + "\n")

        # Save program separately
        with open(os.path.join(trace_dir, f"program_{existing_traces}.py"), "w") as f:
            f.write(trace.program)

        # Create a metadata file in the trace directory if it doesn't exist.
        metadata_file = os.path.join(curriculum_save_path, task_dir, "metadata.json")
        if not os.path.exists(metadata_file):
            with open(metadata_file, "w") as f:
                f.write(json.dumps({
                    "task_description": trace.task_description,
                    "success": 1 if trace.success else 0,
                    "attempts": 1
                }))
        else:
            with open(metadata_file, "r") as f:
                metadata = json.load(f)
            metadata["success"] += 1 if trace.success else 0
            metadata["attempts"] += 1
            metadata["success"] /= metadata["attempts"]
            with open(metadata_file, "w") as f:
                f.write(json.dumps(metadata))

    def _load_curriculum_traces(self):
        """Load curriculum traces from disk"""
        curriculum_save_path = self.get_curriculum_save_path()

        if not os.path.exists(curriculum_save_path):
            return

        trace_file = os.path.join(curriculum_save_path, "trace.jsonl")

        if not os.path.exists(trace_file):
            logger.error(f"Trace file not found: {trace_file}, starting from scratch")
            return

        with open(trace_file, "r") as f:
            for line in f:
                try:
                    trace = json.loads(line)
                    self.task_history.append(Trace(**trace))
                except Exception as e:
                    logger.warning(f"Error loading trace: {e}")
                    pass

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    evaluator = AutoCurriculumEvaluatorSingle(
        model_path=r"ft:gpt-4o-2024-08-06:paperplane-ai:fact-self-gen-planning:AQzcPI91",
        system_prompt_path=r"../../../data/prompts/bottoms_up_prompts/finetuning_prompts/system_message_policy_self_gen.md",
        save_path=r"finetuned_model_gen",
        starting_scenarios_folder=r"../skills/data_scenarios/starting_scenarios",
        curriculum_strategy=RecipeBasedCurriculum("recipes.jsonl")
    )
    instance = FactorioInstance(address='localhost', bounding_box=200, tcp_port=27000, fast=True, cache_scripts=False)
    evaluator.run_curriculum_episode(instance, num_tasks=120)