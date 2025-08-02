"""
Main entry point for running Factorio actions.
This file dispatches to either batched or unbatched execution modes.
"""

import argparse
from pathlib import Path

from run_actions_batched import execute_events_from_file_batched
from run_actions_unbatched import execute_events_from_file
from log_analyzer import analyze_logs_example


def main():
    """Main entry point that dispatches to the appropriate execution mode."""
    parser = argparse.ArgumentParser(
        description="Execute Factorio events from JSONL files"
    )
    parser.add_argument(
        "--max-time",
        type=int,
        default=10000,
        help="Maximum tick time to include in events file",
    )
    parser.add_argument(
        "--analyze-logs",
        action="store_true",
        help="Analyze existing log files instead of running simulation",
    )
    parser.add_argument(
        "--enable-logging",
        action="store_true",
        help="Enable logging of entities and inventory data to files",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Game speed multiplier (default: 1.0, higher = faster)",
    )
    parser.add_argument(
        "--diff-thread",
        action="store_true",
        help="Execute actions in separate threads instead of same thread (may cause timing issues)",
    )
    parser.add_argument(
        "--batch-mode",
        action="store_true",
        help="Use batch processing mode for better performance",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of events to process in each batch (default: 50)",
    )
    args = parser.parse_args()

    if args.analyze_logs:
        analyze_logs_example()
        return

    # Default to the combined_events_py.jsonl file in the same directory
    current_dir = Path(__file__).parent
    events_file = (
        current_dir / "_runnable_actions" / f"combined_events_py_{args.max_time}.jsonl"
    )

    if not events_file.exists():
        print(f"Events file not found: {events_file}")
        print("Please provide the path to your events JSONL file")
        return

    if args.batch_mode:
        print("Using batch processing mode")
        execute_events_from_file_batched(
            str(events_file),
            enable_logging=args.enable_logging,
            speed=args.speed,
            batch_size=args.batch_size,
        )
    else:
        print("Using traditional sequential processing mode")
        execute_events_from_file(
            str(events_file),
            enable_logging=args.enable_logging,
            speed=args.speed,
            diff_thread=args.diff_thread,
        )


if __name__ == "__main__":
    main()
