import glob
import json
import os
from pathlib import Path
from collections import defaultdict
from typing import Dict, Tuple

from dotenv import load_dotenv
import argparse
import subprocess
import time

try:
    import psycopg2  # type: ignore
except Exception:
    psycopg2 = None


def parse_version_description(desc: str) -> dict:
    meta = {}
    if not desc:
        return meta
    for line in desc.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta


def main():
    parser = argparse.ArgumentParser(
        description="Audit and optionally resume pending runs"
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Execute pending runs instead of only printing suggestions",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=None,
        help="Max number of runs to execute in parallel when --run is provided (default: detected container count)",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent
    print(repo_root)
    cfg_glob = str(repo_root / ".fle" / "*" / "labplay*.json")
    print(cfg_glob)

    # Auto-load environment variables from the repo's .env
    load_dotenv(dotenv_path=repo_root / ".env")

    # Detect number of running Factorio containers (for offset cycling and default concurrency)
    num_containers = 1
    try:
        from fle.commons.cluster_ips import get_local_container_ips  # type: ignore

        result = get_local_container_ips()
        if isinstance(result, tuple) and len(result) == 3:
            _, _, tcp_ports = result
            if isinstance(tcp_ports, list) and len(tcp_ports) > 0:
                num_containers = len(tcp_ports)
    except Exception:
        num_containers = 1

    # Discover planned runs (env_id, model) pairs from configs
    planned_counts: dict[tuple[str, str], int] = defaultdict(int)
    config_map: dict[tuple[str, str], list[str]] = defaultdict(list)
    cfg_paths = sorted(glob.glob(cfg_glob))
    for cfg_path in cfg_paths:
        try:
            with open(cfg_path, "r") as f:
                configs = json.load(f)
        except Exception:
            continue
        for rc in configs:
            env_id = rc.get("env_id")
            model = rc.get("model", "")
            key = (env_id, model)
            planned_counts[key] += 8
            if cfg_path not in config_map[key]:
                config_map[key].append(cfg_path)

    # Completed runs from Postgres (distinct versions)
    completed_counts: Dict[Tuple[str, str], int] = defaultdict(int)
    versions: set[int] = set()

    # Require Postgres; no fallbacks
    required = [
        "SKILLS_DB_HOST",
        "SKILLS_DB_PORT",
        "SKILLS_DB_NAME",
        "SKILLS_DB_USER",
        "SKILLS_DB_PASSWORD",
    ]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise SystemExit(
            f"Missing Postgres env vars: {', '.join(missing)}. Set them and re-run."
        )

    if psycopg2 is None:
        raise SystemExit("psycopg2 not available. Install it to query Postgres.")

    # Query Postgres for completions and max version
    conn = psycopg2.connect(
        host=os.getenv("SKILLS_DB_HOST"),
        port=os.getenv("SKILLS_DB_PORT"),
        dbname=os.getenv("SKILLS_DB_NAME"),
        user=os.getenv("SKILLS_DB_USER"),
        password=os.getenv("SKILLS_DB_PASSWORD"),
    )
    cur = conn.cursor()
    cur.execute(
        """
        SELECT DISTINCT version, COALESCE(version_description, ''), COALESCE(model, '')
        FROM programs
        WHERE version IS NOT NULL
        """
    )
    for version, version_description, model in cur.fetchall():
        meta = parse_version_description(version_description)
        task_key = meta.get("type")
        if task_key:
            completed_counts[(task_key, model)] += 1
            versions.add(int(version))

    cur.execute("SELECT MAX(version) FROM programs")
    row = cur.fetchone()
    max_version = int(row[0]) if row and row[0] is not None else 0
    cur.close()
    conn.close()

    # No fallbacks: completed_counts is solely derived from Postgres

    total_planned = sum(planned_counts.values())
    total_completed = sum(
        min(planned_counts.get(k, 0), v) for k, v in completed_counts.items()
    )
    remaining = total_planned - total_completed

    print(f"Planned runs: {total_planned}")
    print(f"Completed runs (counted by distinct versions): {total_completed}")
    if versions:
        print(
            f"Version range present: v{min(versions)}..v{max(versions)} (n={len(versions)})"
        )
    print(f"Max version in DB: v{max_version}; next start: v{max_version + 1}")

    print("\nPer (env_id, model) remaining:")
    per_line = []
    for key in sorted(planned_counts.keys()):
        planned = planned_counts[key]
        done = completed_counts.get(key, 0)
        rem = max(0, planned - done)
        env_id, model = key
        per_line.append((rem, env_id, model, done, planned))
    per_line.sort(reverse=True)
    for rem, env_id, model, done, planned in per_line:
        if rem > 0:
            print(f"- {env_id} | {model}: {done}/{planned} done, {rem} remaining")

    print("\nSuggested resume commands (aggregate counts):")
    # Prepare key pools for per-process env injection
    openrouter_keys = [
        os.getenv(f"OPEN_ROUTER_API_KEY{i}")
        for i in range(1, 5)
        if os.getenv(f"OPEN_ROUTER_API_KEY{i}")
    ] or (
        [os.getenv("OPEN_ROUTER_API_KEY")] if os.getenv("OPEN_ROUTER_API_KEY") else []
    )
    anthropic_keys = [
        os.getenv(f"ANTHROPIC_API_KEY{i}")
        for i in range(1, 4)
        if os.getenv(f"ANTHROPIC_API_KEY{i}")
    ] or ([os.getenv("ANTHROPIC_API_KEY")] if os.getenv("ANTHROPIC_API_KEY") else [])

    # Build job list with per-run env and log path metadata
    commands: list[dict] = []
    resume_log_dir = (
        repo_root / ".fle" / "logs" / "resume" / time.strftime("%Y%m%d-%H%M%S")
    )
    resume_log_dir.mkdir(parents=True, exist_ok=True)
    openrouter_rr = 0
    anthropic_rr = 0
    for key, planned in planned_counts.items():
        done = completed_counts.get(key, 0)
        rem = max(0, planned - done)
        if rem <= 0:
            continue
        cfgs = config_map.get(key, [])
        if not cfgs:
            continue
        cfg = cfgs[0]
        print(f"# {rem}x pending for {key[0]} | {key[1]}")
        print(
            f"uv run -m fle.run eval --config '{cfg}' --offset 0  # repeat {rem} times"
        )
        job_idx = 0
        for _ in range(rem):
            # Cycle offsets 0..(num_containers-1)
            offset = job_idx % max(1, num_containers)
            cmd = [
                "uv",
                "run",
                "-m",
                "fle.run",
                "eval",
                "--config",
                cfg,
                "--offset",
                str(offset),
            ]
            # Per-job environment overrides (round-robin across available keys)
            env = os.environ.copy()
            safe_model = (key[1] or "").lower()
            if "claude" in safe_model and anthropic_keys:
                env["ANTHROPIC_API_KEY"] = anthropic_keys[
                    anthropic_rr % len(anthropic_keys)
                ]
                anthropic_rr += 1
            if (
                "open-router" in safe_model
                or "open_router" in safe_model
                or "openrouter" in safe_model
            ) and openrouter_keys:
                env["OPEN_ROUTER_API_KEY"] = openrouter_keys[
                    openrouter_rr % len(openrouter_keys)
                ]
                openrouter_rr += 1

            # Per-job log file (headless)
            cfg_name = Path(cfg).name
            env_name = (key[0] or "unknown").replace("/", "_")
            model_name = (key[1] or "unknown").replace("/", "_")
            log_path = (
                resume_log_dir / f"{env_name}__{model_name}__{cfg_name}__{job_idx}.log"
            )

            commands.append(
                {
                    "cmd": cmd,
                    "env": env,
                    "log_path": str(log_path),
                }
            )
            job_idx += 1

    print(f"\nTotal remaining: {remaining}")

    if args.run and commands:
        effective_concurrency = args.concurrency or max(1, num_containers)
        print(
            f"\nExecuting {len(commands)} runs with concurrency={effective_concurrency}..."
        )
        print(f"Logs: {resume_log_dir}")
        active: list[tuple[subprocess.Popen, object]] = []
        idx = 0
        while idx < len(commands) or active:
            # Start new processes up to concurrency limit
            while idx < len(commands) and len(active) < max(1, effective_concurrency):
                job = commands[idx]
                log_fh = open(job["log_path"], "ab")
                proc = subprocess.Popen(
                    job["cmd"],
                    cwd=str(repo_root),
                    stdout=log_fh,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    env=job.get("env"),
                )
                active.append((proc, log_fh))
                idx += 1
            # Poll and remove finished
            still_active: list[tuple[subprocess.Popen, object]] = []
            for p, fh in active:
                ret = p.poll()
                if ret is None:
                    still_active.append((p, fh))
                else:
                    try:
                        fh.close()
                    except Exception:
                        pass
            active = still_active
            if active:
                time.sleep(1)


if __name__ == "__main__":
    main()
