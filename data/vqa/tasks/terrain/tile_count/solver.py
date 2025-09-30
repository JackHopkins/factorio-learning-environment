import copy
import random
import re

from inspect_ai.solver import Solver, solver, TaskState, Generate


@solver
def tile_count_questions(multiple_choice: bool = True) -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        renderer = state.metadata["renderer"]

        counts = {}
        for entity in renderer.entities:
            name = entity.name.replace("-", " ")
            name = re.sub("\d+", "", name)  # Remove variants

            if "water" in name or "cliff" in name:
                name += "-tile"
            if name.endswith("big"):
                name = name[:-3]
                name = "big " + name

            name = name.strip()
            if name not in counts:
                counts[name] = 0
            counts[name] += 1

        for entity in renderer.water_tiles:
            if entity["name"] not in counts:
                counts[entity["name"]] = 0
            counts[entity["name"]] += 1

        multiple_choice_bands = [0, 1, 2, 4, 8, 16, 32, 64, 128]

        state.metadata["tile_count_questions"] = []

        for key, value in counts.items():
            if multiple_choice:
                band = None
                for band in multiple_choice_bands:
                    if value > band:
                        continue
                    break

                removed_multiple_choice_bands = copy.deepcopy(multiple_choice_bands)
                removed_multiple_choice_bands.remove(band)
                alphabet = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k"]
                other_options = random.sample(removed_multiple_choice_bands, 3)
                other_options.append(band)
                random.shuffle(other_options)
                option_string = "\n".join(
                    [
                        f"{alphabet[i]}){option}"
                        for i, option in enumerate(other_options)
                    ]
                )
                question = f"How many {key}s do you see?\n{option_string}\nProvide the letter of the best match and nothing else."

                qa_entry = {
                    "question": question,
                    "answer": str(alphabet[other_options.index(band)]),
                    "entity_properties": key,
                    "count": value,
                    "options": other_options,
                    "question_type": "multiple_choice",
                }
                state.metadata["tile_count_questions"].append(qa_entry)
            else:
                qa_entry = {
                    "question": f"How many {key}s do you see?",
                    "answer": str(value),
                    "entity_properties": key,
                    "question_type": "open_ended",
                }
                state.metadata["tile_count_questions"].append(qa_entry)

        return state

    return solve
