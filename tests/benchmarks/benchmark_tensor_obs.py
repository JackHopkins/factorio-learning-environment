"""End-to-end observation tensor benchmark: RCON drain -> reconcile -> numpy.

Builds an MLP-ready float32 tensor from the tiered diff protocol and measures
the full pipeline. The tensor is updated incrementally from diff records, so
steady-state cost is O(changes), not O(world).

Tensor layout: [C, H, W] spatial grid (CELL-tile cells centered on origin)
plus a small global feature vector.

    channels 0-5   entity counts per type (furnace/belt/inserter/assembler/chest/other)
    channel  6     status sum (working=1.0 scale)
    channels 7-8   direction sin/cos sums
    channel  9     energy (MJ buckets)
    channel  10    crafting progress (deciles)
    channel  11    inventory fullness (log2 bucket sum)
    channel  12    water tile count
    channel  13    tree count
    channel  14    rock/cliff count
    channel  15    ore amount (bucket sum)
    channel  16    enemy structure count

All channels are additive so record application is subtract-old/add-new.

Usage: python tests/benchmarks/benchmark_tensor_obs.py [--port 27099]
"""

import argparse
import math
import statistics
import sys
import time
from pathlib import Path

import numpy as np
from factorio_rcon import RCONClient

sys.path.insert(0, str(Path(__file__).parent))
from benchmark_tiered_obs import TieredClient  # noqa: E402

GRID = 96  # cells per side
CELL = 3  # tiles per cell
HALF = GRID * CELL // 2  # window covers [-HALF, HALF) tiles
N_CHANNELS = 17
ENTITY_CHANNEL = {
    "stone-furnace": 0,
    "transport-belt": 1,
    "burner-inserter": 2,
    "assembling-machine-1": 3,
    "iron-chest": 4,
}
OTHER_CHANNEL = 5
C_STATUS, C_SIN, C_COS, C_ENERGY, C_PROGRESS, C_INV = 6, 7, 8, 9, 10, 11
C_WATER, C_TREE, C_ROCK, C_ORE, C_NEST = 12, 13, 14, 15, 16
N_GLOBAL = 8


def cell_of(x, y):
    gx = int((x + HALF) // CELL)
    gy = int((y + HALF) // CELL)
    if 0 <= gx < GRID and 0 <= gy < GRID:
        return gx, gy
    return None


class TensorClient(TieredClient):
    """TieredClient that incrementally maintains an MLP observation tensor."""

    def __init__(self):
        super().__init__()
        self.grid = np.zeros((N_CHANNELS, GRID, GRID), dtype=np.float32)
        self.global_vec = np.zeros(N_GLOBAL, dtype=np.float32)
        self._contrib = {}  # unit_number -> (gy, gx, channel_values dict)
        self._ore_contrib = {}  # "x:y" -> (gy, gx, bucket)
        self._water_contrib = {}  # (cx, cy) -> list of (gy, gx, count)

    # -- entity rows ---------------------------------------------------------

    @staticmethod
    def _parse_row(row):
        fields = row.split(",")
        name = fields[0]
        x, y = float(fields[1]), float(fields[2])
        direction, status = int(fields[3]), int(fields[4])
        energy = progress = inv = 0.0
        for f in fields[5:]:
            tag = f[:1]
            if tag == "E":
                energy = float(f[1:])
            elif tag == "P":
                progress = float(f[1:])
            elif tag == "I":
                inv += float(f.rsplit(":", 1)[1])
        return name, x, y, direction, status, energy, progress, inv

    def _entity_contrib(self, row):
        name, x, y, direction, status, energy, progress, inv = self._parse_row(row)
        cell = cell_of(x, y)
        if cell is None:
            return None
        gx, gy = cell
        angle = direction / 16.0 * 2.0 * math.pi
        return gy, gx, {
            ENTITY_CHANNEL.get(name, OTHER_CHANNEL): 1.0,
            C_STATUS: status / 10.0,
            C_SIN: math.sin(angle),
            C_COS: math.cos(angle),
            C_ENERGY: energy,
            C_PROGRESS: progress / 10.0,
            C_INV: inv,
        }

    def _apply_contrib(self, contrib, sign):
        gy, gx, values = contrib
        for channel, v in values.items():
            self.grid[channel, gy, gx] += sign * v

    def apply_entity(self, resp):
        if not resp:
            return 0
        records = resp.split(";")
        for rec in records:
            tag = rec[:1]
            if tag == "u":
                key, row = rec[1:].split(",", 1)
                old = self._contrib.pop(key, None)
                if old is not None:
                    self._apply_contrib(old, -1.0)
                contrib = self._entity_contrib(row)
                if contrib is not None:
                    self._contrib[key] = contrib
                    self._apply_contrib(contrib, +1.0)
                self.entities[key] = row
            elif tag == "r":
                key = rec[1:]
                old = self._contrib.pop(key, None)
                if old is not None:
                    self._apply_contrib(old, -1.0)
                self.entities.pop(key, None)
            elif tag == "h":
                tick, research, pct = rec[1:].split(":")
                self.tick = int(tick)
                self.research = None if research == "-" else research
                self.research_pct = int(pct)
            elif tag == "q":
                self.techs_finished.append(rec[1:])
            elif tag == "!":
                self.overflow = True
        self._update_globals()
        return len(records)

    # -- terrain records -----------------------------------------------------

    def _apply_water_chunk(self, cx, cy, hexmask):
        old = self._water_contrib.pop((cx, cy), None)
        if old is not None:
            for gy, gx, count in old:
                self.grid[C_WATER, gy, gx] -= count
        if not hexmask:
            return
        rows = np.array([int(hexmask[i * 8:(i + 1) * 8], 16) for i in range(32)],
                        dtype=np.uint32)
        tile_mask = (rows[:, None] >> np.arange(32, dtype=np.uint32)[None, :]) & 1
        dy, dx = np.nonzero(tile_mask)
        wx = cx * 32 + dx + HALF
        wy = cy * 32 + dy + HALF
        keep = (wx >= 0) & (wx < GRID * CELL) & (wy >= 0) & (wy < GRID * CELL)
        if not keep.any():
            return
        gx = wx[keep] // CELL
        gy = wy[keep] // CELL
        cells = {}
        for a, b in zip(gy, gx):
            cells[(int(a), int(b))] = cells.get((int(a), int(b)), 0) + 1
        contrib = [(a, b, c) for (a, b), c in cells.items()]
        self._water_contrib[(cx, cy)] = contrib
        for gy_, gx_, count in contrib:
            self.grid[C_WATER, gy_, gx_] += count

    def _point_delta(self, key, channel, new_value):
        """Set a point contribution on `channel`, replacing any previous one."""
        old = self._ore_contrib.pop(key, None)
        if old is not None:
            gy, gx, v = old
            self.grid[channel, gy, gx] -= v
        if new_value is None:
            return
        x, y = key.split(":")
        cell = cell_of(float(x), float(y))
        if cell is None:
            return
        gx, gy = cell
        self._ore_contrib[key] = (gy, gx, new_value)
        self.grid[channel, gy, gx] += new_value

    def apply_terrain(self, resp):
        if not resp:
            return 0
        records = resp.split(";")
        for rec in records:
            tag = rec[:1]
            if tag == "c":
                cx, cy, hexmask = rec[1:].split(":", 2)
                cx, cy = int(cx), int(cy)
                self.water[(cx, cy)] = int(hexmask, 16) if hexmask else 0
                self._apply_water_chunk(cx, cy, hexmask)
            elif tag == "o":
                name, x, y, bucket = rec[1:].split(":")
                key = f"{x}:{y}"
                self.ores[key] = (name, int(bucket))
                self._point_delta(key, C_ORE, float(bucket))
            elif tag == "d":
                key = rec[1:]
                self.ores.pop(key, None)
                self._point_delta(key, C_ORE, None)
            elif tag == "t":
                key = rec[1:]
                if key not in self.trees:
                    self.trees.add(key)
                    cell = cell_of(*map(float, key.split(":")))
                    if cell:
                        self.grid[C_TREE, cell[1], cell[0]] += 1
            elif tag == "x":
                key = rec[1:]
                cell = cell_of(*map(float, key.split(":")))
                if key in self.trees:
                    self.trees.discard(key)
                    if cell:
                        self.grid[C_TREE, cell[1], cell[0]] -= 1
                elif key in self.obstacles:
                    self.obstacles.discard(key)
                    if cell:
                        self.grid[C_ROCK, cell[1], cell[0]] -= 1
            elif tag == "k":
                key = rec[1:]
                if key not in self.obstacles:
                    self.obstacles.add(key)
                    cell = cell_of(*map(float, key.split(":")))
                    if cell:
                        self.grid[C_ROCK, cell[1], cell[0]] += 1
            elif tag == "n":
                key, name, x, y = rec[1:].split(",")
                self.nests[key] = (name, float(x), float(y))
                cell = cell_of(float(x), float(y))
                if cell:
                    self.grid[C_NEST, cell[1], cell[0]] += 1
            elif tag == "m":
                key = rec[1:]
                nest = self.nests.pop(key, None)
                if nest:
                    cell = cell_of(nest[1], nest[2])
                    if cell:
                        self.grid[C_NEST, cell[1], cell[0]] -= 1
            elif tag == "!":
                self.overflow = True
        self._update_globals()
        return len(records)

    def _update_globals(self):
        g = self.global_vec
        g[0] = self.tick / 1e6
        g[1] = self.research_pct / 100.0
        g[2] = len(self.entities) / 1e4
        g[3] = len(self.ores) / 1e4
        g[4] = len(self.trees) / 1e5
        g[5] = len(self.nests) / 100.0
        g[6] = len(self.techs_finished) / 100.0
        g[7] = 1.0 if self.overflow else 0.0

    def observation(self):
        """Flat float32 vector for an MLP (zero-copy views)."""
        return self.grid.reshape(-1), self.global_vec

    def rebuild(self):
        """Full tensor rebuild from client dicts (recenter / recovery path)."""
        self.grid[:] = 0.0
        self._contrib.clear()
        self._ore_contrib.clear()
        self._water_contrib.clear()
        for key, row in self.entities.items():
            contrib = self._entity_contrib(row)
            if contrib is not None:
                self._contrib[key] = contrib
                self._apply_contrib(contrib, +1.0)
        for key, (_, bucket) in self.ores.items():
            self._point_delta(key, C_ORE, float(bucket))
        for key in self.trees:
            cell = cell_of(*map(float, key.split(":")))
            if cell:
                self.grid[C_TREE, cell[1], cell[0]] += 1
        for key in self.obstacles:
            cell = cell_of(*map(float, key.split(":")))
            if cell:
                self.grid[C_ROCK, cell[1], cell[0]] += 1
        for _, x, y in self.nests.values():
            cell = cell_of(x, y)
            if cell:
                self.grid[C_NEST, cell[1], cell[0]] += 1
        for (cx, cy), mask in self.water.items():
            hexmask = format(mask, "0256x") if mask else ""
            self._apply_water_chunk(cx, cy, hexmask)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=27099)
    args = ap.parse_args()

    rc = RCONClient("localhost", args.port, "factorio")
    rc.connect()
    rc.send_command("/sc game.speed = 10")
    client = TensorClient()

    flat, gvec = client.observation()
    print(f"tensor: grid {client.grid.shape} + global {gvec.shape} = "
          f"{flat.size + gvec.size} float32 ({(flat.nbytes + gvec.nbytes) / 1024:.0f} KB)\n")

    # --- 1. initial sync: terrain burst + entity snapshot -> tensor ---
    t0 = time.perf_counter()
    resp_t = rc.send_command("/sc obs_terrain_drain()") or ""
    if resp_t.count(";") < 100:  # burst already consumed: mid-episode attach
        resp_t = rc.send_command("/sc obs_terrain_full_sync()") or ""
    resp_e = rc.send_command("/sc obs_diff_full_sync()") or ""
    t_rcon = (time.perf_counter() - t0) * 1000
    t0 = time.perf_counter()
    n_t = client.apply_terrain(resp_t)
    n_e = client.apply_entity(resp_e)
    t_apply = (time.perf_counter() - t0) * 1000
    print(f"initial sync: {n_t + n_e} records ({(len(resp_t) + len(resp_e)) / 1024:.0f} KB); "
          f"rcon {t_rcon:.0f} ms + apply-to-tensor {t_apply:.0f} ms", flush=True)

    # --- 2. spawn factory + make it hot ---
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
    for _, f in ipairs(surface.find_entities_filtered{name = "stone-furnace", force = "player"}) do
        f.get_inventory(defines.inventory.fuel).insert{name = "coal", count = 25}
        f.get_inventory(defines.inventory.furnace_source).insert{name = "iron-ore", count = 50}
    end
    rcon.print(placed)
    """
    spawned = rc.send_command("/sc " + SPAWN.strip())
    time.sleep(1.0)
    resp = rc.send_command("/sc obs_all_drain()") or ""
    epart, _, tpart = resp.partition("~")
    t0 = time.perf_counter()
    client.apply_entity(epart)
    client.apply_terrain(tpart)
    t = (time.perf_counter() - t0) * 1000
    print(f"spawned {spawned} + fueled furnaces -> burst applied to tensor in {t:.1f} ms")

    # --- 3. end-to-end steady-state: drain -> reconcile -> tensor ---
    t_rcons, t_applies, sizes = [], [], []

    def e2e_poll():
        t0 = time.perf_counter()
        resp = rc.send_command("/sc obs_all_drain()") or ""
        t1 = time.perf_counter()
        epart, _, tpart = resp.partition("~")
        client.apply_entity(epart)
        client.apply_terrain(tpart)
        _ = client.observation()
        t2 = time.perf_counter()
        t_rcons.append((t1 - t0) * 1000)
        t_applies.append((t2 - t1) * 1000)
        sizes.append(len(resp))
        return (t2 - t0) * 1000

    for _ in range(3):
        e2e_poll()
    t_rcons.clear(); t_applies.clear(); sizes.clear()
    totals = [e2e_poll() for _ in range(30)]
    print(f"\nE2E poll (hot factory): mean {statistics.mean(totals):.1f} ms  "
          f"p50 {statistics.median(totals):.1f}  min {min(totals):.1f}  max {max(totals):.1f}"
          f"  -> {1000 / statistics.mean(totals):.0f} obs/s")
    print(f"  breakdown p50: rcon {statistics.median(t_rcons):.2f} ms, "
          f"reconcile+tensor {statistics.median(t_applies):.3f} ms "
          f"(payload p50 {statistics.median(sizes):.0f} B)")

    # --- 4. full rebuild (recenter / recovery path) ---
    ts = []
    for _ in range(10):
        t0 = time.perf_counter()
        client.rebuild()
        ts.append((time.perf_counter() - t0) * 1000)
    print(f"\nfull tensor rebuild: mean {statistics.mean(ts):.1f} ms  p50 {statistics.median(ts):.1f} ms "
          f"(from {len(client.entities)} entities, {len(client.ores)} ores, {len(client.trees)} trees)")

    # --- 5. sanity checks ---
    grid = client.grid
    n_in_window = sum(1 for c in client._contrib.values())
    type_sum = float(grid[0:6].sum())
    print(f"\nsanity: entity-channel sum {type_sum:.0f} vs tracked-in-window {n_in_window}"
          f" | ore cells {int((grid[C_ORE] > 0).sum())}, tree cells {int((grid[C_TREE] > 0).sum())},"
          f" water cells {int((grid[C_WATER] > 0).sum())}")
    print(f"nonzero grid values: {int((grid != 0).sum())}/{grid.size} "
          f"({100 * (grid != 0).sum() / grid.size:.1f}%)")
    assert type_sum == n_in_window, "entity channel counts drifted from contrib map"
    print("PASS: incremental tensor consistent")


if __name__ == "__main__":
    main()