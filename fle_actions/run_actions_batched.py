"""
Refactored Factorio batch action processor with clean class architecture.

Main entry point that uses the processor classes defined in separate modules.
"""

from pathlib import Path

from processors import SequentialProcessor, PipelineProcessor
from processing_config import ProcessingConfig


def main():
    """Main entry point with argument parsing."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Execute Factorio events using batch processing"
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
        "--batch-size",
        type=int,
        default=500,
        help="Tick interval for batching events (default: 500)",
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=1,
        help="Maximum number of concurrent batch preparation threads",
    )
    parser.add_argument(
        "--pipeline",
        action="store_true",
        help="Use non-blocking pipeline processing instead of sequential batches",
    )
    parser.add_argument(
        "--periodic-log-interval",
        type=int,
        default=0,
        help="Tick interval for periodic logging (default: 0, disabled)",
    )

    args = parser.parse_args()

    if args.analyze_logs:
        from log_analyzer import analyze_logs_example

        analyze_logs_example()
        return

    # Determine events file
    current_dir = Path(__file__).parent
    events_file = (
        current_dir / "_runnable_actions" / f"combined_events_py_{args.max_time}.jsonl"
    )

    if not events_file.exists():
        print(f"Events file not found: {events_file}")
        print("Please provide the path to your events JSONL file")
        return

    # Create configuration
    config = ProcessingConfig(
        events_file_path=str(events_file),
        enable_logging=args.enable_logging,
        speed=args.speed,
        batch_size=args.batch_size,
        max_concurrent_batches=args.max_concurrent,
        periodic_log_interval=args.periodic_log_interval,
    )

    # Create and run processor
    if args.pipeline:
        processor = PipelineProcessor(config)
        print("🚀 Using pipeline batch processing (non-blocking)")
    else:
        processor = SequentialProcessor(config)
        print("📦 Using sequential batch processing (blocking)")

    processor.setup()
    try:
        processor.execute()
    finally:
        processor.cleanup()


if __name__ == "__main__":
    main()
