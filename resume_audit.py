import glob
import json
import os
from collections import defaultdict
from typing import Dict, Tuple

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
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    cfg_glob = os.path.join(repo_root, ".fle", "[1-7]", "labplay*.json")

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

    print(f"\nTotal remaining: {remaining}")


if __name__ == "__main__":
    main()
