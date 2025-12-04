import argparse
import sys
import shutil
from pathlib import Path
import importlib.resources
import asyncio

# Ensure slpp warnings are suppressed for all users before any imports
import warnings

warnings.filterwarnings("ignore", category=SyntaxWarning, module="slpp")

from fle.cluster.run_envs import (
    start_cluster,
    stop_cluster,
    restart_cluster,
    ClusterManager,
)
from fle.agents.data.sprites.download import download_sprites_from_hf, generate_sprites


def fle_init():
    """Initialize FLE environment by creating .env file and configs directory if they don't exist."""
    created_files = []

    # Create .env file if it doesn't exist
    if not Path(".env").exists():
        try:
            pkg = importlib.resources.files("fle")
            env_path = pkg / ".example.env"
            shutil.copy(str(env_path), ".env")
            created_files.append(".env file")
        except Exception as e:
            print(f"Error creating .env file: {e}", file=sys.stderr)
            sys.exit(1)

    # Create configs directory and copy default config if it doesn't exist
    configs_dir = Path("configs")
    if not configs_dir.exists():
        try:
            configs_dir.mkdir(exist_ok=True)
            pkg = importlib.resources.files("fle")
            config_path = pkg / "eval" / "configs" / "gym_run_config.json"
            shutil.copy(str(config_path), configs_dir / "gym_run_config.json")
            created_files.append("configs/ directory with gym_run_config.json")
        except Exception as e:
            print(f"Error creating configs directory: {e}", file=sys.stderr)
            sys.exit(1)

    if created_files:
        print(
            f"Created {', '.join(created_files)} - please edit .env with your API keys and DB config"
        )


def fle_eval(args):
    """Run evaluation/experiments with the given config."""
    try:
        # Import run_eval only when needed (requires eval dependencies)
        from fle.eval.entrypoints.gym_eval import main as run_eval

        config_path = str(Path(args.config))
        asyncio.run(run_eval(config_path))
    except ImportError as e:
        print(
            "Error: Evaluation functionality requires additional dependencies.",
            file=sys.stderr,
        )
        print(
            "Install with: pip install factorio-learning-environment[eval]",
            file=sys.stderr,
        )
        print(f"Original error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def fle_cluster(args):
    """Handle cluster management commands."""
    if args.cluster_command == "start":
        if not (1 <= args.number <= 33):
            print("Error: number of instances must be between 1 and 33.")
            sys.exit(1)
        # Validate save file if provided
        if args.use_save and not Path(args.use_save).exists():
            print(f"Error: Save file '{args.use_save}' does not exist.")
            sys.exit(1)

        start_cluster(args.number, args.scenario, args.attach_mods, args.use_save)

    elif args.cluster_command == "stop":
        stop_cluster()

    elif args.cluster_command == "restart":
        restart_cluster()

    elif args.cluster_command == "logs":
        manager = ClusterManager()
        manager.logs(getattr(args, "service", "factorio_0"))

    elif args.cluster_command == "show":
        manager = ClusterManager()
        manager.show()

    else:
        print(f"Error: Unknown cluster command '{args.cluster_command}'")


def fle_sprites(args):
    try:
        # Download spritemaps from HuggingFace
        print("Downloading spritemaps...")
        success = download_sprites_from_hf(
            output_dir=args.spritemap_dir, force=args.force, num_workers=args.workers
        )

        if not success:
            print("Failed to download spritemaps", file=sys.stderr)
            sys.exit(1)

        # Generate individual sprites from spritemaps
        print("\nGenerating sprites...")
        success = generate_sprites(
            input_dir=args.spritemap_dir, output_dir=args.sprite_dir
        )

        if not success:
            print("Failed to generate sprites", file=sys.stderr)
            sys.exit(1)

        print("\nSprites successfully downloaded and generated!")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main CLI entry point for FLE."""
    parser = argparse.ArgumentParser(
        prog="fle",
        description="Factorio Learning Environment CLI - Manage clusters and run experiments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  fle init                                   # Initialize environment
  fle cluster start                          # Start 1 Factorio instance
  fle cluster start -n 4                     # Start 4 instances  
  fle cluster start -s open_world            # Start with open world scenario
  fle cluster stop                           # Stop all instances
  fle cluster show                           # Show running services
  fle cluster logs factorio_0                # View logs for specific service
  fle cluster restart                        # Restart current cluster
  fle eval --config configs/run_config.json  # Run experiment
  fle eval --config configs/gym_run_config.json
  fle cluster [start|stop|restart|help] [-n N] [-s SCENARIO]
  fle sprites [--force] [--workers N]

Tips:
  Use 'fle <command> -h' for command-specific help
  Use 'fle cluster <subcommand> -h' for cluster subcommand help
        """,
    )

    # Add subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Init command
    subparsers.add_parser("init", help="Initialize FLE environment (.env file)")

    # Cluster management subcommand
    cluster_parser = subparsers.add_parser(
        "cluster",
        help="Manage Factorio server clusters",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  fle cluster start                    # Start 1 instance (default scenario)
  fle cluster start -n 4               # Start 4 instances
  fle cluster start -s open_world      # Start with open world scenario
  fle cluster start -sv save.zip       # Start from a save file
  fle cluster start -m                 # Start with mods attached
  fle cluster stop                     # Stop all running instances
  fle cluster restart                  # Restart current cluster
  fle cluster show                     # Show running services and ports
  fle cluster logs factorio_0          # Show logs for specific service
        """,
    )

    cluster_subparsers = cluster_parser.add_subparsers(
        dest="cluster_command", help="Cluster management commands"
    )

    # Cluster start command
    start_parser = cluster_subparsers.add_parser(
        "start", help="Start Factorio instances"
    )
    start_parser.add_argument(
        "-n",
        "--number",
        type=int,
        default=1,
        help="Number of Factorio instances to run (1-33, default: 1)",
    )
    start_parser.add_argument(
        "-s",
        "--scenario",
        choices=["open_world", "default_lab_scenario", "MetaCALM"],
        default="default_lab_scenario",
        help="Scenario to run (default: default_lab_scenario)",
    )
    start_parser.add_argument(
        "-sv", "--use_save", type=str, help="Use a .zip save file from Factorio"
    )
    start_parser.add_argument(
        "-m", "--attach_mods", action="store_true", help="Attach mods to the instances"
    )

    # Cluster stop command
    cluster_subparsers.add_parser("stop", help="Stop all running instances")

    # Cluster restart command
    cluster_subparsers.add_parser("restart", help="Restart the current cluster")

    # Cluster logs command
    logs_parser = cluster_subparsers.add_parser("logs", help="Show service logs")
    logs_parser.add_argument(
        "service",
        nargs="?",
        default="factorio_0",
        help="Service name (default: factorio_0)",
    )

    # Cluster show command
    cluster_subparsers.add_parser(
        "show", help="Show running services and exposed ports"
    )

    # Eval command
    eval_parser = subparsers.add_parser("eval", help="Run experiments/evaluation")
    eval_parser.add_argument(
        "--config", required=True, help="Path to run config JSON file"
    )

    # Sprites command
    sprites_parser = subparsers.add_parser(
        "sprites", help="Download and generate sprites"
    )
    sprites_parser.add_argument(
        "--force", action="store_true", help="Force re-download even if sprites exist"
    )
    sprites_parser.add_argument(
        "--workers",
        type=int,
        default=10,
        help="Number of parallel download workers (default: 10)",
    )
    sprites_parser.add_argument(
        "--spritemap-dir",
        type=str,
        default=".fle/spritemaps",
        help="Directory to save downloaded spritemaps (default: .fle/spritemaps)",
    )
    sprites_parser.add_argument(
        "--sprite-dir",
        type=str,
        default=".fle/sprites",
        help="Directory to save generated sprites (default: .fle/sprites)",
    )
    args = parser.parse_args()

    # Handle commands
    if args.command == "init":
        fle_init()

    elif args.command == "cluster":
        if not args.cluster_command:
            cluster_parser.print_help()
            sys.exit(1)
        fle_cluster(args)

    elif args.command == "eval":
        fle_init()  # Ensure .env exists before running eval
        fle_eval(args)
    elif args.command == "sprites":
        fle_sprites(args)
    elif args.command is None:
        parser.print_help()
        sys.exit(1)
    else:
        print(f"Error: Unknown command '{args.command}'")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
