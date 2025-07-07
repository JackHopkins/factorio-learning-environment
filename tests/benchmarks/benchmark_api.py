import time
from fle.env import FactorioInstance, Direction
from entities import Position
from game_types import Prototype, Resource


def run_benchmark(game: FactorioInstance, num_iterations: int = 100):
    benchmarks = {
        "place_entity_next_to": benchmark_place_entity_next_to,
        "place_entity": benchmark_place_entity,
        "move_to": benchmark_move_to,
        "harvest_resource": benchmark_harvest_resource,
        "craft_item": benchmark_craft_item,
        "connect_entities": benchmark_connect_entities,
        "rotate_entity": benchmark_rotate_entity,
        "insert_item": benchmark_insert_item,
        "extract_item": benchmark_extract_item,
        "inspect_inventory": benchmark_inspect_inventory,
        "get_resource_patch": benchmark_get_resource_patch,
    }

    results = {}

    game.speed(10)
    for name, func in benchmarks.items():
        start_time = time.time()
        count = func(game, num_iterations)
        end_time = time.time()
        game.reset()
        duration = end_time - start_time
        ops_per_second = count / duration
        ops_per_minute = ops_per_second * 60

        results[name] = {
            "operations": count,
            "duration": duration,
            "ops_per_second": ops_per_second,
            "ops_per_minute": ops_per_minute,
        }

    return results


def benchmark_place_entity(game: FactorioInstance, iterations: int):
    count = 0
    for i in range(iterations):
        try:
            game.place_entity(Prototype.TransportBelt, position=Position(x=0, y=0))
            count += 1
        except Exception:
            pass
    return count


def benchmark_place_entity_next_to(game: FactorioInstance, iterations: int):
    count = 0
    reference_position = Position(x=0, y=0)
    for i in range(iterations):
        try:
            entity = game.place_entity_next_to(
                Prototype.TransportBelt,
                reference_position=reference_position,
                direction=Direction.RIGHT,
                spacing=0,
            )
            reference_position = entity.position
            count += 1
        except Exception:
            pass
    return count


def benchmark_move_to(game: FactorioInstance, iterations: int):
    count = 0
    for i in range(iterations):
        try:
            game.move_to(Position(x=i, y=0))
            count += unrealistic_instruction_penalty(count)
        except Exception:
            pass
    return count


def benchmark_harvest_resource(game: FactorioInstance, iterations: int):
    resource_position = game.nearest(Resource.Coal)
    count = 0
    game.move_to(resource_position)
    for _ in range(iterations):
        try:
            game.harvest_resource(resource_position, quantity=1)
            count += unrealistic_instruction_penalty(count)
        except Exception:
            pass
    return count


def benchmark_craft_item(game: FactorioInstance, iterations: int):
    count = 0
    for _ in range(iterations):
        try:
            game.craft_item(Prototype.IronGearWheel, quantity=1)
            count += 1
        except Exception:
            pass
    return count


def benchmark_connect_entities(game: FactorioInstance, iterations: int):
    game.move_to(Position(x=0, y=0))
    game.place_entity(Prototype.TransportBelt, position=Position(x=0, y=0))
    count = 0
    for i in range(1, iterations + 1):
        try:
            game.move_to(Position(x=i, y=0))
            game.place_entity(Prototype.TransportBelt, position=Position(x=i, y=0))
            game.connect_entities(
                Position(x=i - 1, y=0), Position(x=i, y=0), Prototype.TransportBelt
            )
            count += 1
        except Exception:
            pass
    return count


def benchmark_rotate_entity(game: FactorioInstance, iterations: int):
    game.move_to(Position(x=0, y=0))
    entity = game.place_entity(Prototype.TransportBelt, position=Position(x=0, y=0))
    count = 0
    for _ in range(iterations):
        try:
            game.rotate_entity(entity, Direction.next_clockwise(entity.direction))
            count += 1
        except Exception:
            pass
    return count


def benchmark_insert_item(game: FactorioInstance, iterations: int):
    chest = game.place_entity(Prototype.IronChest, position=Position(x=0, y=0))
    count = 0
    for _ in range(iterations):
        try:
            game.insert_item(Prototype.IronPlate, chest, quantity=1)
            count += 1
        except Exception:
            pass
    return count


def benchmark_extract_item(game: FactorioInstance, iterations: int):
    chest = game.place_entity(Prototype.IronChest, position=Position(x=0, y=0))
    game.insert_item(Prototype.IronPlate, chest, quantity=iterations)
    count = 0
    for _ in range(iterations):
        try:
            game.extract_item(Prototype.IronPlate, chest.position, quantity=1)
            count += 1
        except Exception:
            pass
    return count


def benchmark_inspect_inventory(game: FactorioInstance, iterations: int):
    count = 0
    for _ in range(iterations):
        try:
            game.inspect_inventory()
            count += 1
        except Exception:
            pass
    return count


def benchmark_get_resource_patch(game: FactorioInstance, iterations: int):
    resource_position = game.nearest(Resource.Coal)
    count = 0
    for _ in range(iterations):
        try:
            game.get_resource_patch(Resource.Coal, resource_position)
            count += 1
        except Exception:
            pass
    return count


def unrealistic_instruction_penalty(count):
    # Apply a penalty for very fast unrealistic instructions
    # return 1 if count % 5 == 0 else 0
    return 1


def run_and_print_results(game: FactorioInstance, num_iterations: int = 100):
    results = run_benchmark(game, num_iterations)

    print(f"Benchmark Results (iterations: {num_iterations}):")
    print("-" * 80)
    print(
        f"{'Operation':<20} {'Ops/Min':<10} {'Ops/Sec':<10} {'Duration':<10} {'Count':<10}"
    )
    print("-" * 80)

    for name, data in results.items():
        print(
            f"{name:<20} {data['ops_per_minute']:.2f} {data['ops_per_second']:.2f} {data['duration']:.2f}s {data['operations']}"
        )

    total_ops = sum(data["operations"] for data in results.values())
    total_duration = sum(data["duration"] for data in results.values())
    total_ops_per_minute = (total_ops / total_duration) * 60

    print("-" * 80)
    print(
        f"{'Total':<20} {total_ops_per_minute:.2f} {total_ops / total_duration:.2f} {total_duration:.2f}s {total_ops}"
    )


if __name__ == "__main__":
    inventory = {
        "iron-plate": 500,
        "copper-plate": 200,
        "coal": 200,
        "stone": 200,
        "iron-gear-wheel": 200,
        "transport-belt": 1000,
        "burner-inserter": 200,
        "assembling-machine-1": 20,
        "iron-chest": 10,
    }
    game = FactorioInstance(
        address="localhost",
        bounding_box=200,
        tcp_port=27000,
        fast=True,
        cache_scripts=False,
        inventory=inventory,
    )
    run_and_print_results(game)
