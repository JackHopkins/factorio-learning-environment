#!/usr/bin/env python3
import os
import sys
import asyncio
# Add the necessary paths to sys.path
root_dir = os.path.dirname(os.path.abspath(__file__))
env_src_dir = os.path.join(root_dir, 'env', 'src')
# Add paths to sys.path if they're not already there
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
if env_src_dir not in sys.path:
    sys.path.insert(0, env_src_dir)
# Now import and run the actual script
from eval.open.independent_runs.run import main
from env.src.gym_env.run_eval import main as run_eval
if __name__ == "__main__":
    asyncio.run(run_eval())