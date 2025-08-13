import argparse
import asyncio
import importlib.resources
import shutil
import subprocess
import sys
from pathlib import Path

from fle.run_eval import main as run_eval


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
    """Manage local Factorio headless servers using the Docker manager API."""
    from fle.services.docker.config import DockerConfig, Scenario, Mode
    from fle.services.docker.docker_manager import FactorioHeadlessClusterManager

    try:
        config = DockerConfig()
        # Map args to config if provided
        if args and args.s:
            if args.s == "open_world":
                config.scenario_name = Scenario.OPEN_WORLD.value
            elif args.s == "default_lab_scenario":
                config.scenario_name = Scenario.DEFAULT_LAB_SCENARIO.value
        num = args.n if args and args.n else 1
        docker_platform = "linux/arm64" if config.arch in ("arm64", "aarch64") else "linux/amd64"
        mgr = FactorioHeadlessClusterManager(config, docker_platform, num)

        async def run():
            if args and args.cluster_command == "stop":
                await mgr.stop()
            elif args and args.cluster_command == "restart":
                await mgr.restart()
            else:
                await mgr.start()
            await mgr.attach_docker_configs()
            await mgr.docker.close()

        asyncio.run(run())
    except Exception as e:
        print(f"Error managing cluster: {e}", file=sys.stderr)
        sys.exit(1)


def fle_eval(args, env):
    if not env:
        return
    # Ensure servers are started via Docker manager if not already running
    # Attempt to start 1 instance as a convenience if containers are missing
    try:
        from fle.services.docker.docker_manager import FactorioHeadlessClusterManager
        from fle.services.docker.config import DockerConfig

        async def ensure_running():
            # Instantiate inside loop to avoid 'no running event loop'
            config = DockerConfig()
            docker_platform = "linux/arm64" if config.arch in ("arm64", "aarch64") else "linux/amd64"
            mgr = FactorioHeadlessClusterManager(config, docker_platform, 1)
            # Try to get IPs; if none/invalid response, start cluster
            ips, udp_ports, tcp_ports = await mgr.get_local_container_ips()
            if not tcp_ports:
                print("Server not running, starting cluster...")
                await mgr.start()
                ips, udp_ports, tcp_ports = await mgr.get_local_container_ips()
            await mgr.attach_docker_configs()
            await mgr.docker.close()

        asyncio.run(ensure_running())
    except Exception as e:
        print(f"Warning: could not ensure cluster running automatically ({e}). Continuing...")
        raise e
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
        raise e
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
        "cluster", help="Manage Docker containers for local Factorio servers"
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
