"""
Factorio batch processors with different execution strategies.

Classes:
- BatchProcessor: Base class for batch processing logic
- SequentialProcessor: Sequential batch processing implementation
- PipelineProcessor: Pipeline batch processing implementation
"""

import time
from pathlib import Path
from typing import Dict, Any, List, Tuple

from run_actions_utils import (
    load_events,
    create_factorio_instance,
    parse_function_call,
    initialize_logging,
    cleanup_logging,
)
from action_converter import ActionConverter
from periodic_logger import PeriodicLogger
from processing_config import ProcessingConfig


class BatchProcessor:
    """Base class for batch processing logic."""

    def __init__(self, config: ProcessingConfig):
        self.config = config
        self.instance = None
        self.periodic_logger = None

    def setup(self):
        """Initialize the Factorio instance and logging."""
        self.instance = create_factorio_instance(self.config.max_concurrent_batches)
        self.instance.reset()
        self.instance.speed(self.config.speed)
        print("Factorio instance created and reset")

        # Setup logging
        if self.config.enable_logging:
            initialize_logging()
            print("Logging enabled - data will be saved to logs/")
        else:
            print("Logging disabled - no data will be saved")

        # Setup periodic logging
        periodic_log_file = None
        if self.config.enable_periodic_logging:
            events_path = Path(self.config.events_file_path)
            periodic_log_file = (
                events_path.parent / f"{events_path.stem}_periodic_data.jsonl"
            )
            print(
                f"Periodic logging enabled - data will be saved to {periodic_log_file} every {self.config.periodic_log_interval} ticks"
            )

        self.periodic_logger = PeriodicLogger(
            str(periodic_log_file) if periodic_log_file else None,
            self.config.periodic_log_interval,
        )

    def cleanup(self):
        """Clean up resources."""
        try:
            if self.instance:
                # Emergency cleanup for all batch managers
                print("🧹 Performing final server cleanup...")
                for manager in self.instance.batch_managers:
                    try:
                        manager.emergency_cleanup()
                    except Exception as e:
                        print(
                            f"Warning: Manager {manager.manager_id} cleanup failed: {e}"
                        )

                # Final server cleanup
                self.instance.begin_transaction()
                self.instance.add_command(
                    "/sc global.actions.reset_sequence()", raw=True
                )
                self.instance.add_command(
                    "/sc global.actions.clear_batch_results()", raw=True
                )
                self.instance.execute_transaction()
                print("✅ Final server cleanup completed")

                self.instance.cleanup()
        except Exception as e:
            print(f"Warning: Final cleanup failed: {e}")

        if self.config.enable_logging:
            cleanup_logging()
        print("Instance and logging cleaned up")

    def load_and_prepare_events(self) -> List[Dict]:
        """Load events from file and prepare them for processing."""
        events = load_events(self.config.events_file_path)
        events.sort(key=lambda x: x.get("tick", 0))

        batch_actions = []
        for event in events:
            tick = event.get("tick", 0)
            call = event.get("call", "")

            try:
                func_name, args = parse_function_call(call)
                batch_actions.append(
                    {"tick": tick, "func_name": func_name, "args": args}
                )
            except Exception as e:
                print(f"Warning: Failed to parse event {call}: {e}")

        return batch_actions

    def submit_batch_to_server(
        self, batch: List[Dict], start_tick: int
    ) -> Tuple[List[Dict], float]:
        """Submit a batch of actions to the server and handle results."""
        namespace = self.instance.namespace
        print(f"Processing batch of {len(batch)} actions starting at tick {start_tick}")

        # Prepare batch
        batch_info = []
        tool_execution_start = time.time()

        # Add periodic logging commands
        min_tick = batch[0]["tick"] if batch else start_tick
        max_tick = max(action["tick"] for action in batch) if batch else start_tick
        periodic_commands = self.periodic_logger.add_periodic_commands(
            batch_info, namespace, min_tick, max_tick
        )

        # Process regular batch actions
        for i, action in enumerate(batch):
            tick = action["tick"]
            func_name = action["func_name"]
            args = action["args"]

            try:
                result = ActionConverter.execute_tool_call_in_batch(
                    namespace, func_name, args, tick
                )
                command_index = len(batch_info)
                batch_info.append(
                    {
                        "index": command_index,
                        "func_name": func_name,
                        "tick": tick,
                        "args": args,
                        "batch_result": result,
                        "is_periodic": False,
                    }
                )
            except Exception as e:
                print(f"Error adding {func_name} to batch: {e}")
                command_index = len(batch_info)
                batch_info.append(
                    {
                        "index": command_index,
                        "func_name": func_name,
                        "tick": tick,
                        "args": args,
                        "error": str(e),
                        "is_periodic": False,
                    }
                )

        tool_execution_time = time.time() - tool_execution_start

        # Submit and stream results
        print(
            f"Submitting batch of {len(batch)} actions + periodic logging commands..."
        )
        submission_start_time = time.time()
        results = []
        result_count = 0

        for result in self.instance.batch_manager.submit_batch_and_stream(
            timeout_seconds=600, poll_interval=0.1
        ):
            # Measure time to first result if this is the first one
            if result_count == 0:
                first_result_time = time.time() - submission_start_time
                print(f"    First result received after {first_result_time:.3f}s")

            result_count += 1
            command_index = result["command_index"]

            # Handle periodic logging
            if command_index in periodic_commands:
                if result.get("success") and result.get("result"):
                    executed_tick = result["tick"]
                    success = self.periodic_logger.log_result(
                        executed_tick, result["result"]
                    )
                    if success:
                        print(f"    📊 Periodic data logged at tick {executed_tick}")
                continue

            # Handle regular commands
            executed_tick = result["tick"]
            planned_tick = result.get(
                "planned_tick", "?"
            )  # Get from Lua results instead of lookup
            success = result["success"]

            tick_info = (
                f"tick {executed_tick} (planned {planned_tick}) ⚠️"
                if planned_tick != "?" and executed_tick != planned_tick
                else f"tick {executed_tick}"
            )

            status = "✓" if success else "❌"
            print(f"  {status} {result['command']} at {tick_info}")
            if not success:
                print(f"    Error: {result['result']}")

            results.append(result)

        return results, tool_execution_time


class SequentialProcessor(BatchProcessor):
    """Sequential batch processing implementation."""

    def execute(self):
        """Execute events using sequential batch processing."""
        try:
            events = self.load_and_prepare_events()
            if not events:
                print("No events to process")
                return

            print(
                f"Starting sequential batch execution with tick interval batch size {self.config.batch_size}"
            )
            print(f"Total events to process: {len(events)}")

            min_tick = events[0]["tick"]
            max_tick = events[-1]["tick"]
            print(f"Event tick range: {min_tick} to {max_tick}")

            total_results = []
            batch_num = 0
            current_tick_start = (
                min_tick // self.config.batch_size
            ) * self.config.batch_size

            while current_tick_start <= max_tick:
                current_tick_end = current_tick_start + self.config.batch_size
                batch_num += 1

                batch_events = [
                    event
                    for event in events
                    if current_tick_start <= event["tick"] < current_tick_end
                ]

                if not batch_events:
                    print(
                        f"\n\033[96m=== Batch {batch_num} (ticks {current_tick_start}-{current_tick_end - 1}): No events ===\033[0m"
                    )
                    current_tick_start = current_tick_end
                    continue

                print(
                    f"\n\033[96m=== Batch {batch_num} (ticks {current_tick_start}-{current_tick_end - 1}): {len(batch_events)} events ===\033[0m"
                )

                # Show tick distribution in this batch
                batch_ticks = [event["tick"] for event in batch_events]
                print(
                    f"\033[36m    Tick range in batch: {min(batch_ticks)} to {max(batch_ticks)}\033[0m"
                )

                # Process batch
                self.instance.batch_manager.activate()
                batch_results, tool_time = self.submit_batch_to_server(
                    batch_events, batch_events[0]["tick"]
                )
                self.instance.batch_manager.deactivate()

                total_results.extend(batch_results)

                # Display tool execution timing
                avg_time_per_action = (
                    tool_time / len(batch_events) if batch_events else 0
                )
                print(
                    f"    Actions processed in {tool_time:.3f}s (avg {avg_time_per_action * 1000:.2f}ms per action)"
                )

                # Periodic memory cleanup
                if batch_num % 10 == 0:
                    try:
                        print(
                            f"    🧹 Performing periodic server memory cleanup (batch {batch_num})"
                        )
                        self.instance.begin_transaction()
                        self.instance.add_command(
                            "/sc global.actions.clear_batch_results()", raw=True
                        )
                        self.instance.execute_transaction()
                    except Exception as e:
                        print(f"Warning: Failed to perform server memory cleanup: {e}")

                current_tick_start = current_tick_end

            # Print final statistics
            successful_results = sum(
                1 for r in total_results if r.get("success", False)
            )
            failed_results = len(total_results) - successful_results
            print(
                f"\nCompleted batch execution of {len(events)} events across {batch_num} tick interval batches"
            )
            print(f"Total results collected: {len(total_results)}")
            print(f"Successful commands: {successful_results}")
            print(f"Failed commands: {failed_results}")

            if self.config.enable_periodic_logging and self.periodic_logger.enabled:
                print(f"Periodic data logged to: {self.periodic_logger.log_file_path}")

        except KeyboardInterrupt:
            print("\n🛑 Execution interrupted by user - cleaning up queued actions...")
            self._emergency_cleanup()
        except Exception as e:
            print(f"Error during batch execution: {e}")
            self._emergency_cleanup()
            raise

    def _emergency_cleanup(self):
        """Emergency cleanup for interrupts."""
        try:
            print("   Clearing queued actions from server...")
            for manager in self.instance.batch_managers:
                print(f"   Processing manager {manager.manager_id}...")
                cleanup_results = manager.emergency_cleanup()

                # Report results
                for operation, result in cleanup_results.items():
                    if result == "success":
                        print(f"      ✅ {operation}")
                    else:
                        print(f"      ❌ {operation}: {result}")

            print("   ✅ Server cleanup completed")
        except Exception as e:
            print(f"   ⚠️ Warning: Failed to clear queued actions: {e}")

        try:
            self.instance.batch_manager.deactivate()
        except:
            pass


class PipelineProcessor(BatchProcessor):
    """Pipeline batch processing implementation."""

    def __init__(self, config: ProcessingConfig):
        super().__init__(config)
        self.completed_batches = []
        self.batch_stats = {}
        self.start_time = None

    def execute(self):
        """Execute events using pipeline batch processing."""
        try:
            events = self.load_and_prepare_events()
            if not events:
                print("No events to process")
                return

            print(
                f"Starting pipeline execution with tick interval batch size {self.config.batch_size}"
            )
            print(f"Max concurrent batches: {self.config.max_concurrent_batches}")
            print(f"Total events to process: {len(events)}")

            min_tick = events[0]["tick"]
            max_tick = events[-1]["tick"]
            print(f"Event tick range: {min_tick} to {max_tick}")

            self.start_time = time.time()

            # Process batches sequentially for simplicity but with pipeline organization
            batch_count = 0
            current_tick_start = (
                min_tick // self.config.batch_size
            ) * self.config.batch_size
            all_results = []

            while current_tick_start <= max_tick:
                current_tick_end = current_tick_start + self.config.batch_size

                batch_events = [
                    event
                    for event in events
                    if current_tick_start <= event["tick"] < current_tick_end
                ]

                if batch_events:
                    tick_range = f"(ticks {current_tick_start}-{current_tick_end - 1})"
                    print(
                        f"\n📦 Processing batch {batch_count} {tick_range}: {len(batch_events)} events"
                    )

                    # Process this batch
                    batch_start_time = time.time()
                    self.instance.batch_manager.activate()
                    batch_results, tool_time = self.submit_batch_to_server(
                        batch_events, batch_events[0]["tick"]
                    )
                    self.instance.batch_manager.deactivate()

                    batch_duration = time.time() - batch_start_time

                    # Store batch statistics
                    self.batch_stats[batch_count] = {
                        "start_time": batch_start_time,
                        "duration": batch_duration,
                        "command_count": len(batch_events),
                        "result_count": len(batch_results),
                        "tick_range": tick_range,
                        "tool_execution_time": tool_time,
                    }

                    all_results.extend(batch_results)
                    batch_count += 1

                    # Display timing info
                    avg_time_per_action = (
                        tool_time / len(batch_events) if batch_events else 0
                    )
                    print(
                        f"    ✅ Completed in {batch_duration:.2f}s, tool time: {tool_time:.3f}s (avg {avg_time_per_action * 1000:.2f}ms per action)"
                    )

                    # Periodic memory cleanup for pipeline mode
                    if batch_count % 20 == 0:  # Every 20 batches for pipeline mode
                        try:
                            print(
                                f"    🧹 Performing periodic server memory cleanup (batch {batch_count})"
                            )
                            self.instance.begin_transaction()
                            self.instance.add_command(
                                "/sc global.actions.clear_batch_results()", raw=True
                            )
                            self.instance.execute_transaction()
                        except Exception as e:
                            print(
                                f"Warning: Failed to perform server memory cleanup: {e}"
                            )

                current_tick_start = current_tick_end

            print(f"\n📦 All {batch_count} batches completed")

            # Calculate and print final statistics
            total_time = time.time() - self.start_time
            total_results = len(all_results)
            successful_results = sum(1 for r in all_results if r.get("success", False))
            failed_results = total_results - successful_results

            print("\n📊 Final Statistics:")
            print(f"   Total events processed: {len(events)}")
            print(f"   Total batches: {batch_count}")
            print(f"   Total commands: {total_results}")
            print(f"   Successful commands: {successful_results}")
            print(f"   Failed commands: {failed_results}")
            print(f"   Total time: {total_time:.2f}s")

            if total_time > 0:
                print(f"   Commands per second: {total_results / total_time:.1f}")

            # Print detailed timing analysis
            self.print_timing_summary()

            if self.config.enable_periodic_logging and self.periodic_logger.enabled:
                print(f"Periodic data logged to: {self.periodic_logger.log_file_path}")

        except KeyboardInterrupt:
            print("\n🛑 Execution interrupted by user - cleaning up queued actions...")
            self._emergency_cleanup()
        except Exception as e:
            print(f"Error during pipeline execution: {e}")
            self._emergency_cleanup()
            raise

    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics."""
        if not self.start_time:
            return {}

        elapsed = time.time() - self.start_time
        total_commands = sum(
            stats["result_count"] for stats in self.batch_stats.values()
        )

        return {
            "total_batches_completed": len(self.batch_stats),
            "total_commands_processed": total_commands,
            "elapsed_time": elapsed,
            "commands_per_second": total_commands / elapsed if elapsed > 0 else 0,
            "batch_stats": self.batch_stats.copy(),
        }

    def get_all_results(self) -> Dict[int, List[Dict]]:
        """Get all results organized by batch_id."""
        # For this simplified version, return empty dict as results are handled inline
        return {}

    def print_timing_summary(self):
        """Print detailed timing analysis for bottleneck identification."""
        if not self.batch_stats:
            print("No timing data available")
            return

        print("\n" + "=" * 60)
        print("📊 PIPELINE PROCESSING TIMING ANALYSIS")
        print("=" * 60)

        durations = [stats["duration"] for stats in self.batch_stats.values()]
        tool_times = [
            stats["tool_execution_time"] for stats in self.batch_stats.values()
        ]
        command_counts = [stats["command_count"] for stats in self.batch_stats.values()]

        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)
        avg_tool_time = sum(tool_times) / len(tool_times)
        max_tool_time = max(tool_times)
        avg_commands = sum(command_counts) / len(command_counts)

        print(f"Batches Processed: {len(self.batch_stats)}")
        print()
        print("⏱️  TIMING BREAKDOWN:")
        print(
            f"  Batch Duration:        avg={avg_duration:.3f}s  max={max_duration:.3f}s"
        )
        print(
            f"  Tool Execution Time:   avg={avg_tool_time:.3f}s  max={max_tool_time:.3f}s"
        )
        print(f"  Commands per Batch:    avg={avg_commands:.1f}")

        if avg_commands > 0:
            avg_time_per_command = avg_tool_time / avg_commands
            print(f"  Time per Command:      avg={avg_time_per_command * 1000:.2f}ms")

        print()
        print("🔍 PERFORMANCE ANALYSIS:")
        if avg_duration > 5.0:
            print("  • High batch duration - consider smaller batch sizes")
        if avg_tool_time / avg_duration > 0.8:
            print(
                "  • Tool execution is majority of time - well optimized server communication"
            )
        else:
            print(
                "  • Significant overhead beyond tool execution - check server responsiveness"
            )

        print("=" * 60)

    def _emergency_cleanup(self):
        """Emergency cleanup for interrupts."""
        try:
            print("   Clearing queued actions from server...")
            for manager in self.instance.batch_managers:
                print(f"   Processing manager {manager.manager_id}...")
                cleanup_results = manager.emergency_cleanup()

                # Report results
                for operation, result in cleanup_results.items():
                    if result == "success":
                        print(f"      ✅ {operation}")
                    else:
                        print(f"      ❌ {operation}: {result}")

            print("   ✅ Server cleanup completed")
        except Exception as e:
            print(f"   ⚠️ Warning: Failed to clear queued actions: {e}")
