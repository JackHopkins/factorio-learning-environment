import base64
import json
import time
import zlib
from copy import deepcopy

import pytest

from fle.env.entities import Position, Direction
from fle.env.game_types import Prototype


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        "burner-mining-drill": 5,
        "electric-mining-drill": 20,
        "small-electric-pole": 10,
        "underground-belt": 10,
        "small-lamp": 10,
        "stone-furnace": 10,
        "burner-inserter": 10,
        "transport-belt": 100,
        "iron-chest": 1,
        "wooden-chest": 2,
        "iron-ore": 5,
        "coal": 50,
        "assembling-machine-1": 1,
        "inserter": 10,
    }
    instance.reset()
    yield instance.namespace


def decode_blueprint(encoded_data):
    """
    Decode a Factorio blueprint from Base64
    Returns both the encoded and decoded data
    """
    try:
        # Remove the "0" version prefix if present
        if encoded_data.startswith("0"):
            encoded_data = encoded_data[1:]

        # Decode Base64
        decoded_data = base64.b64decode(encoded_data)

        # Decompress if needed (Factorio uses zlib compression)
        try:
            decompressed_data = zlib.decompress(decoded_data)
            decoded_json = json.loads(decompressed_data)
        except zlib.error:
            # If decompression fails, try parsing directly (might not be compressed)
            decoded_json = json.loads(decoded_data)

        return {"encoded": encoded_data, "decoded": decoded_json}
    except Exception:
        return None


def test_fail_on_incorrect_blueprint(game):
    assert not game._load_blueprint("BLHA", Position(x=0, y=0))


def test_belt_inserter_chain(game):
    # Test belt and inserter chain
    belt1 = game.place_entity(
        Prototype.TransportBelt, Direction.EAST, Position(x=0, y=0)
    )
    game.place_entity(Prototype.TransportBelt, Direction.EAST, Position(x=1, y=0))
    game.place_entity(Prototype.Inserter, Direction.NORTH, Position(x=1, y=1))
    chest = game.place_entity(
        Prototype.WoodenChest, Direction.NORTH, Position(x=1, y=2)
    )

    game.insert_item(Prototype.IronOre, belt1, quantity=5)
    game.insert_item(Prototype.Coal, chest, quantity=5)

    entities = game._save_entity_state(distance=30, player_entities=True)
    game.reset()
    assert game._load_entity_state(entities)
    pass


def test_save_load1(game):
    furnace = game.place_entity(
        Prototype.StoneFurnace, Direction.UP, Position(x=5, y=0)
    )
    game.insert_item(Prototype.Coal, furnace, quantity=5)
    game.insert_item(Prototype.IronOre, furnace, quantity=5)
    game.move_to(Position(x=20, y=20))
    game.instance.speed(1)
    entities = game._save_entity_state(distance=30, player_entities=True)
    copied_entities = deepcopy(entities)
    game.instance.reset()
    assert game._load_entity_state(entities)
    entities = game._save_entity_state(distance=30, player_entities=True)
    game.instance.speed(1)
    assert (
        copied_entities[0]["burner"]["inventory"]["coal"]
        == entities[0]["burner"]["inventory"]["coal"]
    )


def test_benchmark(game):
    furnace = game.place_entity(
        Prototype.StoneFurnace, Direction.UP, Position(x=5, y=0)
    )
    game.insert_item(Prototype.Coal, furnace, quantity=5)
    game.insert_item(Prototype.IronOre, furnace, quantity=5)
    game.move_to(Position(x=20, y=20))

    save_times = []
    load_times = []
    lengths = []
    # TODO: This test gets stuck for macbook m4 for 100 iterations
    for i in range(10):
        save_start = time.time()
        entities = game._save_entity_state(distance=100, encode=True, compress=True)
        lengths.append(len(entities))
        save_end = time.time()

        game.reset()

        load_start = time.time()
        game._load_entity_state(entities, decompress=True)
        load_end = time.time()

        save_times.append(save_end - save_start)
        load_times.append(load_end - load_start)
    print()
    print(
        f"Average save time: {(sum(save_times) / len(save_times)) * 1000} milliseconds (player entities)"
    )
    print(
        f"Average load time: {(sum(load_times) / len(load_times)) * 1000} milliseconds (player entities)"
    )
    print(f"Average length of saved data: {sum(lengths) / len(lengths)} bytes")
