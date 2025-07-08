import time

from fle.env import FactorioInstance


def run_string_benchmark(game: FactorioInstance, num_iterations: int = 100):
    benchmarks = {
        "place_entity_next_to": benchmark_place_entity_next_to_str,
        "place_entity": benchmark_place_entity_str,
        "move_to": benchmark_move_to_str,
        "harvest_resource": benchmark_harvest_resource_str,
        "craft_item": benchmark_craft_item_str,
        "connect_entities": benchmark_connect_entities_str,
        "rotate_entity": benchmark_rotate_entity_str,
        "insert_item": benchmark_insert_item_str,
        "extract_item": benchmark_extract_item_str,
        "inspect_inventory": benchmark_inspect_inventory_str,
        "get_resource_patch": benchmark_get_resource_patch_str,
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


def benchmark_place_entity_str(game: FactorioInstance, iterations: int):
    count = 0
    for i in range(iterations):
        try:
            game.eval(
                "place_entity(Prototype.TransportBelt, position=Position(x=0, y=0))"
            )
            count += 1
        except Exception:
            pass
    return count


def benchmark_place_entity_next_to_str(game: FactorioInstance, iterations: int):
    count = 0
    for i in range(iterations):
        try:
            cmd = f"""
reference_position = Position(x={i}, y=0)
entity = place_entity_next_to(
    Prototype.TransportBelt,
    reference_position=reference_position,
    direction=Direction.RIGHT,
    spacing=0
)
"""
            game.eval(cmd)
            count += 1
        except Exception:
            pass
    return count


def benchmark_move_to_str(game: FactorioInstance, iterations: int):
    count = 0
    for i in range(iterations):
        try:
            game.eval(f"move_to(Position(x={i}, y=0))")
            count += 1
        except Exception:
            pass
    return count


def benchmark_harvest_resource_str(game: FactorioInstance, iterations: int):
    count = 0
    # First find resource position
    game.eval("move_to(nearest(Resource.Coal))")

    for _ in range(iterations):
        try:
            game.eval("harvest_resource(nearest(Resource.Coal), quantity=1)")
            count += 1
        except Exception:
            pass
    return count


def benchmark_craft_item_str(game: FactorioInstance, iterations: int):
    count = 0
    for _ in range(iterations):
        try:
            game.eval("craft_item(Prototype.IronGearWheel, quantity=1)")
            count += 1
        except Exception:
            pass
    return count


def benchmark_connect_entities_str(game: FactorioInstance, iterations: int):
    game.eval("move_to(Position(x=0, y=0))")
    game.eval("place_entity(Prototype.TransportBelt, position=Position(x=0, y=0))")
    count = 0
    for i in range(1, iterations + 1):
        try:
            cmd = f"""
move_to(Position(x={i}, y=0))
place_entity(Prototype.TransportBelt, position=Position(x={i}, y=0))
connect_entities(Position(x={i - 1}, y=0), Position(x={i}, y=0), Prototype.TransportBelt)
"""
            game.eval(cmd)
            count += 1
        except Exception:
            pass
    return count


def benchmark_rotate_entity_str(game: FactorioInstance, iterations: int):
    game.eval("move_to(Position(x=0, y=0))")
    game.eval(
        "belt = place_entity(Prototype.TransportBelt, position=Position(x=0, y=0))"
    )
    count = 0
    for _ in range(iterations):
        try:
            game.eval("rotate_entity(belt, Direction.next_clockwise(belt.direction))")
            count += 1
        except Exception:
            pass
    return count


def benchmark_insert_item_str(game: FactorioInstance, iterations: int):
    game.eval("chest = place_entity(Prototype.IronChest, position=Position(x=0, y=0))")
    count = 0
    for _ in range(iterations):
        try:
            game.eval("insert_item(Prototype.IronPlate, chest, quantity=1)")
            count += 1
        except Exception:
            pass
    return count


def benchmark_extract_item_str(game: FactorioInstance, iterations: int):
    game.eval("chest = place_entity(Prototype.IronChest, position=Position(x=0, y=0))")
    game.eval(f"insert_item(Prototype.IronPlate, chest, quantity={iterations})")
    count = 0
    for _ in range(iterations):
        try:
            game.eval("extract_item(Prototype.IronPlate, chest.position, quantity=1)")
            count += 1
        except Exception:
            pass
    return count


def benchmark_inspect_inventory_str(game: FactorioInstance, iterations: int):
    count = 0
    for _ in range(iterations):
        try:
            game.eval("inspect_inventory()")
            count += 1
        except Exception:
            pass
    return count


def benchmark_get_resource_patch_str(game: FactorioInstance, iterations: int):
    count = 0
    for _ in range(iterations):
        try:
            game.eval("get_resource_patch(Resource.Coal, nearest(Resource.Coal))")
            count += 1
        except Exception:
            pass
    return count


def run_and_print_results(game: FactorioInstance, num_iterations: int = 100):
    results = run_string_benchmark(game, num_iterations)

    print(f"String-Based Benchmark Results (iterations: {num_iterations}):")
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
