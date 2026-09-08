"""Benchmark the tiered event-driven observation mod (open_world scenario).

Requires a server running the scenario with observation_diff.lua loaded:
    python tests/benchmarks/benchmark_tiered_obs.py [--port 27099]
"""

import argparse
import statistics
import time

from factorio_rcon import RCONClient


class TieredClient:
    """Reconciles drained records into a full client-side game state."""

    def __init__(self):
        self.entities = {}  # unit_number -> row str
        self.water = {}  # (cx, cy) -> 1024-bit int mask
        self.ores = {}  # "x:y" -> (name, bucket)
        self.trees = set()  # "x:y"
        self.obstacles = set()  # "x:y" rocks + cliffs
        self.nests = {}  # unit_number -> (name, x, y)
        self.tick = 0
        self.research = None
        self.research_pct = 0
        self.player_x = 0.0
        self.player_y = 0.0
        self.techs_finished = []
        self.overflow = False

    def apply_entity(self, resp):
        if not resp:
            return 0
        records = resp.split(";")
        for rec in records:
            tag = rec[:1]
            if tag == "u":
                key, row = rec[1:].split(",", 1)
                self.entities[key] = row
            elif tag == "r":
                self.entities.pop(rec[1:], None)
            elif tag == "h":
                parts = rec[1:].split(":")
                self.tick = int(parts[0])
                self.research = None if parts[1] == "-" else parts[1]
                self.research_pct = int(parts[2])
                if len(parts) >= 5:
                    self.player_x = float(parts[3])
                    self.player_y = float(parts[4])
            elif tag == "q":
                self.techs_finished.append(rec[1:])
            elif tag == "!":
                self.overflow = True
        return len(records)

    def apply_terrain(self, resp):
        if not resp:
            return 0
        records = resp.split(";")
        for rec in records:
            tag = rec[:1]
            if tag == "c":
                cx, cy, hexmask = rec[1:].split(":", 2)
                self.water[(int(cx), int(cy))] = int(hexmask, 16) if hexmask else 0
            elif tag == "o":
                name, x, y, bucket = rec[1:].split(":")
                self.ores[f"{x}:{y}"] = (name, int(bucket))
            elif tag == "d":
                self.ores.pop(rec[1:], None)
            elif tag == "t":
                self.trees.add(rec[1:])
            elif tag == "x":
                self.trees.discard(rec[1:])
                self.obstacles.discard(rec[1:])
            elif tag == "k":
                self.obstacles.add(rec[1:])
            elif tag == "n":
                key, name, x, y = rec[1:].split(",")
                self.nests[key] = (name, float(x), float(y))
            elif tag == "m":
                self.nests.pop(rec[1:], None)
            elif tag == "!":
                self.overflow = True
        return len(records)


def bench(fn, iters=15, warmup=2):
    for _ in range(warmup):
        fn()
    ts = []
    for _ in range(iters):
        t0 = time.perf_counter()
        fn()
        ts.append((time.perf_counter() - t0) * 1000)
    return statistics.mean(ts), statistics.median(ts), min(ts), max(ts)


def fmt(label, r, extra=""):
    m, p50, mn, mx = r
    print(f"{label:36s} mean {m:7.1f} ms  p50 {p50:7.1f}  min {mn:7.1f}  max {mx:7.1f} {extra}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=27099)
    args = ap.parse_args()

    rc = RCONClient("localhost", args.port, "factorio")
    rc.connect()
    rc.send_command("/sc game.speed = 10")
    client = TieredClient()

    def drain_entities():
        return rc.send_command("/sc obs_diff_drain()") or ""

    def drain_terrain():
        return rc.send_command("/sc obs_terrain_drain()") or ""

    # --- 1. initial terrain burst from map generation ---
    t0 = time.perf_counter()
    resp = drain_terrain()
    n = client.apply_terrain(resp)
    t = (time.perf_counter() - t0) * 1000
    water_chunks = sum(1 for m in client.water.values() if m)
    print(f"initial terrain drain: {n} records, {len(resp) / 1024:.0f} KB, {t:.0f} ms")
    print(f"  client terrain: {len(client.water)} chunks ({water_chunks} with water), "
          f"{len(client.ores)} ore tiles, {len(client.trees)} trees, "
          f"{len(client.obstacles)} rocks/cliffs, {len(client.nests)} enemy structures", flush=True)

    # --- 2. spawn factory (raise_built -> events) ---
    SPAWN = """
    local surface = game.surfaces[1]
    local names = {"stone-furnace", "transport-belt", "burner-inserter", "assembling-machine-1", "iron-chest"}
    local placed = 0
    for i = 0, 999 do
        local e = surface.create_entity{name = names[(i % 5) + 1],
            position = {-140 + (i % 70) * 4, -140 + math.floor(i / 70) * 4},
            force = "player", raise_built = true}
        if e then placed = placed + 1 end
    end
    rcon.print(placed)
    """
    spawned = rc.send_command("/sc " + SPAWN.strip())
    resp = drain_entities()
    client.apply_entity(resp)
    print(f"\nspawned {spawned} entities -> drain {len(resp) / 1024:.1f} KB, client tracks {len(client.entities)}")

    # --- 3. hot factory: fuel + feed every furnace, machines run ---
    FUEL = """
    local n = 0
    for _, f in ipairs(game.surfaces[1].find_entities_filtered{name = "stone-furnace", force = "player"}) do
        f.get_inventory(defines.inventory.fuel).insert{name = "coal", count = 25}
        f.get_inventory(defines.inventory.furnace_source).insert{name = "iron-ore", count = 50}
        n = n + 1
    end
    rcon.print(n)
    """
    n_fueled = rc.send_command("/sc " + FUEL.strip())
    time.sleep(1.0)
    client.apply_entity(drain_entities())  # absorb the initial burst of status changes
    print(f"\nfueled {n_fueled} furnaces (smelting at speed 10). steady-state polls:")
    sizes, recs = [], []

    def hot_poll():
        resp = drain_entities()
        sizes.append(len(resp))
        recs.append(client.apply_entity(resp))

    fmt("hot-factory entity drain", bench(hot_poll, iters=30),
        f"(payload p50 {statistics.median(sizes):.0f} B, records p50 {statistics.median(recs):.0f})")

    # --- 4. chunk streaming: generate 121 new chunks mid-episode ---
    t0 = time.perf_counter()
    rc.send_command("/sc game.surfaces[1].request_to_generate_chunks({2000, 2000}, 5) "
                    "game.surfaces[1].force_generate_chunk_requests() rcon.print(1)")
    gen_t = (time.perf_counter() - t0) * 1000
    t0 = time.perf_counter()
    resp = drain_terrain()
    n = client.apply_terrain(resp)
    t = (time.perf_counter() - t0) * 1000
    print(f"\nnew-chunk streaming: generation {gen_t:.0f} ms; drain {n} records, "
          f"{len(resp) / 1024:.1f} KB, {t:.1f} ms -> client now {len(client.water)} chunks", flush=True)

    # --- 5. resource depletion: eventless amount drift ---
    DEPLETE = """
    local n = 0
    for _, o in ipairs(game.surfaces[1].find_entities_filtered{type = "resource", limit = 400}) do
        if o.amount > 600 then
            o.amount = o.amount - 500
            n = n + 1
        end
    end
    rcon.print(n)
    """
    n_dep = int(rc.send_command("/sc " + DEPLETE.strip()))
    t0 = time.perf_counter()
    caught = 0
    while caught < n_dep and time.perf_counter() - t0 < 60:
        resp = drain_terrain()
        caught += sum(1 for r in resp.split(";") if r[:1] == "o")
        client.apply_terrain(resp)
        time.sleep(0.1)
    print(f"\nresource reconciler: {caught}/{n_dep} depleted tiles surfaced in {time.perf_counter() - t0:.1f} s")

    # --- 6. tree removal events ---
    CHOP = """
    local n = 0
    for _, t in ipairs(game.surfaces[1].find_entities_filtered{type = "tree", limit = 20}) do
        t.destroy{raise_destroy = true}
        n = n + 1
    end
    rcon.print(n)
    """
    n_chop = rc.send_command("/sc " + CHOP.strip())
    resp = drain_terrain()
    n_x = sum(1 for r in resp.split(";") if r[:1] == "x")
    client.apply_terrain(resp)
    print(f"tree chop: {n_chop} destroyed -> {n_x} removal records in next drain")

    # --- 7. combined full-tier poll: one RCON call for both buffers ---
    sizes.clear()

    def full_poll():
        resp = rc.send_command("/sc obs_all_drain()") or ""
        sizes.append(len(resp))
        epart, _, tpart = resp.partition("~")
        client.apply_entity(epart)
        client.apply_terrain(tpart)

    r = bench(full_poll, iters=30)
    fmt("combined poll (single call)", r,
        f"(payload p50 {statistics.median(sizes):.0f} B) -> {1000 / r[0]:.0f} obs/s")

    # --- 8. effective UPS under mod load ---
    t0 = time.perf_counter()
    tick0 = int(rc.send_command("/sc rcon.print(game.tick)"))
    time.sleep(5)
    tick1 = int(rc.send_command("/sc rcon.print(game.tick)"))
    ups = (tick1 - tick0) / (time.perf_counter() - t0)
    print(f"\neffective UPS at speed 10: {ups:.0f} (target 600)")

    # --- 9. consistency checks ---
    SCAN = """
    local out = {}
    local n = 0
    for _, e in ipairs(game.surfaces[1].find_entities_filtered{force = "player"}) do
        if e.unit_number then
            n = n + 1
            out[n] = e.unit_number .. "|" .. e.name .. "|" .. e.position.x .. "," .. e.position.y
        end
    end
    rcon.print(table.concat(out, ";"))
    """
    time.sleep(1)
    client.apply_entity(drain_entities())
    resp = rc.send_command("/sc " + SCAN.strip()) or ""
    truth = {}
    for rec in resp.split(";"):
        if rec:
            key, name, pos = rec.split("|")
            truth[key] = (name, pos)
    mine = {}
    for key, row in client.entities.items():
        f = row.split(",")
        mine[key] = (f[0], f[1] + "," + f[2])
    missing = set(truth) - set(mine)
    extra = set(mine) - set(truth)
    mismatch = {k for k in set(truth) & set(mine) if truth[k] != mine[k]}
    print(f"entity consistency: server={len(truth)} client={len(mine)} "
          f"missing={len(missing)} extra={len(extra)} mismatch={len(mismatch)}")

    ORE_CHECK = """
    local total = 0
    for _, o in ipairs(game.surfaces[1].find_entities_filtered{type = "resource"}) do
        total = total + 1
    end
    rcon.print(total)
    """
    n_true = int(rc.send_command("/sc " + ORE_CHECK.strip()))
    print(f"ore consistency: server={n_true} tiles, client={len(client.ores)}")
    print(f"overflow flagged: {client.overflow}")


if __name__ == "__main__":
    main()