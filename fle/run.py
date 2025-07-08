import argparse
import asyncio
import sys
import shutil
import subprocess
from pathlib import Path
import importlib.resources

from fle.env.gym_env.run_eval import main as run_eval


# Minimal ConfigManager for config loading
class ConfigManager:
    @staticmethod
    def load(config_path):
        import json

        with open(config_path, "r") as f:
            return json.load(f)


def copy_env_and_configs():
    try:
        pkg = importlib.resources.files("fle")
        env_template = pkg / ".example.env"
        with importlib.resources.as_file(env_template) as env_path:
            if not Path(".env").exists():
                shutil.copy(env_path, ".env")
                print(
                    "Created .env file - please edit with your API keys and DB config"
                )
            else:
                print(".env already exists, skipping copy.")
        run_configs_dir = pkg / "eval" / "algorithms" / "independent"
        configs_out = Path("configs")
        configs_out.mkdir(exist_ok=True)
        for config in run_configs_dir.iterdir():
            if config.name.startswith("run_config_example_") and config.name.endswith(
                ".json"
            ):
                with importlib.resources.as_file(config) as config_path:
                    shutil.copy(config_path, configs_out / config.name)
        print("Copied example run configs to ./configs/")
    except Exception as e:
        print(f"Error during init: {e}", file=sys.stderr)
        sys.exit(1)


def run_cluster(args=None):
    script = Path(__file__).parent / "cluster" / "local" / "run-envs.sh"
    if not script.exists():
        print(f"Cluster script not found: {script}", file=sys.stderr)
        sys.exit(1)
    cmd = [str(script)]
    if args:
        if args.cluster_command:
            cmd.append(args.cluster_command)
        if args.n:
            cmd.extend(["-n", str(args.n)])
        if args.s:
            cmd.extend(["-s", args.s])
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running cluster script: {e}", file=sys.stderr)
        sys.exit(e.returncode)


def eval_command(args):
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Config file '{args.config}' not found.", file=sys.stderr)
        sys.exit(1)
    # Only 'independent' supported for now
    if args.algorithm != "independent":
        print("Only --algorithm independent is supported.", file=sys.stderr)
        sys.exit(1)
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


def main():
    parser = argparse.ArgumentParser(
        prog="fle",
        description="Factorio Learning Environment CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  fle eval --algorithm independent --config configs/run_config_example_open_play.json
  fle cluster [start|stop|restart|help] [-n N] [-s SCENARIO]
  fle init
        """,
    )
    subparsers = parser.add_subparsers(dest="command")

    # init
    subparsers.add_parser("init", help="Initialize FLE workspace (copy .env, configs)")

    # cluster
    parser_cluster = subparsers.add_parser(
        "cluster", help="Setup Docker containers (run run-envs.sh)"
    )
    parser_cluster.add_argument(
        "cluster_command",
        nargs="?",
        default=None,
        choices=["start", "stop", "restart", "help"],
        help="Cluster command (start/stop/restart/help)",
    )
    parser_cluster.add_argument(
        "-n", type=int, default=None, help="Number of Factorio instances"
    )
    parser_cluster.add_argument(
        "-s",
        type=str,
        default=None,
        help="Scenario (open_world or default_lab_scenario)",
    )

    # eval
    parser_eval = subparsers.add_parser("eval", help="Run experiment")
    parser_eval.add_argument(
        "--algorithm", required=True, help="Algorithm (independent)"
    )
    parser_eval.add_argument("--config", required=True, help="Path to run config JSON")

    args = parser.parse_args()

    if args.command == "init":
        copy_env_and_configs()
        return
    elif args.command == "cluster":
        run_cluster(args)
        return
    elif args.command == "eval":
        eval_command(args)
        return
    else:
        # No args: run with default example config
        try:
            pkg = importlib.resources.files("fle")
            default_config = (
                pkg
                / "eval"
                / "algorithms"
                / "independent"
                / "run_config_example_open_play.json"
            )
            with importlib.resources.as_file(default_config) as config_path:
                sys.argv = ["run_eval", "--run_config", str(config_path)]
                asyncio.run(run_eval())
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
