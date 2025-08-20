#!/usr/bin/env python3

import sys
import os
import time

# Add the FLE package to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))

from fle.env.instance import FactorioInstance
from fle.env.entities import (
    Position,
    Direction,
    Dimensions,
    TileDimensions,
    PlaceholderEntity,
)
from fle.env.game_types import Prototype


def convert_dict_to_entity(entity_dict):
    """Convert dictionary entity data to proper Entity object."""
    if not isinstance(entity_dict, dict):
        return entity_dict

    # Find the matching Prototype
    matching_prototype = None
    for prototype in Prototype:
        if prototype.value[0] == entity_dict["name"].replace("_", "-"):
            matching_prototype = prototype
            break

    if matching_prototype is None:
        print(f"Warning: No matching Prototype found for {entity_dict['name']}")
        return entity_dict

    # Get the metaclass from the prototype
    metaclass = matching_prototype.value[1]
    while isinstance(metaclass, tuple):
        metaclass = metaclass[1]

    # Convert the entity data
    entity_data = entity_dict.copy()

    # Convert direction from int to Direction enum
    if "direction" in entity_data and isinstance(entity_data["direction"], int):
        direction_value = entity_data["direction"]
        # Convert factorio direction (0,2,4,6) to Direction enum
        direction_map = {
            0: Direction.UP,
            2: Direction.RIGHT,
            4: Direction.DOWN,
            6: Direction.LEFT,
        }
        entity_data["direction"] = direction_map.get(direction_value, Direction.UP)

    # Convert position dict to Position object
    if "position" in entity_data and isinstance(entity_data["position"], dict):
        pos_dict = entity_data["position"]
        entity_data["position"] = Position(x=pos_dict["x"], y=pos_dict["y"])

    # Convert dimensions dict to Dimensions object
    if "dimensions" in entity_data and isinstance(entity_data["dimensions"], dict):
        dim_dict = entity_data["dimensions"]
        entity_data["dimensions"] = Dimensions(
            width=dim_dict["width"], height=dim_dict["height"]
        )

    # Convert tile_dimensions dict to TileDimensions object
    if "tile_dimensions" in entity_data and isinstance(
        entity_data["tile_dimensions"], dict
    ):
        tile_dim_dict = entity_data["tile_dimensions"]
        entity_data["tile_dimensions"] = TileDimensions(
            tile_width=tile_dim_dict["tile_width"],
            tile_height=tile_dim_dict["tile_height"],
        )

    # Convert warnings dict to list of strings
    if "warnings" in entity_data and isinstance(entity_data["warnings"], dict):
        warnings_dict = entity_data["warnings"]
        entity_data["warnings"] = list(warnings_dict.values())

    # Add the prototype to the entity data
    entity_data["prototype"] = matching_prototype

    # Remove any empty values that might cause issues
    entity_data = {
        k: v for k, v in entity_data.items() if v is not None or isinstance(v, int)
    }

    try:
        # Create the Entity object
        entity = metaclass(**entity_data)
        return entity
    except Exception as e:
        print(f"Could not create {entity_data['name']} Entity object: {e}")
        print(f"Entity data: {entity_data}")
        return entity_dict  # Return original dict if conversion fails


def example_batch_streaming():
    """Example showing streaming batch execution where results are yielded as they become available."""

    # Create a Factorio instance with expanded inventory for more complex operations
    instance = FactorioInstance(
        address="localhost",
        tcp_port=27000,
        inventory={
            "stone": 50,
            "iron-ore": 30,
            "coal": 20,  # Added coal for furnace fuel demonstration
            "burner-mining-drill": 10,
            "stone-furnace": 10,
            "transport-belt": 20,
            "inserter": 10,
            "assembling-machine-1": 5,
            "iron-plate": 20,
            "copper-plate": 10,
            "iron-gear-wheel": 5,
            "iron-chest": 5,
        },
        fast=True,
    )

    namespace = instance.namespace

    try:
        print(
            "=== Enhanced Streaming Batch Processing Example (Two-Batch Approach) ===\n"
        )

        # Reset the instance to clean state
        print("0. Resetting instance...")
        instance.reset()

        # current_tick = instance.get_elapsed_ticks()
        current_tick = 0
        print(f"   Current game tick: {current_tick}")

        # ===================== FIRST BATCH =====================
        print("1. First batch: Creating entities and basic operations...")
        instance.batch_manager.activate()

        # Add commands that don't depend on entity references
        commands_info_batch1 = []

        # Command 1: Set research first (quick operation)
        # tick1 = current_tick + 5
        # result1 = namespace.set_research(Technology.Automation, tick=tick1)
        # commands_info_batch1.append(
        #     (f"Set research to Automation at tick {tick1}", result1)
        # )

        # Command 2: Move to working area
        tick2 = current_tick + 20
        result2 = namespace.move_to(Position(x=10, y=5), tick=tick2)
        commands_info_batch1.append((f"Move to (10,5) at tick {tick2}", result2))

        # Command 3: Harvest some stone nearby
        tick3 = current_tick + 80
        result3 = namespace.harvest_resource(
            Position(x=12, y=5), quantity=10, tick=tick3
        )
        commands_info_batch1.append(
            (f"Harvest iron ore at (12,5) at tick {tick3}", result3)
        )

        # Command 4: Craft some iron gear wheels
        tick4 = current_tick + 130
        result4 = namespace.craft_item(Prototype.IronGearWheel, quantity=3, tick=tick4)
        commands_info_batch1.append(
            (f"Craft 3 iron gear wheels at tick {tick4}", result4)
        )

        # Command 5: Place stone furnace
        tick5 = current_tick + 180
        result5 = namespace.place_entity(
            Prototype.StoneFurnace, position=Position(x=10, y=6), tick=tick5
        )
        commands_info_batch1.append(
            (f"Place stone furnace at (10,6) at tick {tick5}", result5)
        )

        # Command 6: Place iron chest (for insert/extract operations)
        tick6 = current_tick + 220
        result6 = namespace.place_entity(
            Prototype.IronChest, position=Position(x=10, y=7), tick=tick6
        )
        commands_info_batch1.append(
            (f"Place iron chest at (10,7) at tick {tick6}", result6)
        )

        # Command 7: Place inserter (we'll need this entity for batch 2)
        tick7 = current_tick + 260
        result7 = namespace.place_entity(
            Prototype.Inserter, position=Position(x=11, y=6), tick=tick7
        )
        commands_info_batch1.append(
            (f"Place inserter at (11,6) at tick {tick7}", result7)
        )

        # Command 8: Place assembling machine (we'll need this entity for batch 2)
        tick8 = current_tick + 300
        result8 = namespace.place_entity(
            Prototype.AssemblingMachine1, position=Position(x=11, y=10), tick=tick8
        )
        commands_info_batch1.append(
            (f"Place assembling machine at (11,10) at tick {tick8}", result8)
        )

        # Command 9: Insert iron plates into the chest using PlaceholderEntity
        # Create a PlaceholderEntity for the chest we placed earlier
        chest_placeholder = PlaceholderEntity(
            name="iron-chest", position=Position(x=10, y=7)
        )
        tick9 = current_tick + 340
        result9 = namespace.insert_item(
            Prototype.IronPlate, chest_placeholder, quantity=10, tick=tick9
        )
        commands_info_batch1.append(
            (
                f"Insert 10 iron plates into chest using PlaceholderEntity at tick {tick9}",
                result9,
            )
        )

        # Command 10: Extract iron plates from the chest using PlaceholderEntity
        tick10 = current_tick + 380
        result10 = namespace.extract_item(
            Prototype.IronPlate, chest_placeholder, quantity=5, tick=tick10
        )
        commands_info_batch1.append(
            (
                f"Extract 5 iron plates from chest using PlaceholderEntity at tick {tick10}",
                result10,
            )
        )

        print("   Commands added to first batch:")
        for desc, result in commands_info_batch1:
            print(f"     {desc}: {result}")

        # Submit first batch and stream results as they arrive
        print("\n2. Submitting first batch and streaming results...")
        start_time = time.time()

        batch1_results = {}  # Store results indexed by command_index
        batch1_results_count = 0

        # Stream results from first batch
        for result in instance.batch_manager.submit_batch_and_stream(
            timeout_seconds=30, poll_interval=0.05
        ):
            batch1_results_count += 1
            elapsed = time.time() - start_time
            command_index = result["command_index"]

            # Store the result for later entity extraction
            batch1_results[command_index] = result

            print(
                f"   ✓ First batch result {batch1_results_count} received after {elapsed:.2f}s:"
            )
            print(f"     Command: {result['command']} (index {command_index})")
            print(f"     Success: {result['success']}")
            if result["success"]:
                print(f"     Result: {result['result']}")
            else:
                print(f"     Error: {result['result']}")
            print()

        batch1_time = time.time() - start_time
        print(
            f"   First batch completed in {batch1_time:.2f}s with {batch1_results_count} results"
        )

        # Extract real entity references from first batch streamed results
        # result7 is the inserter (index 6), result8 is the assembling machine (index 7)
        # result5 is the stone furnace (index 4), result6 is the iron chest (index 5)
        # result9 is insert_item (index 8), result10 is extract_item (index 9)
        inserter_entity = None
        assembling_machine_entity = None
        stone_furnace_entity = None
        iron_chest_entity = None

        for command_index, result in batch1_results.items():
            if result["success"]:
                if command_index == 5:  # result7 - inserter
                    inserter_entity = convert_dict_to_entity(result["result"])
                    print(f"     ✓ Inserter entity created: {inserter_entity}")
                elif command_index == 6:  # result8 - assembling machine
                    assembling_machine_entity = convert_dict_to_entity(result["result"])
                    print(
                        f"     ✓ Assembling machine entity created: {assembling_machine_entity}"
                    )
                elif command_index == 3:  # result5 - stone furnace
                    stone_furnace_entity = convert_dict_to_entity(result["result"])
                    print(
                        f"     ✓ Stone furnace entity created: {stone_furnace_entity}"
                    )
                elif command_index == 4:  # result6 - iron chest
                    iron_chest_entity = convert_dict_to_entity(result["result"])
                    print(f"     ✓ Iron chest entity created: {iron_chest_entity}")
                elif command_index == 7:  # result9 - insert_item
                    print(f"     ✓ Insert item command executed: {result['result']}")
                elif command_index == 8:  # result10 - extract_item
                    print(f"     ✓ Extract item command executed: {result['result']}")
            else:
                print(f"     ✗ Command {command_index + 1} failed: {result['result']}")

        instance.batch_manager.deactivate()

        # ===================== SECOND BATCH =====================
        print("\n3. Second batch: Operations using real entity references...")
        instance.batch_manager.activate()

        commands_info_batch2 = []

        # Update current tick after first batch execution
        # current_tick = instance.get_elapsed_ticks()
        current_tick = 0

        # Command 9: Rotate the inserter (using real entity reference)
        tick9 = current_tick + 40
        if inserter_entity:
            result9 = namespace.rotate_entity(inserter_entity, tick=tick9)
            commands_info_batch2.append((f"Rotate inserter at tick {tick9}", result9))
        else:
            print("     ⚠ Skipping inserter rotation - entity not available")

        # Command 10: Set recipe for assembling machine (using real entity reference)
        tick10 = current_tick + 80
        if assembling_machine_entity:
            result10 = namespace.set_entity_recipe(
                assembling_machine_entity, Prototype.IronGearWheel, tick=tick10
            )
            commands_info_batch2.append(
                (
                    f"Set assembling machine recipe to iron gear wheel at tick {tick10}",
                    result10,
                )
            )
        else:
            print(
                "     ⚠ Skipping recipe setting - assembling machine entity not available"
            )

        # Command 11: Extract items from furnace (using real entity reference)
        # Skip this for now since the furnace won't have any items yet
        # tick11 = current_tick + 120
        # if stone_furnace_entity:
        #     result11 = namespace.extract_item(Prototype.IronPlate, stone_furnace_entity, quantity=5, tick=tick11)
        #     commands_info_batch2.append((f"Extract 5 iron plates from furnace at tick {tick11}", result11))
        # else:
        #     print("     ⚠ Skipping item extraction - stone furnace entity not available")
        print(
            "     ℹ Skipping furnace extraction - furnace is empty (no iron ore was added)"
        )

        # Command 11: Insert coal into the stone furnace using PlaceholderEntity
        # This demonstrates referencing an entity created in the first batch
        furnace_placeholder = PlaceholderEntity(
            name="stone-furnace", position=Position(x=10, y=6)
        )
        tick11 = current_tick + 80
        result11 = namespace.insert_item(
            Prototype.Coal, furnace_placeholder, quantity=5, tick=tick11
        )
        commands_info_batch2.append(
            (
                f"Insert 5 coal into stone furnace using PlaceholderEntity at tick {tick11}",
                result11,
            )
        )

        # Command 12: Inspect inventory to see current state
        tick12 = current_tick + 120  # Moved up since we skipped command 11
        result12 = namespace.inspect_inventory(tick=tick12)
        commands_info_batch2.append((f"Inspect inventory at tick {tick12}", result12))

        # Command 13: Pick up the transport belt (cleanup) - use actual position
        tick13 = current_tick + 160  # Moved up since we skipped command 11
        if iron_chest_entity:
            result13 = namespace.pickup_entity(iron_chest_entity, tick=tick13)
            commands_info_batch2.append(
                (
                    f"Pick up iron chest at {iron_chest_entity.position} at tick {tick13}",
                    result13,
                )
            )
        else:
            print("     ⚠ Skipping iron chest pickup - entity not available")

        print("   Commands added to second batch:")
        for desc, result in commands_info_batch2:
            print(f"     {desc}: {result}")

        # Stream results from second batch as they become available
        print("\n4. Streaming results from second batch as they complete...")
        print("   (Results will appear as soon as each command finishes)\n")

        results_received = 0
        start_time = time.time()

        # Use the streaming method for second batch
        for result in instance.batch_manager.submit_batch_and_stream(
            timeout_seconds=25, poll_interval=0.05
        ):
            results_received += 1
            elapsed = time.time() - start_time

            print(f"   ✓ Result {results_received} received after {elapsed:.2f}s:")
            print(
                f"     Command: {result['command']} (index {result['command_index']})"
            )
            print(f"     Success: {result['success']}")
            print(f"     Executed at tick: {result['tick']}")

            if result["success"]:
                print(f"     Result: {result['result']}")
            else:
                print(f"     Error: {result['result']}")
            print()

        batch2_time = time.time() - start_time
        total_time = batch1_time + batch2_time
        print(
            f"   Second batch: {results_received} results received in {batch2_time:.2f}s"
        )
        print(f"   Total processing time: {total_time:.2f}s")

        # Deactivate batch mode
        print("\n5. Deactivating batch mode...")
        instance.batch_manager.deactivate()

        print("\n=== Enhanced two-batch streaming processing complete! ===")
        print("Summary:")
        print(
            f"  - First batch (entity creation): {batch1_results_count} commands in {batch1_time:.2f}s"
        )
        print(
            f"  - Second batch (entity operations): {results_received} commands in {batch2_time:.2f}s"
        )
        print(f"  - Total time: {total_time:.2f}s")

    except Exception as e:
        print(f"Error during batch processing: {e}")
        instance.batch_manager.deactivate()
        raise

    finally:
        instance.cleanup()


def comparison_example():
    """Compare streaming vs traditional batch processing."""

    print("=== Comparison: Streaming vs Traditional Batch Processing ===\n")

    instance = FactorioInstance(
        address="localhost",
        tcp_port=27000,
        inventory={
            "stone": 50,
            "transport-belt": 10,
            "inserter": 5,
            "iron-plate": 20,
            "coal": 10,
        },
    )

    namespace = instance.namespace

    try:
        # Reset instance
        instance.reset()

        # Test with traditional approach first
        print("1. Traditional batch processing (wait for all results):")
        instance.batch_manager.activate()

        current_tick = instance.get_elapsed_ticks()

        tick1 = current_tick + 10
        tick2 = current_tick + 70
        tick3 = current_tick + 130
        tick4 = current_tick + 180

        namespace.move_to(Position(x=5, y=5), tick=tick1)
        namespace.place_entity(
            Prototype.TransportBelt, position=Position(x=5, y=6), tick=tick2
        )
        namespace.craft_item(Prototype.IronGearWheel, quantity=2, tick=tick3)
        namespace.inspect_inventory(tick=tick4)

        start_time = time.time()
        results = instance.batch_manager.submit_batch_and_wait(timeout_seconds=15)
        traditional_time = time.time() - start_time

        print(
            f"   Traditional approach: received {len(results)} results in {traditional_time:.2f}s"
        )
        instance.batch_manager.deactivate()

        # Reset for next test
        instance.reset()

        # Test with streaming approach
        print("\n2. Streaming batch processing (results as available):")
        instance.batch_manager.activate()

        current_tick = instance.get_elapsed_ticks()

        tick1 = current_tick + 10
        tick2 = current_tick + 70
        tick3 = current_tick + 130
        tick4 = current_tick + 180

        namespace.move_to(Position(x=10, y=10), tick=tick1)
        namespace.place_entity(
            Prototype.TransportBelt, position=Position(x=10, y=11), tick=tick2
        )
        namespace.craft_item(Prototype.IronGearWheel, quantity=2, tick=tick3)
        namespace.inspect_inventory(tick=tick4)

        start_time = time.time()
        results_count = 0
        first_result_time = None

        for result in instance.batch_manager.submit_batch_and_stream(
            poll_interval=0.05
        ):
            results_count += 1
            if first_result_time is None:
                first_result_time = time.time() - start_time

        streaming_time = time.time() - start_time

        print(
            f"   Streaming approach: received {results_count} results in {streaming_time:.2f}s"
        )
        print(f"   First result available after: {first_result_time:.2f}s")

        instance.batch_manager.deactivate()

        print("\n3. Performance comparison:")
        print(f"   Traditional: {traditional_time:.2f}s (wait for all)")
        print(
            f"   Streaming: {streaming_time:.2f}s total, {first_result_time:.2f}s for first result"
        )
        print(
            f"   Benefit: Start processing results {traditional_time - first_result_time:.2f}s earlier!"
        )

    except Exception as e:
        print(f"Error during comparison: {e}")
        instance.batch_manager.deactivate()
        raise

    finally:
        instance.cleanup()


if __name__ == "__main__":
    print("Choose an example to run:")
    print("1. Enhanced streaming batch processing example")
    print("2. Comparison between streaming and traditional approaches")
    print("3. Run both examples")

    # choice = input("Enter choice (1-3): ").strip()
    choice = "1"
    if choice == "1":
        example_batch_streaming()
    elif choice == "2":
        comparison_example()
    elif choice == "3":
        example_batch_streaming()
        print("\n" + "=" * 60 + "\n")
        comparison_example()
    else:
        print("Invalid choice. Running streaming example by default.")
        example_batch_streaming()
