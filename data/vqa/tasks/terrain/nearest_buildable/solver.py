import random
from typing import List, Dict, Any
from inspect_ai.solver import Solver, solver, TaskState, Generate
from fle.env import Position, BuildingBox
from fle.env.game_types import Prototype

# Common prototypes to test for building placement
BUILDABLE_PROTOTYPES = [
    # Basic structures
    Prototype.WoodenChest,
    Prototype.IronChest,
    Prototype.SteelChest,

    # Production buildings
    Prototype.AssemblingMachine1,
    Prototype.AssemblingMachine2,
    Prototype.StoneFurnace,
    Prototype.SteelFurnace,
    Prototype.ElectricFurnace,

    # Mining
    Prototype.BurnerMiningDrill,
    Prototype.ElectricMiningDrill,

    # Power
    Prototype.SteamEngine,
    Prototype.SolarPanel,
    Prototype.Accumulator,
    Prototype.Boiler,

    # Logistics
    Prototype.TransportBelt,
    Prototype.FastTransportBelt,
    Prototype.Inserter,
    Prototype.LongHandedInserter,
    Prototype.FastInserter,

    # Defense
    Prototype.GunTurret,
    Prototype.StoneWall,

    # Fluid handling
    Prototype.Pipe,
    Prototype.StorageTank,
    Prototype.OffshorePump,
    Prototype.Pump,

    # Advanced
    Prototype.Lab,
    Prototype.ChemicalPlant,
    Prototype.OilRefinery,
    Prototype.RocketSilo,
]


@solver
def nearest_buildable_questions(
        questions_per_position: int = 5,
        multiple_choice: bool = True,
        prototype_subset: List[Prototype] = None
) -> Solver:
    """
    Generate questions about nearest buildable positions for various prototypes.

    Args:
        questions_per_position: Number of questions to generate per terrain position
        multiple_choice: If True, generate multiple choice questions
        prototype_subset: Specific prototypes to test, if None uses default list
    """

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        instance = state.metadata.get('instance')
        renderer = state.metadata.get('renderer')

        if not instance:
            state.metadata["error"] = "No instance found"
            state.metadata["nearest_buildable_questions"] = []
            return state

        characters = list(filter(lambda x: x.name == 'character', renderer.entities))
        player_position = None
        if len(characters) == 1:
            player_position = characters[0].position
        else:
            return state

        # Use provided prototypes or default list
        prototypes_to_test = prototype_subset or BUILDABLE_PROTOTYPES

        # Sample prototypes for this position
        num_questions = min(questions_per_position, len(prototypes_to_test))
        selected_prototypes = random.sample(prototypes_to_test, num_questions)

        nearest_buildable_questions = []

        for prototype in selected_prototypes:
            try:
                # Get the prototype's dimensions
                width = prototype.WIDTH
                height = prototype.HEIGHT

                # Create building box
                building_box = BuildingBox(width=width, height=height)

                # Get current player position as center
                player_pos = player_position
                center_pos = Position(x=player_pos.x, y=player_pos.y)

                # Find nearest buildable position
                buildable_area = instance.namespace.nearest_buildable(
                    entity=prototype,
                    building_box=building_box,
                    center_position=center_pos
                )

                # Extract the center position of buildable area
                nearest_pos = buildable_area.center

                if not multiple_choice:
                    # Open-ended question
                    question = f"What is the position of the nearest place you can build a {prototype.value[0]}?"
                    answer = f"Position(x={nearest_pos.x}, y={nearest_pos.y})"

                    qa_entry = {
                        "question": question,
                        "answer": answer,
                        "prototype": prototype.value[0],
                        "building_box": {"width": width, "height": height},
                        "center_position": {"x": center_pos.x, "y": center_pos.y},
                        "buildable_area": {
                            "center": {"x": nearest_pos.x, "y": nearest_pos.y},
                            "left_top": {"x": buildable_area.left_top.x, "y": buildable_area.left_top.y},
                            "right_bottom": {"x": buildable_area.right_bottom.x, "y": buildable_area.right_bottom.y}
                        },
                        "question_type": "open_ended"
                    }
                else:
                    # Multiple choice question
                    # Generate distractor positions
                    distractors = []

                    # Add some offset positions as distractors
                    offsets = [
                        (-5, -5), (5, 5), (-10, 0), (0, 10),
                        (-7, 3), (3, -7), (8, -2), (-2, 8)
                    ]

                    for offset_x, offset_y in random.sample(offsets, 3):
                        distractor_pos = Position(
                            x=center_pos.x + offset_x,
                            y=center_pos.y + offset_y
                        )
                        distractors.append(distractor_pos)

                    # Create options list with correct answer
                    options = distractors + [nearest_pos]
                    random.shuffle(options)

                    # Create alphabet labels
                    alphabet = ['a', 'b', 'c', 'd']

                    # Format options string
                    option_strings = []
                    for i, pos in enumerate(options):
                        option_strings.append(f"{alphabet[i]}) Position(x={pos.x}, y={pos.y})")

                    options_text = "\n".join(option_strings)

                    # Find correct answer letter
                    correct_index = options.index(nearest_pos)
                    correct_letter = alphabet[correct_index]

                    question = (
                        f"What is the position of the nearest place you can build a {prototype.value[0]}?\n"
                        f"Provide the correct letter and nothing else.\n"
                        f"{options_text}"
                    )

                    qa_entry = {
                        "question": question,
                        "answer": correct_letter,
                        "prototype": prototype.value[0],
                        "building_box": {"width": width, "height": height},
                        "center_position": {"x": center_pos.x, "y": center_pos.y},
                        "buildable_area": {
                            "center": {"x": nearest_pos.x, "y": nearest_pos.y},
                            "left_top": {"x": buildable_area.left_top.x, "y": buildable_area.left_top.y},
                            "right_bottom": {"x": buildable_area.right_bottom.x, "y": buildable_area.right_bottom.y}
                        },
                        "options": [{"x": pos.x, "y": pos.y} for pos in options],
                        "correct_index": correct_index,
                        "question_type": "multiple_choice"
                    }

                nearest_buildable_questions.append(qa_entry)

            except Exception as e:
                # Log error but continue with other prototypes
                print(f"Error finding buildable position for {prototype.value[0]}: {e}")
                continue

        state.metadata["nearest_buildable_questions"] = nearest_buildable_questions
        return state

    return solve


@solver
def nearest_buildable_with_resources_questions(
        questions_per_position: int = 3,
        multiple_choice: bool = True
) -> Solver:
    """
    Generate questions about nearest buildable positions for resource-dependent entities
    like mining drills that need to be placed on resource patches.
    """

    # Prototypes that need resources
    RESOURCE_DEPENDENT_PROTOTYPES = [
        (Prototype.BurnerMiningDrill, ["iron-ore", "copper-ore", "coal", "stone"]),
        (Prototype.ElectricMiningDrill, ["iron-ore", "copper-ore", "coal", "stone"]),
        (Prototype.PumpJack, ["crude-oil"]),
        (Prototype.OffshorePump, ["water"])
    ]

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        instance = state.metadata.get('instance')
        renderer = state.metadata.get('renderer')

        if not instance:
            state.metadata["error"] = "No instance found"
            state.metadata["nearest_buildable_resource_questions"] = []
            return state

        questions = []

        characters = list(filter(lambda x: x.name == 'character', renderer.entities))
        player_position = None
        if len(characters) == 1:
            player_position = characters[0].position
        else:
            return state

        # Sample resource-dependent prototypes
        num_questions = min(questions_per_position, len(RESOURCE_DEPENDENT_PROTOTYPES))
        selected_items = random.sample(RESOURCE_DEPENDENT_PROTOTYPES, num_questions)

        for prototype, valid_resources in selected_items:
            try:
                width = prototype.WIDTH
                height = prototype.HEIGHT
                building_box = BuildingBox(width=width, height=height)

                # Get current position
                player_pos = player_position #instance.namespace.get_player().position
                center_pos = Position(x=player_pos.x, y=player_pos.y)

                # Find nearest buildable position (will consider resource requirements)
                buildable_area = instance.namespace.nearest_buildable(
                    entity=prototype,
                    building_box=building_box,
                    center_position=center_pos
                )

                nearest_pos = buildable_area.center

                # Determine which resource this would be on
                resource_type = "a resource patch"
                if prototype == Prototype.PumpJack:
                    resource_type = "crude oil"
                elif prototype == Prototype.OffshorePump:
                    resource_type = "water"
                else:
                    resource_type = "ore"

                if not multiple_choice:
                    question = (
                        f"What is the position of the nearest {resource_type} where I can build a {prototype.value[0]}?"
                    )
                    answer = f"Position(x={nearest_pos.x}, y={nearest_pos.y})"

                    qa_entry = {
                        "question": question,
                        "answer": answer,
                        "prototype": prototype.value[0],
                        "resource_type": resource_type,
                        "building_box": {"width": width, "height": height},
                        "buildable_position": {"x": nearest_pos.x, "y": nearest_pos.y},
                        "question_type": "open_ended"
                    }
                else:
                    # Generate distractors
                    distractors = []
                    offsets = [(-8, -8), (10, 0), (0, -10), (7, 7), (-5, 5), (5, -5)]

                    for offset_x, offset_y in random.sample(offsets, 3):
                        distractor = Position(
                            x=center_pos.x + offset_x,
                            y=center_pos.y + offset_y
                        )
                        distractors.append(distractor)

                    options = distractors + [nearest_pos]
                    random.shuffle(options)

                    alphabet = ['a', 'b', 'c', 'd']
                    option_strings = [
                        f"{alphabet[i]}) Position(x={pos.x}, y={pos.y})"
                        for i, pos in enumerate(options)
                    ]

                    correct_index = options.index(nearest_pos)

                    question = (
                        f"What is the position of the nearest {resource_type} where you can build a {prototype.value[0]}?\n"
                        f"Provide the correct letter and nothing else.\n"
                        f"{'\n'.join(option_strings)}"
                    )

                    qa_entry = {
                        "question": question,
                        "answer": alphabet[correct_index],
                        "prototype": prototype.value[0],
                        "resource_type": resource_type,
                        "building_box": {"width": width, "height": height},
                        "buildable_position": {"x": nearest_pos.x, "y": nearest_pos.y},
                        "options": [{"x": pos.x, "y": pos.y} for pos in options],
                        "correct_index": correct_index,
                        "question_type": "multiple_choice"
                    }

                questions.append(qa_entry)

            except Exception as e:
                print(f"Error with {prototype.value[0]}: {e}")
                continue

        state.metadata["nearest_buildable_resource_questions"] = questions
        return state

    return solve