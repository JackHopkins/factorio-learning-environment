#!/usr/bin/env python3
import argparse
import asyncio
import sys
from pathlib import Path
from fle.env.gym_env.run_eval import main as run_eval
from fle.logger import error


def main():
    """Main entry point for the fle command."""
    parser = argparse.ArgumentParser(
        prog='fle',
        description='Factorio Learning Environment - Run AI agents in Factorio',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  fle --run_config eval/open/independent_runs/run_config_example_lab_play.json

For more information, visit: https://github.com/JackHopkins/PaperclipMaximiser
        """
    )
    
    parser.add_argument(
        '--run_config',
        type=str,
        help='Path to the run configuration JSON file',
        required=True
    )
    
    args = parser.parse_args()
    
    # Validate that the config file exists
    config_path = Path(args.run_config)
    if not config_path.exists():
        error(f"Configuration file '{args.run_config}' not found.")
        sys.exit(1)
    
    # Set up arguments for run_eval and call it
    original_argv = sys.argv.copy()
    try:
        asyncio.run(run_eval(config_path))
    except KeyboardInterrupt:
        error("Interrupted by user.")
        sys.exit(1)
    except Exception as e:
        error(f"Error: {e}")
        sys.exit(1)
    finally:
        sys.argv = original_argv


if __name__ == "__main__":
    main()