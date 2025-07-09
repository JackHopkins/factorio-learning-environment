import argparse
import sys
import shutil
import subprocess
from pathlib import Path
import importlib.resources
import asyncio
from fle.env.gym_env.run_eval import main as run_eval


def fle_init():
    if Path(".env").exists():
        return True
    try:
        pkg = importlib.resources.files("fle")
        env_template = pkg / ".example.env"
        with importlib.resources.as_file(env_template) as env_path:
            shutil.copy(env_path, ".env")
            print("Created .env file - please edit with your API keys and DB config")
        configs_out = Path("configs")
        configs_out.mkdir(exist_ok=True)
        shutil.copy(
            str(pkg / "eval" / "algorithms" / "independent" / "gym_run_config.json"),
            str(configs_out / "gym_run_config.json"),
        )
    except Exception as e:
        print(f"Error during init: {e}", file=sys.stderr)
        sys.exit(1)
    return False


def fle_cluster(args):
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


def fle_eval(args, env):
    if not env:
        return
    # Check if Factorio server is running on port 34197
    probe = Path(__file__).parent / "cluster" / "docker" / "probe.sh"
    result = subprocess.run(["sh", str(probe)])
    if result.returncode != 0:
        print("Server not running, starting cluster...")
        fle_cluster(None)
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Config file '{args.config}' not found.", file=sys.stderr)
        sys.exit(1)
    try:
        sys.argv = ["run_eval", "--run_config", str(config_path)]
        asyncio.run(run_eval())
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        sys.exit(1)
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
    parser_eval = subparsers.add_parser("eval", help="Run experiment")
    parser_eval.add_argument("--config", required=True, help="Path to run config JSON")
    args = parser.parse_args()
    env = True
    if args.command:
        env = fle_init()
    if args.command == "cluster":
        fle_cluster(args)
    elif args.command == "eval":
        fle_eval(args, env)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
