"""Benchmark the control.lua event-driven diff mod on the open_world scenario."""

import statistics
import time

from factorio_rcon import RCONClient

rc = RCONClient("localhost", 27099, "factorio")
rc.connect()

state = {}


def apply_diff(resp):
    if not resp:
        return 0
    changes = resp.split(";")
    for c in changes:
        if c[0] == "u":
            key, row = c[1:].split(",", 1)
            state[key] = row
        elif c[0] == "r":
            state.pop(c[1:], None)
    return len(changes)


def drain():
    return rc.send_command("/sc obs_diff_drain()") or ""


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
    print(f"{label:34s} mean {m:7.1f} ms  p50 {p50:7.1f}  min {mn:7.1f}  max {mx:7.1f}  -> {1000 / m:6.0f} obs/s {extra}", flush=True)


# --- 1. spawn 1000 entities WITH raise_built: events populate the buffer ---
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
t0 = time.perf_counter()
print("spawned:", rc.send_command("/sc " + SPAWN.strip()), f"({(time.perf_counter() - t0) * 1000:.0f} ms)")

t0 = time.perf_counter()
resp = drain()
n = apply_diff(resp)
print(f"drain after spawn: {n} records, {len(resp) / 1024:.1f} KB, {(time.perf_counter() - t0) * 1000:.1f} ms, client entities = {len(state)}")

# --- 2. full sync (cold client) ---
def full_sync():
    resp = rc.send_command("/sc obs_diff_full_sync()") or ""
    state.clear()
    apply_diff(resp)
    return resp

t0 = time.perf_counter()
resp = full_sync()
print(f"full_sync: {len(state)} entities, {len(resp) / 1024:.1f} KB, {(time.perf_counter() - t0) * 1000:.1f} ms")

# --- 3. steady state: nothing changed ---
sizes = []
def poll():
    resp = drain()
    sizes.append(len(resp))
    apply_diff(resp)

fmt("steady-state drain", bench(poll), f"(avg payload {statistics.mean(sizes):.0f} B)")

# --- 4. event churn: 25 builds + 25 destroys (raised) between polls ---
CHURN = """
local surface = game.surfaces[1]
local built = 0
for i = 0, 24 do
    local e = surface.create_entity{name = "wooden-chest",
        position = {150 + (i % 5) * 2, 150 + math.floor(i / 5) * 2},
        force = "player", raise_built = true}
    if e then built = built + 1 end
end
local chests = surface.find_entities_filtered{name = "wooden-chest", force = "player"}
local killed = 0
for i = 1, math.min(25, #chests) do
    chests[i].destroy{raise_destroy = true}
    killed = killed + 1
end
rcon.print(built .. "/" .. killed)
"""
sizes.clear()
ts = []
for _ in range(12):
    rc.send_command("/sc " + CHURN.strip())
    t0 = time.perf_counter()
    poll()
    ts.append((time.perf_counter() - t0) * 1000)
fmt("50-event churn drain", (statistics.mean(ts), statistics.median(ts), min(ts), max(ts)), f"(avg payload {statistics.mean(sizes):.0f} B)")

# --- 5. eventless churn: script-set direction, reconciler must catch it ---
ROTATE = """
local belts = game.surfaces[1].find_entities_filtered{name = "transport-belt", force = "player", limit = 50}
for _, b in ipairs(belts) do b.direction = (b.direction + 4) % 16 end
rcon.print(#belts)
"""
print("\nrotating 50 belts via script (no events fired)...")
rc.send_command("/sc " + ROTATE.strip())
t0 = time.perf_counter()
caught = 0
while caught < 50 and time.perf_counter() - t0 < 30:
    resp = drain()
    caught += sum(1 for c in resp.split(";") if c and c[0] == "u" and "transport-belt" in c)
    apply_diff(resp)
    time.sleep(0.25)
print(f"reconciler caught {caught}/50 rotations in {time.perf_counter() - t0:.1f} s")

# --- 6. consistency check: client state vs authoritative full scan ---
SCAN = """
local out = {}
local n = 0
local ents = game.surfaces[1].find_entities_filtered{force = "player"}
for i = 1, #ents do
    local e = ents[i]
    if e.unit_number then
        n = n + 1
        out[n] = e.unit_number .. "," .. e.name .. "," .. e.position.x .. "," .. e.position.y .. "," .. (e.direction or 0)
    end
end
rcon.print(table.concat(out, ";"))
"""
resp = rc.send_command("/sc " + SCAN.strip()) or ""
truth = {}
for rec in resp.split(";"):
    if rec:
        key, rest = rec.split(",", 1)
        truth[key] = rest
mine = {k: v.rsplit(",", 1)[0] for k, v in state.items()}  # drop status (flickers)
missing = set(truth) - set(mine)
extra = set(mine) - set(truth)
mismatch = {k for k in set(truth) & set(mine) if truth[k] != mine[k]}
print(f"\nconsistency: server={len(truth)} client={len(mine)} missing={len(missing)} extra={len(extra)} field-mismatch={len(mismatch)}")
if mismatch:
    k = next(iter(mismatch))
    print("  example mismatch:", k, "server:", truth[k], "client:", mine[k])
