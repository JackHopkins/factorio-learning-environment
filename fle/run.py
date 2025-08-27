import argparse
import sys
import shutil
import subprocess
from pathlib import Path
import importlib.resources
import asyncio
from fle.env.gym_env.run_eval import main as run_eval
import signal

signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))


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


def fle_cluster(args):
    cluster_path = Path(__file__).parent / "cluster"
    script = cluster_path / "run-envs.sh"
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
        subprocess.run(cmd, cwd=str(cluster_path), check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running cluster script: {e}", file=sys.stderr)
        sys.exit(e.returncode)


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
  fle cluster [start|stop|restart|help] [-n N] [-s SCENARIO]
        """,
    )
    subparsers = parser.add_subparsers(dest="command")
    parser_cluster = subparsers.add_parser(
        "cluster", help="Setup Docker containers (run run-envs.sh)"
    )
    parser_cluster.add_argument(
        "cluster_command",
        nargs="?",
        choices=["start", "stop", "restart", "help"],
        help="Cluster command (start/stop/restart/help)",
    )
    parser_cluster.add_argument("-n", type=int, help="Number of Factorio instances")
    parser_cluster.add_argument(
        "-s",
        type=str,
        help="Scenario (open_world or default_lab_scenario)",
    )
    parser_eval = subparsers.add_parser("eval", help="Run experiment")
    parser_eval.add_argument("--config", required=True, help="Path to run config JSON")
    args = parser.parse_args()
    if args.command:
        fle_init()
    if args.command == "cluster":
        fle_cluster(args)
    elif args.command == "eval":
        fle_eval(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
