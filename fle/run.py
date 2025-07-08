#!/usr/bin/env python3
import argparse
import asyncio
import sys
import shutil
import subprocess
from pathlib import Path
import importlib.resources
from fle.env.gym_env.run_eval import main as run_eval


def copy_env_and_configs():
    # Copy .example.env to .env if not exists
    try:
        with importlib.resources.files("fle") as pkg:
            env_template = pkg / ".example.env"
            if not Path(".env").exists():
                shutil.copy(env_template, ".env")
                print(
                    "Created .env file - please edit with your API keys and DB config"
                )
            else:
                print(".env already exists, skipping copy.")
            # Copy example run configs
            run_configs_dir = pkg / "eval" / "algorithms" / "independent"
            configs_out = Path("configs")
            configs_out.mkdir(exist_ok=True)
            for config in run_configs_dir.glob("run_config_example_*.json"):
                shutil.copy(config, configs_out / config.name)
            print("Copied example run configs to ./configs/")
    except Exception as e:
        print(f"Error during init: {e}", file=sys.stderr)
        sys.exit(1)


def run_cluster():
    script = Path(__file__).parent / "cluster" / "local" / "run-envs.sh"
    if not script.exists():
        print(f"Cluster script not found: {script}", file=sys.stderr)
        sys.exit(1)
    try:
        subprocess.run([str(script)], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running cluster script: {e}", file=sys.stderr)
        sys.exit(e.returncode)


def main():
    parser = argparse.ArgumentParser(
        prog="fle",
        description="Factorio Learning Environment - Run AI agents in Factorio",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  fle --run_config eval/open/independent_runs/run_config_example_lab_play.json
  fle init
  fle cluster
        """,
    )
    subparsers = parser.add_subparsers(dest="command")

    # init subcommand
    subparsers.add_parser("init", help="Initialize FLE workspace (copy .env, configs)")

    # cluster subcommand
    subparsers.add_parser("cluster", help="Setup Docker containers (run run-envs.sh)")

    # Default run (no subcommand)
    parser.add_argument(
        "--run_config",
        type=str,
        help="Path to the run configuration JSON file",
        required=False,
    )

    args = parser.parse_args()

    if args.command == "init":
        copy_env_and_configs()
        return
    elif args.command == "cluster":
        run_cluster()
        return
    elif args.run_config:
        # Validate that the config file exists
        config_path = Path(args.run_config)
        if not config_path.exists():
            print(
                f"Error: Configuration file '{args.run_config}' not found.",
                file=sys.stderr,
            )
            sys.exit(1)
        # Set up arguments for run_eval and call it
        original_argv = sys.argv.copy()
        try:
            sys.argv = ["run_eval", "--run_config", str(config_path)]
            asyncio.run(run_eval())
        except KeyboardInterrupt:
            print("\nInterrupted by user.", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        finally:
            sys.argv = original_argv
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
