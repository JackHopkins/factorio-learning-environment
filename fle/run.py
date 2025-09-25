import argparse
import sys
import shutil
from pathlib import Path
import importlib.resources
import asyncio
from fle.env.gym_env.run_eval import main as run_eval


def fle_init():
    if Path(".env").exists():
        return
    try:
        pkg = importlib.resources.files("fle")
        env_path = pkg / ".example.env"
        shutil.copy(str(env_path), ".env")
        print("Created .env file - please edit with your API keys and DB config")
    except Exception as e:
        print(f"Error during init: {e}", file=sys.stderr)
        sys.exit(1)


def fle_eval(args):
    try:
        config_path = str(Path(args.config))
        asyncio.run(run_eval(config_path))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        prog="fle",
        description="Factorio Learning Environment CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  fle eval --config configs/gym_run_config.json
        """,
    )
    subparsers = parser.add_subparsers(dest="command")
    parser_eval = subparsers.add_parser("eval", help="Run experiment")
    parser_eval.add_argument("--config", required=True, help="Path to run config JSON")
    args = parser.parse_args()
    if args.command:
        fle_init()
    elif args.command == "eval":
        fle_eval(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
