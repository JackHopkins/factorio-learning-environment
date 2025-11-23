import argparse
import sys
import shutil
import subprocess
from pathlib import Path
import importlib.resources
import asyncio
from fle.env.gym_env.run_eval import main as run_eval
from fle.agents.data.sprites.download import download_sprites_from_hf, generate_sprites


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


def fle_inspect_eval(args):
    """New command: fle inspect-eval using Inspect framework"""
    view_process = None

    try:
        # Start inspect view first if requested (in background)
        if args.view:
            print(f"🔍 Starting Inspect view on port {args.view_port}...")
            view_cmd = ["inspect", "view", "--port", str(args.view_port)]
            if args.log_dir:
                view_cmd.extend(["--log-dir", args.log_dir])
            else:
                view_cmd.extend(["--log-dir", ".fle/inspect_logs"])

            print(f"View command: {' '.join(view_cmd)}")
            print(f"📊 View will be available at: http://localhost:{args.view_port}")

            # Start view in background
            view_process = subprocess.Popen(
                view_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

            import time

            time.sleep(2)  # Give view server time to start
            print("🌐 Inspect view server started in background")

        # Build evaluation command
        if args.eval_set:
            # Use eval-set for multiple tasks
            cmd = [
                "inspect",
                "eval-set",
                "eval/inspect_integration/factorio_eval_set.py",
                #  "-M \"transforms=['middle-out']\""
            ]
        else:
            # Use the working controlled solver via agent_task.py
            cmd = [
                "inspect",
                "eval",
                "eval/inspect_integration/agent_task.py@factorio_agent_evaluation",
                # "-M \"transforms=['middle-out']\""
            ]

        # Add optional arguments with custom log subdir for eval-sets
        if args.log_dir:
            cmd.extend(["--log-dir", args.log_dir])
        else:
            # Create timestamped subdirectory for eval-sets to avoid conflicts
            if args.eval_set:
                import datetime

                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                log_dir = f".fle/inspect_logs/evalset_{timestamp}"
            else:
                log_dir = ".fle/inspect_logs"
            cmd.extend(["--log-dir", log_dir])

        if args.max_connections:
            cmd.extend(["--max-connections", str(args.max_connections)])
        else:
            cmd.extend(["--max-connections", "8"])

        # Configure max-tasks for eval-set mode
        if args.eval_set:
            if hasattr(args, "max_tasks") and args.max_tasks:
                cmd.extend(["--max-tasks", str(args.max_tasks)])
            else:
                # Default max-tasks to match max-connections (number of available servers)
                max_tasks = args.max_connections if args.max_connections else 8
                cmd.extend(["--max-tasks", str(max_tasks)])

        if args.cache:
            cmd.extend(["--cache", "true"])

        if hasattr(args, "limit") and args.limit:
            cmd.extend(["--limit", str(args.limit)])

        if args.model:
            cmd.extend(["--model", args.model])
        else:
            # Default to a working model for testing
            cmd.extend(["--model", "openai/gpt-4o-mini"])

        # Add reasoning configuration for reasoning models
        if hasattr(args, "reasoning_effort") and args.reasoning_effort:
            cmd.extend(["--reasoning-effort", args.reasoning_effort])

        if hasattr(args, "reasoning_tokens") and args.reasoning_tokens:
            cmd.extend(["--reasoning-tokens", str(args.reasoning_tokens)])

        # Add Pass@N configuration
        if hasattr(args, "epochs") and args.epochs:
            cmd.extend(["--epochs", str(args.epochs)])
        elif hasattr(args, "pass_n") and args.pass_n:
            # Default: use pass_n as epochs for Pass@N evaluation
            cmd.extend(["--epochs", str(args.pass_n)])
            cmd.extend(["--epochs-reducer", f"pass_at_{args.pass_n}"])

        if hasattr(args, "epochs_reducer") and args.epochs_reducer:
            cmd.extend(["--epochs-reducer", args.epochs_reducer])

        cmd.extend(["-M", "transforms=['middle-out']"])
        # Set environment variables for dynamic task configuration
        import os

        if args.env_id:
            os.environ["FLE_ENV_ID"] = args.env_id
            print(f"🎯 Targeting specific task: {args.env_id}")

        if args.model:
            os.environ["FLE_MODEL"] = args.model

        if hasattr(args, "limit") and args.limit:
            os.environ["FLE_LIMIT"] = str(args.limit)

        # Set trajectory length from CLI argument
        if hasattr(args, "trajectory_length") and args.trajectory_length:
            os.environ["FLE_TRAJECTORY_LENGTH"] = str(args.trajectory_length)
        else:
            os.environ["FLE_TRAJECTORY_LENGTH"] = "64"  # Ensure default is 64

        # Check if Factorio servers are reachable before starting evaluation
        print("🔍 Checking Factorio server availability...")
        import socket

        def check_port(host, port, timeout=2):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                result = sock.connect_ex((host, port))
                sock.close()
                return result == 0
            except Exception:
                return False

        # Check first few Factorio server ports
        reachable_servers = []
        for i in range(32):  # Check first 32 servers
            port = 27000 + i
            if check_port("localhost", port, timeout=1):
                reachable_servers.append(f"factorio_{i}")

        if reachable_servers:
            print(
                f"✅ Found {len(reachable_servers)} reachable Factorio servers: {reachable_servers}"
            )
        else:
            print(
                "⚠️  No Factorio servers reachable. Starting evaluation anyway (will use mock mode)"
            )
            print(
                "💡 To use real Factorio: run 'fle cluster start -n 8' and wait 30-60 seconds"
            )

        if args.config:
            print(
                f"Note: Config {args.config} provided but using default dataset generation"
            )

        print(f"\n🚀 Running evaluation: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True)
        print(result)

        if args.view:
            print(
                f"\n✅ Evaluation complete! View available at: http://localhost:{args.view_port}"
            )
            print("🌐 Press Ctrl+C to stop the view server when done")
            # Keep view running - wait for user to stop it
            try:
                view_process.wait()
            except KeyboardInterrupt:
                print("\n👋 Stopping view server...")
                view_process.terminate()
                view_process.wait()

    except subprocess.CalledProcessError as e:
        print(
            f"Inspect evaluation failed with return code {e.returncode}",
            file=sys.stderr,
        )
        sys.exit(e.returncode)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        # Clean up view process if it was started
        if view_process and view_process.poll() is None:
            print("🧹 Cleaning up view server...")
            view_process.terminate()
            try:
                view_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                view_process.kill()


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
    parser = argparse.ArgumentParser(
        prog="fle",
        description="Factorio Learning Environment CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  fle eval --config configs/gym_run_config.json
  fle inspect-eval [--config CONFIG] [--cache] [--max-connections N]
  fle cluster [start|stop|restart|help] [-n N] [-s SCENARIO]
  fle sprites [--force] [--workers N]
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

    parser_inspect = subparsers.add_parser(
        "inspect-eval", help="Run evaluation using Inspect framework"
    )
    parser_inspect.add_argument(
        "--config", help="Path to run config JSON (optional, uses all tasks by default)"
    )
    parser_inspect.add_argument(
        "--log-dir", help="Directory for Inspect logs (default: .fle/inspect_logs)"
    )
    parser_inspect.add_argument(
        "--max-connections", type=int, help="Max parallel connections (default: 8)"
    )
    parser_inspect.add_argument(
        "--max-tasks",
        type=int,
        help="Max parallel tasks for eval-set (default: matches max-connections)",
    )
    parser_inspect.add_argument("--cache", action="store_true", help="Enable caching")
    parser_inspect.add_argument(
        "--limit", type=int, help="Limit number of samples to run"
    )
    parser_inspect.add_argument(
        "--view", action="store_true", help="Launch inspect view after evaluation"
    )
    parser_inspect.add_argument(
        "--view-port",
        type=int,
        default=8000,
        help="Port for inspect view (default: 8000)",
    )
    parser_inspect.add_argument(
        "--model", help="Model to use for evaluation (e.g., openai/gpt-4o-mini)"
    )
    parser_inspect.add_argument(
        "--env-id", help="Specific environment/task to evaluate (default: all tasks)"
    )
    parser_inspect.add_argument(
        "--trajectory-length",
        type=int,
        default=64,
        help="Number of trajectory steps (default: 64)",
    )
    parser_inspect.add_argument(
        "--reasoning-effort",
        choices=["low", "medium", "high"],
        help="Reasoning effort for reasoning models",
    )
    parser_inspect.add_argument(
        "--reasoning-tokens",
        type=int,
        help="Maximum reasoning tokens for reasoning models",
    )
    parser_inspect.add_argument(
        "--eval-set",
        action="store_true",
        help="Run multiple Factorio tasks as an evaluation set",
    )
    parser_inspect.add_argument(
        "--pass-n",
        type=int,
        default=8,
        help="Number of attempts for Pass@N evaluation (default: 8)",
    )
    parser_inspect.add_argument(
        "--epochs", type=int, help="Number of epochs to run each sample (for Pass@N)"
    )
    parser_inspect.add_argument(
        "--epochs-reducer", help="Epochs reducer (e.g., pass_at_1, pass_at_8)"
    )

    parser_sprites = subparsers.add_parser(
        "sprites", help="Download and generate sprites"
    )
    parser_sprites.add_argument(
        "--force", action="store_true", help="Force re-download even if sprites exist"
    )
    parser_sprites.add_argument(
        "--workers",
        type=int,
        default=10,
        help="Number of parallel download workers (default: 10)",
    )
    parser_sprites.add_argument(
        "--spritemap-dir",
        type=str,
        default=".fle/spritemaps",
        help="Directory to save downloaded spritemaps (default: .fle/spritemaps)",
    )
    parser_sprites.add_argument(
        "--sprite-dir",
        type=str,
        default=".fle/sprites",
        help="Directory to save generated sprites (default: .fle/sprites)",
    )
    args = parser.parse_args()
    if args.command:
        fle_init()
    if args.command == "cluster":
        fle_cluster(args)
    elif args.command == "eval":
        fle_eval(args)
    elif args.command == "inspect-eval":
        fle_inspect_eval(args)
    elif args.command == "sprites":
        fle_sprites(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
