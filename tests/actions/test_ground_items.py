import pytest

from fle.env.entities import Position
from fle.env.game_types import Prototype, Resource


@pytest.fixture()
def game(configure_game):
    return configure_game(
        inventory={
            "burner-mining-drill": 10,
            "wooden-chest": 10,
            "stone-furnace": 10,
            "burner-inserter": 10,
            "transport-belt": 50,
            "coal": 50,
        }
    )


def _produce_ground_ore(game):
    """Place a fuelled drill on iron ore, sleep, and return (drill, drop_position)."""
    iron = game.nearest(Resource.IronOre)
    game.move_to(iron)
    drill = game.place_entity(Prototype.BurnerMiningDrill, position=iron)
    game.insert_item(Prototype.Coal, drill, quantity=50)
    # Let the drill mine long enough for ore to accumulate on the ground
    game.sleep(10)
    return drill, drill.drop_position


# ── Placement on ground items ────────────────────────────────────────────

def test_place_chest_on_ground_ore(game):
    """Placing a WoodenChest at a drill's drop position where ore has accumulated."""
    drill, drop_pos = _produce_ground_ore(game)
    game.move_to(drop_pos)
    chest = game.place_entity(Prototype.WoodenChest, position=drop_pos)
    assert chest is not None
    assert chest.name == "wooden-chest"


def test_place_furnace_on_ground_ore(game):
    """Placing a StoneFurnace where ore has accumulated.
    Pick up the drill first since the 2x2 furnace would collide with it."""
    drill, drop_pos = _produce_ground_ore(game)
    game.move_to(drill.position)
    game.pickup_entity(drill)
    game.move_to(drop_pos)
    furnace = game.place_entity(Prototype.StoneFurnace, position=drop_pos)
    assert furnace is not None
    assert furnace.name == "stone-furnace"


def test_place_inserter_on_ground_ore(game):
    """Placing a BurnerInserter at a drill's drop position where ore has accumulated."""
    drill, drop_pos = _produce_ground_ore(game)
    game.move_to(drop_pos)
    inserter = game.place_entity(Prototype.BurnerInserter, position=drop_pos)
    assert inserter is not None
    assert inserter.name == "burner-inserter"


# ── Pickup of ground items ───────────────────────────────────────────────

def test_pickup_ground_ore(game):
    """Pick up ore that has been mined onto the ground."""
    drill, drop_pos = _produce_ground_ore(game)
    game.move_to(drop_pos)
    game.pickup_entity(Prototype.IronOre, drop_pos)
    inv = game.inspect_inventory()
    assert inv[Prototype.IronOre] >= 1


def test_pickup_ground_ore_then_place(game):
    """Pick up ground ore first, then place an entity at the cleared position."""
    drill, drop_pos = _produce_ground_ore(game)
    game.move_to(drop_pos)
    game.pickup_entity(Prototype.IronOre, drop_pos)
    chest = game.place_entity(Prototype.WoodenChest, position=drop_pos)
    assert chest is not None
    assert chest.name == "wooden-chest"


# ── Connect entities over ground items ───────────────────────────────────

def test_connect_belts_over_ground_ore(game):
    """Run transport belts through a position where ore is on the ground."""
    drill, drop_pos = _produce_ground_ore(game)
    # Build a belt line that passes through the drop position
    start = Position(x=drop_pos.x - 3, y=drop_pos.y)
    end = Position(x=drop_pos.x + 3, y=drop_pos.y)
    game.move_to(drop_pos)
    belts = game.connect_entities(start, end, Prototype.TransportBelt)
    assert belts is not None
