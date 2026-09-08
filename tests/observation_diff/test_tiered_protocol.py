"""Tests for the tiered event-driven observation protocol (observation_diff.lua).

Runs against a dedicated container provided by the tiered_rcon fixture; see
conftest.py. Each test uses its own map region so state does not interfere.
"""

import sys
import time
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
from benchmark_tensor_obs import TensorClient  # noqa: E402
from benchmark_tiered_obs import TieredClient  # noqa: E402


def drain_entities(rc):
    return rc.send_command("/sc obs_diff_drain()") or ""


def drain_terrain(rc):
    return rc.send_command("/sc obs_terrain_drain()") or ""


def drain_all(rc):
    resp = rc.send_command("/sc obs_all_drain()") or ""
    epart, _, tpart = resp.partition("~")
    return epart, tpart


def absorb(rc, client):
    """Drain and apply everything pending."""
    epart, tpart = drain_all(rc)
    client.apply_entity(epart)
    client.apply_terrain(tpart)


def spawn(rc, x0, y0, n, name="iron-chest", raise_built=True, spacing=2):
    flag = "true" if raise_built else "false"
    lua = f"""
    local placed = 0
    for i = 0, {n - 1} do
        local e = game.surfaces[1].create_entity{{name = "{name}",
            position = {{{x0} + (i % 10) * {spacing}, {y0} + math.floor(i / 10) * {spacing}}},
            force = "player", raise_built = {flag}}}
        if e then placed = placed + 1 end
    end
    rcon.print(placed)
    """
    return int(rc.send_command("/sc " + lua.strip()))


def poll_until(rc, client, predicate, timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        absorb(rc, client)
        if predicate():
            return True
        time.sleep(0.2)
    return False


@pytest.fixture()
def client(tiered_rcon):
    """A fresh client, synced to current server state."""
    c = TieredClient()
    resp = tiered_rcon.send_command("/sc obs_terrain_full_sync()") or ""
    c.apply_terrain(resp)
    resp = tiered_rcon.send_command("/sc obs_diff_full_sync()") or ""
    c.apply_entity(resp)
    return c


def test_rcon_functions_exist(tiered_rcon):
    for fn in ("obs_diff_drain", "obs_terrain_drain", "obs_all_drain",
               "obs_diff_full_sync", "obs_terrain_full_sync"):
        assert tiered_rcon.send_command(f"/sc rcon.print(type({fn}))") == "function"


def test_initial_terrain_state(client):
    """Map-gen chunk events (or full sync) populate the terrain tiers."""
    assert len(client.water) > 50, "expected many generated chunks"
    assert len(client.ores) > 100, "expected ore tiles on the starting map"
    assert len(client.trees) > 100, "expected trees on the starting map"


def test_header_reports_advancing_tick(tiered_rcon, client):
    absorb(tiered_rcon, client)
    t1 = client.tick
    time.sleep(0.5)
    absorb(tiered_rcon, client)
    assert client.tick > t1
    assert 0 <= client.research_pct <= 100


def test_build_events_upsert(tiered_rcon, client):
    before = len(client.entities)
    placed = spawn(tiered_rcon, 100, 100, 20)
    assert placed == 20
    assert poll_until(tiered_rcon, client, lambda: len(client.entities) == before + 20)
    row = next(r for r in client.entities.values() if r.startswith("iron-chest,1"))
    name, x, y, direction, status = row.split(",")[:5]
    assert name == "iron-chest"
    assert 100 <= float(x) <= 120


def test_destroy_events_remove(tiered_rcon, client):
    spawn(tiered_rcon, 140, 100, 10)
    absorb(tiered_rcon, client)
    before = len(client.entities)
    n = int(tiered_rcon.send_command("""/sc local n = 0
for _, e in ipairs(game.surfaces[1].find_entities_filtered{name = "iron-chest",
        force = "player", area = {{139, 99}, {160, 121}}}) do
    e.destroy{raise_destroy = true}
    n = n + 1
end
rcon.print(n)""".strip()))
    assert n == 10
    assert poll_until(tiered_rcon, client, lambda: len(client.entities) == before - 10)


def test_client_matches_authoritative_scan(tiered_rcon, client):
    spawn(tiered_rcon, 180, 100, 15, name="stone-furnace")
    time.sleep(0.5)
    absorb(tiered_rcon, client)
    resp = tiered_rcon.send_command("""/sc local out = {}
for _, e in ipairs(game.surfaces[1].find_entities_filtered{force = "player"}) do
    if e.unit_number then
        out[#out + 1] = e.unit_number .. "|" .. e.name .. "|" .. e.position.x .. "," .. e.position.y
    end
end
rcon.print(table.concat(out, ";"))""".strip()) or ""
    truth = {}
    for rec in resp.split(";"):
        if rec:
            key, name, pos = rec.split("|")
            truth[key] = (name, pos)
    mine = {}
    for key, row in client.entities.items():
        f = row.split(",")
        mine[key] = (f[0], f[1] + "," + f[2])
    assert mine == truth


def test_eventless_mutation_reconciled(tiered_rcon, client):
    """Script-set direction fires no event; the slice reconciler catches it."""
    spawn(tiered_rcon, 220, 100, 5, name="transport-belt")
    absorb(tiered_rcon, client)
    tiered_rcon.send_command("""/sc for _, b in ipairs(game.surfaces[1].find_entities_filtered{
    name = "transport-belt", force = "player", area = {{219, 99}, {240, 121}}}) do
    b.direction = 4
end rcon.print(1)""".strip())

    def rotated():
        rows = [r for r in client.entities.values()
                if r.startswith("transport-belt,2")]
        return len(rows) == 5 and all(r.split(",")[3] == "4" for r in rows)

    assert poll_until(tiered_rcon, client, rotated), "reconciler missed direction change"


def test_eventless_creation_discovered(tiered_rcon, client):
    """create_entity without raise_built fires no event; the discovery sweep
    (every DISCOVERY_EVERY reconcile passes) must still find it."""
    before = len(client.entities)
    placed = spawn(tiered_rcon, 260, 100, 8, raise_built=False)
    assert placed == 8
    assert poll_until(
        tiered_rcon, client, lambda: len(client.entities) >= before + 8, timeout=120
    ), "discovery sweep missed eventless entities"


def test_hot_field_quantization_stays_sparse(tiered_rcon, client):
    """A running furnace changes state every tick, but quantized rows should
    only emit records on bucket transitions."""
    spawn(tiered_rcon, 300, 100, 5, name="stone-furnace", spacing=3)
    tiered_rcon.send_command("""/sc for _, f in ipairs(game.surfaces[1].find_entities_filtered{
    name = "stone-furnace", force = "player", area = {{299, 99}, {320, 121}}}) do
    f.get_inventory(defines.inventory.fuel).insert{name = "coal", count = 20}
    f.get_inventory(defines.inventory.furnace_source).insert{name = "iron-ore", count = 40}
end rcon.print(1)""".strip())
    time.sleep(1.0)
    absorb(tiered_rcon, client)  # absorb the ignition burst

    # a fueled furnace row carries quantized hot fields
    hot = [r for r in client.entities.values()
           if r.startswith("stone-furnace") and ",Icoal:" in r]
    assert hot, "expected fueled furnace rows with inventory buckets"

    total_records = 0
    for _ in range(10):
        epart, tpart = drain_all(tiered_rcon)
        total_records += sum(1 for r in epart.split(";") if r[:1] == "u")
        client.apply_entity(epart)
        client.apply_terrain(tpart)
        time.sleep(0.1)
    # 5 furnaces smelting at speed 10 for ~1s: without quantization this would
    # be hundreds of updates; bucketed rows should emit only a handful.
    assert total_records < 50, f"hot rows not sparse: {total_records} upserts"


def test_resource_depletion_reconciled(tiered_rcon, client):
    changed = int(tiered_rcon.send_command("""/sc local n = 0
for _, o in ipairs(game.surfaces[1].find_entities_filtered{type = "resource", limit = 50}) do
    if o.amount > 600 then o.amount = o.amount - 500 n = n + 1 end
end
rcon.print(n)""".strip()))
    assert changed > 0, "test map had no depletable ore"
    seen = {"n": 0}

    def caught():
        return seen["n"] >= changed

    deadline = time.time() + 60
    while time.time() < deadline and not caught():
        _, tpart = drain_all(tiered_rcon)
        seen["n"] += sum(1 for r in tpart.split(";") if r[:1] == "o")
        client.apply_terrain(tpart)
        time.sleep(0.2)
    assert caught(), f"only {seen['n']}/{changed} depletion updates surfaced"


def test_tree_removal_events(tiered_rcon, client):
    before = len(client.trees)
    assert before > 0
    n = int(tiered_rcon.send_command("""/sc local n = 0
for _, t in ipairs(game.surfaces[1].find_entities_filtered{type = "tree", limit = 10}) do
    t.destroy{raise_destroy = true}
    n = n + 1
end
rcon.print(n)""".strip()))
    assert n == 10
    assert poll_until(tiered_rcon, client, lambda: len(client.trees) == before - 10)


def test_new_chunks_stream_to_client(tiered_rcon, client):
    before = len(client.water)
    tiered_rcon.send_command(
        "/sc game.surfaces[1].request_to_generate_chunks({3000, 3000}, 3) "
        "game.surfaces[1].force_generate_chunk_requests() rcon.print(1)")
    assert poll_until(tiered_rcon, client, lambda: len(client.water) > before), \
        "newly generated chunks never reached the client"


def test_full_sync_resets_consistently(tiered_rcon, client):
    """After arbitrary churn, a fresh client full-syncs to identical state."""
    spawn(tiered_rcon, 340, 100, 12)
    absorb(tiered_rcon, client)
    fresh = TieredClient()
    fresh.apply_entity(tiered_rcon.send_command("/sc obs_diff_full_sync()") or "")
    assert set(fresh.entities) == set(client.entities)
    # rows may differ only in flickering status; compare structural fields
    for key in fresh.entities:
        assert fresh.entities[key].split(",")[:4] == client.entities[key].split(",")[:4]


def test_tensor_incremental_matches_rebuild(tiered_rcon):
    """Incrementally-maintained grid equals a from-scratch rebuild after churn."""
    c = TensorClient()
    c.apply_terrain(tiered_rcon.send_command("/sc obs_terrain_full_sync()") or "")
    c.apply_entity(tiered_rcon.send_command("/sc obs_diff_full_sync()") or "")
    spawn(tiered_rcon, 380, 100, 10)
    time.sleep(0.5)
    absorb(tiered_rcon, c)
    incremental = c.grid.copy()
    c.rebuild()
    np.testing.assert_allclose(incremental, c.grid, atol=1e-4)
    n_tracked = len(c._contrib)
    assert float(c.grid[0:6].sum()) == pytest.approx(n_tracked)

def _tensor_client(rc):
    c = TensorClient()
    c.apply_terrain(rc.send_command("/sc obs_terrain_full_sync()") or "")
    c.apply_entity(rc.send_command("/sc obs_diff_full_sync()") or "")
    return c


def test_entity_table_exact_position_and_properties(tiered_rcon):
    """The table row carries the exact server position and exact item counts
    (wire rows transmit exact values; only the change trigger is bucketed)."""
    c = _tensor_client(tiered_rcon)
    unit = int(tiered_rcon.send_command("""/sc local e = game.surfaces[1].create_entity{
    name = "iron-chest", position = {420, 100}, force = "player", raise_built = true}
e.get_inventory(defines.inventory.chest).insert{name = "iron-plate", count = 37}
rcon.print(e.unit_number .. "," .. e.position.x .. "," .. e.position.y)""".strip()).split(",")[0])
    truth = tiered_rcon.send_command(f"""/sc for _, e in ipairs(game.surfaces[1].find_entities_filtered{{
    name = "iron-chest", force = "player", area = {{{{419, 99}}, {{422, 102}}}}}}) do
    if e.unit_number == {unit} then rcon.print(e.position.x .. "," .. e.position.y) end
end""".strip())
    tx, ty = map(float, truth.split(","))

    # The build event fires during create_entity, BEFORE the insert, so the
    # first row snapshot has an empty chest; the reconciler must then pick up
    # the eventless insert. Poll until the exact count lands.
    def has_exact_count():
        slot = c._slot_of.get(str(unit))
        return slot is not None and c.table[slot][15] == 37.0

    assert poll_until(tiered_rcon, c, has_exact_count), \
        "reconciler never delivered the exact inventory count"
    row = c.table[c._slot_of[str(unit)]]
    assert (row[0], row[1]) == (tx, ty), "table position is not exact"
    assert row[10] == 37.0  # top inventory slot: exact count
    assert c.table_mask[c._slot_of[str(unit)]] == 1.0


def test_entity_table_slot_stability(tiered_rcon):
    """Slots are stable for an entity's lifetime under incremental updates:
    removing one entity must not move any other entity's row."""
    c = _tensor_client(tiered_rcon)
    spawn(tiered_rcon, 460, 100, 3, spacing=4)
    absorb(tiered_rcon, c)
    def in_region(row):
        f = row.split(",")
        return f[0] == "iron-chest" and 459 <= float(f[1]) <= 470 and 99 <= float(f[2]) <= 102

    keys = sorted(k for k, r in c.entities.items() if in_region(r))
    assert len(keys) == 3
    slots_before = {k: c._slot_of[k] for k in keys}
    victim = keys[1]
    vx, vy = c.entities[victim].split(",")[1:3]
    tiered_rcon.send_command(f"""/sc for _, e in ipairs(game.surfaces[1].find_entities_filtered{{
    name = "iron-chest", position = {{{vx}, {vy}}}, radius = 0.5}}) do
    e.destroy{{raise_destroy = true}}
end rcon.print(1)""".strip())
    assert poll_until(tiered_rcon, c, lambda: victim not in c._slot_of)
    assert c.table_mask[slots_before[victim]] == 0.0
    for k in (keys[0], keys[2]):
        assert c._slot_of[k] == slots_before[k], "survivor slot moved"
        assert c.table_mask[slots_before[k]] == 1.0


def test_entity_table_tracks_rebuild_and_dict(tiered_rcon):
    """Occupancy always equals the entity dict; a rebuild reproduces the same
    set of (position, type) rows even though slot assignment may differ."""
    c = _tensor_client(tiered_rcon)
    spawn(tiered_rcon, 500, 100, 6)
    absorb(tiered_rcon, c)
    assert int(c.table_mask.sum()) == len(c.entities)
    live = c.table[c.table_mask > 0]
    rows_before = {tuple(r[[0, 1, 4]]) for r in live}
    c.rebuild()
    assert int(c.table_mask.sum()) == len(c.entities)
    live = c.table[c.table_mask > 0]
    assert {tuple(r[[0, 1, 4]]) for r in live} == rows_before
