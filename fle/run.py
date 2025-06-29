#!/usr/bin/env python3
import asyncio
from eval.open.independent_runs.run import main
from fle.env.gym_env.run_eval import main as run_eval
if __name__ == "__main__":
    asyncio.run(run_eval())