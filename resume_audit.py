import glob
import json
import os
import re
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

    # Completed runs from DB (distinct versions)
    completed_counts: Dict[Tuple[str, str], int] = defaultdict(int)
    versions: set[int] = set()

    # Prefer Postgres if configured
    use_pg = os.getenv("FLE_DB_TYPE", "sqlite").lower() == "postgres"
    pg_vars = [
        os.getenv("SKILLS_DB_HOST"),
        os.getenv("SKILLS_DB_PORT"),
        os.getenv("SKILLS_DB_NAME"),
        os.getenv("SKILLS_DB_USER"),
        os.getenv("SKILLS_DB_PASSWORD"),
    ]
    if use_pg and all(pg_vars) and psycopg2 is not None:
        try:
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
            cur.close()
            conn.close()
        except Exception:
            pass

    # Fallback: derive completed from log folders when DB is missing/unused
    if not completed_counts:
        logs_root = os.path.join(repo_root, ".fle", "trajectory_logs")
        if os.path.isdir(logs_root):
            for name in os.listdir(logs_root):
                if not re.match(r"^v\d+$", name):
                    continue
                run_dir = os.path.join(logs_root, name)
                prompt_path = os.path.join(run_dir, "agent0_system_prompt.txt")
                if not os.path.exists(prompt_path):
                    continue
                try:
                    with open(prompt_path, "r") as f:
                        # Read a small header window
                        head_lines = []
                        for _ in range(20):
                            line = f.readline()
                            if not line:
                                break
                            head_lines.append(line)
                        head = "".join(head_lines)
                except Exception:
                    continue
                m = re.search(
                    r"Create an automatic\s+([^\n]+?)\s+factory", head, re.IGNORECASE
                )
                if not m:
                    continue
                item = m.group(1).strip()
                slug = item.lower().replace(" ", "-")
                env_id = f"{slug}_throughput"
                matched = False
                for planned_env, model in list(planned_counts.keys()):
                    if planned_env == env_id:
                        completed_counts[(env_id, model)] += 1
                        matched = True
                if matched:
                    try:
                        versions.add(int(name[1:]))
                    except Exception:
                        pass

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
