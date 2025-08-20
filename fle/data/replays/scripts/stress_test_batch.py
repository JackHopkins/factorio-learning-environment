#!/usr/bin/env python3

import sys
import os
import time
import random

# Add the FLE package to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))

from fle.env.instance import FactorioInstance
from fle.env.entities import Position


def stress_test_batch_processing():
    """Stress test script that executes 2000 move_to commands over 20000 ticks."""

    print("=== Factorio Server Stress Test: 2000 Commands over 20000 Ticks ===\n")

    # Create a Factorio instance
    instance = FactorioInstance(
        address="localhost",
        tcp_port=27000,
        inventory={
            "stone": 10,  # Minimal inventory since we're just moving
        },
        fast=True,
    )

    namespace = instance.namespace

    try:
        print("0. Resetting instance...")
        instance.reset()

        # Configuration
        TOTAL_COMMANDS = 2000
        TOTAL_TICKS = 20000
        TICKS_PER_COMMAND = 10  # 1 command every 10 ticks
        BATCH_SIZE = 1000  # Process in batches of 200 commands to avoid overwhelming

        print("   Configuration:")
        print(f"   - Total commands: {TOTAL_COMMANDS}")
        print(f"   - Total ticks: {TOTAL_TICKS}")
        print(f"   - Ticks per command: {TICKS_PER_COMMAND}")
        print(f"   - Batch size: {BATCH_SIZE}")
        print(f"   - Number of batches: {TOTAL_COMMANDS // BATCH_SIZE}")

        # Generate random positions for movement (within a reasonable area)
        def generate_random_position():
            x = random.uniform(-50, 50)  # Random x between -50 and 50
            y = random.uniform(-50, 50)  # Random y between -50 and 50
            return Position(x=x, y=y)

        total_start_time = time.time()
        total_results_received = 0
        total_successful = 0
        total_failed = 0

        # Process commands in batches
        num_batches = TOTAL_COMMANDS // BATCH_SIZE

        for batch_num in range(num_batches):
            print(f"\n=== BATCH {batch_num + 1}/{num_batches} ===")

            instance.batch_manager.activate()

            batch_commands = []
            start_command = batch_num * BATCH_SIZE
            end_command = min((batch_num + 1) * BATCH_SIZE, TOTAL_COMMANDS)

            # Add commands to this batch
            for i in range(start_command, end_command):
                tick = i * TICKS_PER_COMMAND
                position = generate_random_position()

                result = namespace.move_to(position, tick=tick)
                batch_commands.append(
                    (
                        f"Move to ({position.x:.1f}, {position.y:.1f}) at tick {tick}",
                        result,
                        tick,
                    )
                )

            print(f"   Added {len(batch_commands)} commands to batch {batch_num + 1}")
            print(f"   Command range: {start_command} to {end_command - 1}")
            print(
                f"   Tick range: {start_command * TICKS_PER_COMMAND} to {(end_command - 1) * TICKS_PER_COMMAND}"
            )

            # Submit batch and stream results
            batch_start_time = time.time()
            batch_results_received = 0
            batch_successful = 0
            batch_failed = 0
            first_result_time = None

            print("   Submitting batch and streaming results...")

            for result in instance.batch_manager.submit_batch_and_stream(
                timeout_seconds=600, poll_interval=0.1
            ):
                batch_results_received += 1
                total_results_received += 1

                if first_result_time is None:
                    first_result_time = time.time() - batch_start_time

                if result["success"]:
                    batch_successful += 1
                    total_successful += 1
                else:
                    batch_failed += 1
                    total_failed += 1

                # Print progress every 50 results or for failed commands
                if batch_results_received % 50 == 0 or not result["success"]:
                    elapsed = time.time() - batch_start_time
                    print(
                        f"     ✓ Batch progress: {batch_results_received}/{len(batch_commands)} "
                        f"results received after {elapsed:.2f}s"
                    )

                    if not result["success"]:
                        print(
                            f"     ✗ Command failed: {result['command']} - {result['result']}"
                        )

            batch_time = time.time() - batch_start_time

            print(f"   Batch {batch_num + 1} completed:")
            print(f"     - Results received: {batch_results_received}")
            print(f"     - Successful: {batch_successful}")
            print(f"     - Failed: {batch_failed}")
            print(f"     - Batch time: {batch_time:.2f}s")
            print(f"     - First result time: {first_result_time:.2f}s")
            print(
                f"     - Commands per second: {batch_results_received / batch_time:.1f}"
            )

            instance.batch_manager.deactivate()

            # Brief pause between batches to let the server recover
            if batch_num < num_batches - 1:
                print("   Pausing 2 seconds before next batch...")
                time.sleep(2)

        total_time = time.time() - total_start_time

        print("\n=== STRESS TEST COMPLETE ===")
        print("Summary:")
        print(f"  - Total commands sent: {TOTAL_COMMANDS}")
        print(f"  - Total results received: {total_results_received}")
        print(f"  - Successful commands: {total_successful}")
        print(f"  - Failed commands: {total_failed}")
        print(
            f"  - Success rate: {(total_successful / total_results_received * 100):.1f}%"
        )
        print(f"  - Total execution time: {total_time:.2f}s")
        print(
            f"  - Average commands per second: {total_results_received / total_time:.1f}"
        )
        print(f"  - Expected game duration: {TOTAL_TICKS} ticks")

        if total_failed > 0:
            print(
                f"\n⚠️  Warning: {total_failed} commands failed. Check server logs for details."
            )
        else:
            print("\n✅ All commands completed successfully!")

    except Exception as e:
        print(f"Error during stress test: {e}")
        instance.batch_manager.deactivate()
        raise

    finally:
        instance.cleanup()


if __name__ == "__main__":
    print("⚠️  Running FULL stress test - this will take several minutes!")
    stress_test_batch_processing()
