"""Stress benchmark: tiered observation protocol against a large active factory.

Builds smelting cells (furnace + burner-inserter + chest + belt) in stages up
to ~20k entities spread over ~500x260 tiles, fuels everything, and measures at
each scale: steady-state drains, UPS, drift-detection latency, cold-attach
cost, and recenter cost. Table capacity is raised to 32k rows.

Usage: python tests/benchmarks/benchmark_stress.py [--port 27099]
"""

import argparse
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from benchmark_tensor_obs import TensorClient  # noqa: E402

STRESS_TABLE_ROWS = 32768
SCALES = (5000, 10000, 20000)
CELLS_PER_ROW = 100  # cell = 5x5 tiles; 100 cells/row -> x in [-250, 250)


def drain_apply(rc, client):
    resp = rc.send_command("/sc obs_all_drain()") or ""
    epart, _, tpart = resp.partition("~")
    client.apply_entity(epart)
    client.apply_terrain(tpart)
    return len(resp)


def spawn_cells(rc, first_cell, n_cells):
    """Each cell: stone-furnace, burner-inserter, iron-chest, transport-belt."""
    lua = f"""
    local surface = game.surfaces[1]
    local placed = 0
    for i = {first_cell}, {first_cell + n_cells - 1} do
        local cx = -250 + (i % {CELLS_PER_ROW}) * 5
        local cy = -250 + math.floor(i / {CELLS_PER_ROW}) * 5
        local specs = {{
            {{"stone-furnace", cx + 1, cy + 1}},
            {{"burner-inserter", cx + 2.5, cy + 0.5}},
            {{"iron-chest", cx + 3.5, cy + 0.5}},
            {{"transport-belt", cx + 2.5, cy + 2.5}},
        }}
        for _, s in ipairs(specs) do
            local e = surface.create_entity{{name = s[1], position = {{s[2], s[3]}},
                force = "player", raise_built = true}}
            if e then placed = placed + 1 end
        end
    end
    rcon.print(placed)
    """
    return int(rc.send_command("/sc " + lua.strip()))


FUEL = """
local n = 0
for _, f in ipairs(game.surfaces[1].find_entities_filtered{name = "stone-furnace", force = "player"}) do
    f.get_inventory(defines.inventory.fuel).insert{name = "coal", count = 50}
    f.get_inventory(defines.inventory.furnace_source).insert{name = "iron-ore", count = 100}
    n = n + 1
end
for _, i in ipairs(game.surfaces[1].find_entities_filtered{name = "burner-inserter", force = "player"}) do
    i.get_inventory(defines.inventory.fuel).insert{name = "coal", count = 5}
end
rcon.print(n)
"""


def measure_ups(rc, seconds=5):
    t0 = time.perf_counter()
    a = int(rc.send_command("/sc rcon.print(game.tick)"))
    time.sleep(seconds)
    b = int(rc.send_command("/sc rcon.print(game.tick)"))
    return (b - a) / (time.perf_counter() - t0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=27099)
    args = ap.parse_args()

    from factorio_rcon import RCONClient

    rc = RCONClient("localhost", args.port, "factorio")
    rc.connect()
    rc.send_command("/sc game.speed = 10")
    client = TensorClient(table_rows=STRESS_TABLE_ROWS)

    # terrain for the whole build area (+ some margin) before spawning
    print("generating chunks (radius 12)...", flush=True)
    t0 = time.perf_counter()
    rc.send_command("/sc game.surfaces[1].request_to_generate_chunks({0, 0}, 12) "
                    "game.surfaces[1].force_generate_chunk_requests() rcon.print(1)")
    print(f"  chunk generation: {time.perf_counter() - t0:.1f} s", flush=True)
    n = drain_apply(rc, client)
    print(f"  terrain drain: {n / 1024:.0f} KB -> {len(client.water)} chunks, "
          f"{len(client.ores)} ores, {len(client.trees)} trees "
          f"(overflow={client.overflow})", flush=True)

    rc.send_command("""/sc if #game.surfaces[1].find_entities_filtered{type = "character"} == 0 then
    game.surfaces[1].create_entity{name = "character", position = {0, 0}, force = "player", raise_built = true}
end rcon.print(1)""".strip())

    total_cells = 0
    for target in SCALES:
        cells_needed = target // 4
        # spawn in batches, draining between to stay under buffer caps
        t0 = time.perf_counter()
        while total_cells < cells_needed:
            batch = min(500, cells_needed - total_cells)
            spawn_cells(rc, total_cells, batch)
            total_cells += batch
            drain_apply(rc, client)
        build_t = time.perf_counter() - t0
        n_fueled = int(rc.send_command("/sc " + FUEL.strip()))
        time.sleep(2.0)
        drain_apply(rc, client)

        n_entities = len(client.entities)
        print(f"\n=== scale ~{target}: {n_entities} tracked entities, "
              f"{n_fueled} furnaces smelting (built in {build_t:.0f} s) ===", flush=True)

        # steady-state polls
        totals, rcon_ts, payloads = [], [], []
        for _ in range(50):
            t0 = time.perf_counter()
            resp = rc.send_command("/sc obs_all_drain()") or ""
            t1 = time.perf_counter()
            epart, _, tpart = resp.partition("~")
            client.apply_entity(epart)
            client.apply_terrain(tpart)
            _ = client.observation()
            totals.append((time.perf_counter() - t0) * 1000)
            rcon_ts.append((t1 - t0) * 1000)
            payloads.append(len(resp))
        totals.sort()
        print(f"  steady poll: p50 {statistics.median(totals):6.1f} ms  "
              f"p95 {totals[47]:6.1f}  max {totals[-1]:6.1f}  "
              f"(rcon p50 {statistics.median(rcon_ts):.1f} ms, "
              f"payload p50 {statistics.median(payloads):.0f} B, "
              f"p95 {sorted(payloads)[47]} B)", flush=True)

        ups = measure_ups(rc)
        print(f"  UPS at speed 10: {ups:.0f}", flush=True)

        # drift-detection latency: rotate 200 belts via script (no events)
        n_rot = int(rc.send_command("""/sc local n = 0
for _, b in ipairs(game.surfaces[1].find_entities_filtered{name = "transport-belt", force = "player"}) do
    if n >= 200 then break end
    b.direction = (b.direction == 4) and 8 or 4
    n = n + 1
end
rcon.print(n)""".strip()))
        t0 = time.perf_counter()
        caught = 0
        while caught < n_rot and time.perf_counter() - t0 < 300:
            resp = rc.send_command("/sc obs_diff_drain()") or ""
            caught += sum(1 for r in resp.split(";")
                          if r[:1] == "u" and "transport-belt" in r)
            client.apply_entity(resp)
            time.sleep(0.25)
        print(f"  drift latency: {caught}/{n_rot} script-rotated belts "
              f"surfaced in {time.perf_counter() - t0:.1f} s", flush=True)

        # cold attach: fresh client, full syncs
        fresh = TensorClient(table_rows=STRESS_TABLE_ROWS)
        t0 = time.perf_counter()
        resp_e = rc.send_command("/sc obs_diff_full_sync()") or ""
        resp_t = rc.send_command("/sc obs_terrain_full_sync()") or ""
        t_rcon = (time.perf_counter() - t0) * 1000
        t0 = time.perf_counter()
        fresh.apply_entity(resp_e)
        fresh.apply_terrain(resp_t)
        t_apply = (time.perf_counter() - t0) * 1000
        t0 = time.perf_counter()
        fresh.rebuild()
        t_rebuild = (time.perf_counter() - t0) * 1000
        print(f"  cold attach: {(len(resp_e) + len(resp_t)) / 1024:.0f} KB, "
              f"rcon {t_rcon:.0f} ms + apply {t_apply:.0f} ms; "
              f"full rebuild {t_rebuild:.0f} ms; "
              f"client match: {len(fresh.entities) == len(client.entities)}", flush=True)
        client = fresh  # continue with the freshly synced client

        # recenter cost: teleport player across the factory
        ts = []
        for corner in ("{-240, -240}", "{240, -240}", "{240, 240}", "{0, 0}"):
            rc.send_command(
                "/sc local ch = game.surfaces[1].find_entities_filtered{type = \"character\"}[1] "
                f"ch.teleport({corner}) rcon.print(1)")
            t0 = time.perf_counter()
            drain_apply(rc, client)
            _ = client.observation()
            ts.append((time.perf_counter() - t0) * 1000)
        print(f"  corner-teleport polls (forced recenter): "
              f"{', '.join(f'{t:.0f}' for t in ts)} ms", flush=True)
        assert not client.overflow, "buffer/table overflow during stress"

    # authoritative consistency at final scale. Pause the world first: on this
    # map biters actively destroy the factory, so a live comparison lags by
    # whatever died between the last drain and the scan.
    rc.send_command("/sc game.tick_paused = true")
    drain_apply(rc, client)
    n_true = int(rc.send_command("""/sc local n = 0
for _, e in ipairs(game.surfaces[1].find_entities_filtered{force = "player"}) do
    if e.unit_number then n = n + 1 end
end
rcon.print(n)""".strip()))
    rc.send_command("/sc game.tick_paused = false game.speed = 10")
    print(f"\nfinal consistency (paused world): server={n_true} "
          f"client={len(client.entities)} exact={n_true == len(client.entities)} "
          f"table_slots={int(client.table_mask.sum())} overflow={client.overflow}", flush=True)


if __name__ == "__main__":
    main()