from time import sleep
from typing import List

import pytest

from factorio_entities import Entity, Position
from factorio_instance import Direction
from factorio_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance

def test_factorio_setup(game):
    """
    Create a test setup in Factorio resembling the provided blueprint.
    :param game:
    :return:
    """

    # Set starting position for placing entities
    coal_position = game.nearest(Resource.Coal)
    game.move_to(coal_position)
    coal_patch = game.get_resource_patch(Resource.Coal, coal_position)
    coal_bounding_box = coal_patch.bounding_box

    coal_center = Position(x=(coal_bounding_box.left_top.x + coal_bounding_box.right_bottom.x) / 2,
                            y=(coal_bounding_box.left_top.y + coal_bounding_box.right_bottom.y) / 2)

    game.move_to(coal_center)

    burner_mining_drill = game.place_entity(Prototype.BurnerMiningDrill, position=coal_center, direction=Direction.UP)

    burner_inserter = game.place_entity_next_to(Prototype.BurnerInserter,
                                                reference_position=burner_mining_drill.position,
                                                spacing=1,
                                                direction=Direction.DOWN)
    mining_drills = [burner_mining_drill]
    inserters = [burner_inserter]

    for i in range(0, 2):
        mining_drills.append(game.place_entity(Prototype.BurnerMiningDrill,
                                                position=Position(x=coal_center.x + mining_drills[-1].tile_dimensions.tile_width * (i + 1),
                                                                  y=coal_center.y),
                                                direction=Direction.UP))
        inserters.append(game.place_entity_next_to(Prototype.BurnerInserter,
                                                    reference_position=mining_drills[-1].position,
                                                    spacing=1,
                                                    direction=Direction.DOWN))

    for last_inserter, inserter in zip(inserters[:-1], inserters[1:]):
        # Connect the pick up position of the new burner inserter to the pick up position of the previous inserter with a belt
        game.connect_entities(last_inserter.pickup_position, inserter.pickup_position, Prototype.TransportBelt)

    game.connect_entities(mining_drills[0].drop_position, inserters[0].pickup_position, Prototype.TransportBelt)

    # Connect the pick up position of the burner inserter to the drop off position of the mining drill with a belt
    game.connect_entities(first_burner_mining_drill.drop_position, first_burner_inserter.pickup_position,
                          Prototype.TransportBelt)






