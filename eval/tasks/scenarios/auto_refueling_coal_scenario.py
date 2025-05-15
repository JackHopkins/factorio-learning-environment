from env.src.entities import Direction, Position
from eval.tasks.scenarios.scenario_abc import ScenarioABC
from env.src.game_types import Resource, Prototype
from env.src.instance import FactorioInstance


class AutorefuelingCoalScenario(ScenarioABC):
    def __init__(self, num_drills=3):
        self.num_drills = num_drills

    def deploy(self, instance: FactorioInstance):
        instance.initial_inventory = {'stone-furnace': 1,
                                      'iron-chest': 5,
                                      'burner-inserter': 10,
                                      'coal': 50,
                                      'transport-belt': 100,
                                      'burner-mining-drill': 5}
        instance.reset()

        game = instance.namespaces[0]

        # Start at the origin
        game.move_to(Position(x=0, y=0))

        # Find the nearest coal patch
        coal_patch = game.get_resource_patch(Resource.Coal, game.nearest(Resource.Coal))

        # Move to the center of the coal patch
        game.move_to(coal_patch.bounding_box.left_top + Position(x=0, y=-5))

        # Place the first drill
        drill = game.place_entity(Prototype.BurnerMiningDrill, Direction.UP, coal_patch.bounding_box.left_top)

        # Place a chest next to the first drill to collect coal
        chest = game.place_entity(Prototype.IronChest, Direction.RIGHT, drill.drop_position)

        # Connect the first drill to the chest with an inserter
        inserter = game.place_entity_next_to(Prototype.BurnerInserter, chest.position, direction=Direction.UP, spacing=0)
        first_inserter = inserter

        # Place an inserter south of the drill to insert coal into the drill
        drill_bottom_y = drill.position.y + drill.dimensions.height
        drill_inserter = game.place_entity(Prototype.BurnerInserter, Direction.UP, Position(x=drill.position.x, y=drill_bottom_y))
        drill_inserter = game.rotate_entity(drill_inserter, Direction.UP)
        first_drill_inserter = drill_inserter

        # Start the transport belt from the chest
        game.move_to(inserter.drop_position)

        drills = []
        belt = None

        # Place additional drills and connect them to the belt
        for i in range(1, self.num_drills):
            # Place the next drill
            next_drill = game.place_entity_next_to(Prototype.BurnerMiningDrill, drill.position, Direction.RIGHT, spacing=2)
            next_drill = game.rotate_entity(next_drill, Direction.UP)
            drills.append(next_drill)

            try:
                # Place a chest next to the next drill to collect coal
                chest = game.place_entity(Prototype.IronChest, Direction.RIGHT, next_drill.drop_position)
            except Exception as e:
                print(f"Could not place chest next to drill: {e}")

            # Place an inserter to connect the chest to the transport belt
            next_inserter = game.place_entity_next_to(Prototype.BurnerInserter, chest.position, direction=Direction.UP, spacing=0)

            # Place an insert underneath the drill to insert coal into the drill
            drill_bottom_y = next_drill.position.y + next_drill.dimensions.height
            drill_inserter = game.place_entity(Prototype.BurnerInserter, Direction.UP, Position(x=next_drill.position.x, y=drill_bottom_y))
            drill_inserter = game.rotate_entity(drill_inserter, Direction.UP)

            # Extend the transport belt to the next drill
            if not belt:
                belt = game.connect_entities(first_inserter.drop_position, next_inserter.drop_position, Prototype.TransportBelt)
            else:
                belt = game.connect_entities(belt, next_inserter.drop_position, Prototype.TransportBelt)

            # Update the drill reference for the next iteration
            drill = next_drill
            inserter = next_inserter
            next_drill_inserter = drill_inserter

        # Connect the drop position of the final drill block to the inserter that is loading it with coal
        belt = game.connect_entities(belt, next_drill_inserter, Prototype.TransportBelt)

        # Connect that inserter to the inserter that is loading the first drill with coal
        belt = game.connect_entities(belt, first_drill_inserter, Prototype.TransportBelt)

        # Connect the first drill inserter to the drop point of the first inserter
        belt = game.connect_entities(belt, belt, Prototype.TransportBelt)

        #game.rotate_entity(belts[-1].belts[-1], Direction.RIGHT)
        # Initialize the system by adding some coal to each drill and inserter
        for drill in drills:
            game.insert_item(Prototype.Coal, drill, 5)

        print(f"Auto-refilling coal mining system with {self.num_drills} drills has been built!")