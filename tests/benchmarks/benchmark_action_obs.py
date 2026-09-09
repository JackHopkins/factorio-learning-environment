"""Benchmark FLE action <-> observation round trips on the tiered protocol.

Uses a real FactorioInstance so actions run through FLE's existing tool Lua
(verified semantics, unmodified). For each action we measure:
  - action latency: the FLE tool call itself (RCON round trip + Lua)
  - poll latency: one obs_all_drain -> reconcile -> observation() afterwards
  - visibility latency: time until the action's effect appears in the client
    state. FLE tools mutate the world via script (no raise_built / events),
    so visibility rides the reconciler / discovery tiers - this measures the
    real act->perceive loop an RL agent would experience.

Usage: python tests/benchmarks/benchmark_action_obs.py [--port 27099]
"""

import argparse
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from benchmark_tensor_obs import TensorClient  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=27099)
    ap.add_argument("--reps", type=int, default=8)
    args = ap.parse_args()

    from fle.env import FactorioInstance
    from fle.env.entities import Direction, Position
    from fle.env.game_types import Prototype

    print("connecting FactorioInstance (injects tool Lua)...", flush=True)
    instance = FactorioInstance(
        address="localhost",
        tcp_port=args.port,
        fast=True,
        cache_scripts=True,
        all_technologies_researched=True,
        inventory={
            "stone-furnace": 40,
            "burner-inserter": 40,
            "transport-belt": 40,
            "coal": 400,
            "iron-plate": 400,
        },
    )
    instance.set_speed(10.0)
    ns = instance.namespace
    rc = instance.rcon_client

    # warm the server: first minutes after a container start run 10-50x
    # slow under box64 dynarec; gate on a sub-5ms noop before measuring
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < 90:
        s = time.perf_counter()
        rc.send_command("/sc rcon.print(1)")
        if (time.perf_counter() - s) * 1000 < 5:
            break
        time.sleep(1)
    print(f"warmup: {time.perf_counter() - t0:.0f} s", flush=True)

    client = TensorClient(table_rows=8192)
    client.apply_entity(rc.send_command("/sc obs_diff_full_sync()") or "")
    resp = rc.send_command("/sc obs_terrain_full_sync()") or ""
    client.apply_terrain(resp)
    print(f"synced: {len(client.entities)} entities, player at "
          f"({client.player_x:.1f}, {client.player_y:.1f})\n", flush=True)

    def poll():
        resp = rc.send_command("/sc obs_all_drain()") or ""
        epart, _, tpart = resp.partition("~")
        client.apply_entity(epart)
        client.apply_terrain(tpart)
        _ = client.observation()

    def visible_within(predicate, timeout=90.0):
        t0 = time.perf_counter()
        while time.perf_counter() - t0 < timeout:
            poll()
            if predicate():
                return (time.perf_counter() - t0) * 1000
            time.sleep(0.02)
        return float("inf")

    results = {}

    def record(name, act_ms, poll_ms, vis_ms):
        results.setdefault(name, {"act": [], "poll": [], "vis": []})
        results[name]["act"].append(act_ms)
        results[name]["poll"].append(poll_ms)
        results[name]["vis"].append(vis_ms)

    def timed(fn):
        t0 = time.perf_counter()
        out = fn()
        return out, (time.perf_counter() - t0) * 1000

    start = ns.player_location
    for i in range(args.reps):
        # setup (untimed): walk to a fresh build site, everything within reach
        ns.move_to(Position(x=start.x + i * 8, y=start.y))
        base = ns.player_location
        fx, fy = base.x + 3, base.y + 3

        # --- place_entity: script placement, eventless -> discovery sweep ---
        furnace, act = timed(lambda: ns.place_entity(
            Prototype.StoneFurnace, position=Position(x=fx, y=fy)))
        n_before = len(client.entities)
        _, p = timed(poll)
        vis = visible_within(lambda: any(
            r.startswith("stone-furnace") and abs(float(r.split(",")[1]) - furnace.position.x) < 1
            and abs(float(r.split(",")[2]) - furnace.position.y) < 1
            for r in client.entities.values()))
        record("place_entity", act, p, vis)

        # --- insert_item into that furnace: bucket change -> reconciler ---
        _, act = timed(lambda: ns.insert_item(Prototype.Coal, furnace, quantity=10))
        _, p = timed(poll)

        def furnace_has_coal():
            for r in client.entities.values():
                if (r.startswith("stone-furnace")
                        and abs(float(r.split(",")[1]) - furnace.position.x) < 1
                        and abs(float(r.split(",")[2]) - furnace.position.y) < 1):
                    return ".coal:" in r
            return False

        vis = visible_within(furnace_has_coal)
        record("insert_item", act, p, vis)

        # --- place + rotate an inserter: script rotation, eventless ---
        ins, _ = timed(lambda: ns.place_entity(
            Prototype.BurnerInserter, position=Position(x=fx + 2.5, y=fy - 1)))
        visible_within(lambda: any(
            r.startswith("burner-inserter") and abs(float(r.split(",")[1]) - ins.position.x) < 1
            and abs(float(r.split(",")[2]) - ins.position.y) < 1
            for r in client.entities.values()))
        def row_dirs():
            # FLE's Direction enum does not map 1:1 onto engine e.direction for
            # inserters (drop-side semantics), and rotate_entity may recreate
            # the entity for some types - so detect visibility as "the row
            # direction at this position changed from its pre-rotation value".
            return {int(r.split(",")[3]) for r in client.entities.values()
                    if r.startswith("burner-inserter")
                    and abs(float(r.split(",")[1]) - ins.position.x) < 1
                    and abs(float(r.split(",")[2]) - ins.position.y) < 1}

        dirs_before = row_dirs()
        rotated, act = timed(lambda: ns.rotate_entity(ins, Direction.LEFT))
        _, p = timed(poll)
        vis = visible_within(lambda: bool(row_dirs() - dirs_before))
        record("rotate_entity", act, p, vis)

        # --- craft_item: player inventory change (not entity state) ---
        _, act = timed(lambda: ns.craft_item(Prototype.IronGearWheel, quantity=1))
        _, p = timed(poll)
        record("craft_item", act, p, 0.0)  # player inventory is not entity state

        # --- move_to: header position, read live every drain ---
        target = Position(x=base.x + 10 + (i % 3) * 2, y=base.y)
        _, act = timed(lambda: ns.move_to(target))
        _, p = timed(poll)
        vis = visible_within(
            lambda: abs(client.player_x - ns.player_location.x) < 0.5
            and abs(client.player_y - ns.player_location.y) < 0.5)
        record("move_to", act, p, vis)

    print(f"{'action':16s} {'action ms (p50)':>16s} {'obs poll ms':>12s} {'visible-in ms':>14s}")
    for name, r in results.items():
        vis = [v for v in r["vis"] if v != float("inf")]
        vis_str = f"{statistics.median(vis):>10.0f}" if vis else "TIMEOUT"
        misses = len(r["vis"]) - len(vis)
        note = f"  ({misses} timeouts)" if misses else ""
        print(f"{name:16s} {statistics.median(r['act']):>16.1f} "
              f"{statistics.median(r['poll']):>12.1f} {vis_str:>14s}{note}", flush=True)

    # canonical RL step: action + one observation, no visibility wait
    ts = []
    pos0 = ns.player_location
    for i in range(20):
        t0 = time.perf_counter()
        ns.move_to(Position(x=pos0.x + (i % 5), y=pos0.y))
        poll()
        ts.append((time.perf_counter() - t0) * 1000)
    print(f"\nact+observe cycle (move_to + poll): p50 {statistics.median(ts):.1f} ms "
          f"-> {1000 / statistics.median(ts):.0f} steps/s", flush=True)
    instance.cleanup()


if __name__ == "__main__":
    main()