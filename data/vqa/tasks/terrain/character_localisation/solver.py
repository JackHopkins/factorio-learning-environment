import random

from inspect_ai.solver import Solver, solver, TaskState, Generate


@solver
def character_localisation_question(multiple_choice: bool = False) -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState:

        renderer = state.metadata['renderer']

        if not renderer:
            return state

        characters = list(filter(lambda x:x.name == 'character', renderer.entities))

        if len(characters) == 1:
            if multiple_choice:
                if len(renderer.entities) >= 3:
                    options = [ entity.position for i, entity in enumerate(random.sample(renderer.entities, k=3))]
                else:
                    options = [ entity.position for entity in renderer.entities ]

                if characters[0].position not in options:
                    options.append( characters[0].position )

                random.shuffle(options)
                correct_index = str(options.index(characters[0].position) + 1)
                option_string = "\n".join([f"{i+1}) Position({str(option)})" for i, option in enumerate(options)])
                question = f"What is the position of your character?\n{option_string}\nOnly provide the correct number."
                qa_entry = {
                    "question": question,
                    "answer": str(correct_index),
                    "position": characters[0].position,
                    "entity_properties": characters[0],
                    "question_type": "multiple_choice"
                }

            else:
                qa_entry = {
                    "question": "What is the position of your character?",
                    "answer": f"Position(x={characters[0].position.x}, y={characters[0].position.y})",
                    "position": characters[0].position,
                    "entity_properties": characters[0],
                    "question_type": "open_ended"
                }

            state.metadata["character_localisation_question"] = [
                qa_entry
            ]
        return state

    return solve