import random

from inspect_ai.solver import Solver, solver, TaskState, Generate

from fle.env import Resource


@solver
def nearest_questions(multiple_choice: bool = True) -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        instance = state.metadata["instance"]
        state.metadata["renderer"]

        state.metadata["nearest_questions"] = []

        bag = [
            Resource.IronOre,
            Resource.Water,
            Resource.Stone,
            Resource.CrudeOil,
            Resource.CopperOre,
            Resource.Coal,
            Resource.Wood,
        ]

        nearests = []
        for b in bag:
            choice = b
            try:
                nearest = instance.namespace.nearest(choice)
                nearests.append((choice, nearest))
            except Exception:
                continue

        for choice, nearest in nearests:
            choice_name, choice_entity = choice
            if not multiple_choice:
                question = f"What is the position of the nearest {choice_name} to you?"
                answer = f"Position({str(nearest)})"

                qa_entry = {
                    "question": question,
                    "answer": answer,
                    "entity_properties": choice_name,
                    "nearest": nearest,
                    "question_type": "open_ended",
                }
                state.metadata["nearest_questions"].append(qa_entry)
            else:
                other_options = random.sample([p for _, p in nearests], 3)
                alphabet = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k"]
                other_options.append(nearest)
                random.shuffle(other_options)
                option_string = "\n".join(
                    [
                        f"{alphabet[i]}) Position({option})"
                        for i, option in enumerate(other_options)
                    ]
                )

                question = (
                    f"What is the position of the nearest {choice_name} to you?\n"
                    f"Provide the correct letter and nothing else.\n"
                    f"{option_string}"
                )

                answer = str(alphabet[other_options.index(nearest)])

                qa_entry = {
                    "question": question,
                    "answer": answer,
                    "entity_properties": choice_name,
                    "nearest": nearest,
                    "options": other_options,
                    "question_type": "multiple_choice",
                }
                state.metadata["nearest_questions"].append(qa_entry)
            pass

        return state

    return solve
