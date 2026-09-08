"""End-to-end observation tensor benchmark: RCON drain -> reconcile -> numpy.

Builds an MLP-ready float32 tensor from the tiered diff protocol and measures
the full pipeline. The tensor is updated incrementally from diff records, so
steady-state cost is O(changes), not O(world).

Observation views: [C, H, W] spatial grid of CELL-tile cells tracking the
player character (recentering when they leave a dead zone), a small global
feature vector including the exact player position, and an object-level
entity view of the VIEW_K entities nearest the player, nearest-first with
player-relative coordinates (the full absolute table stays available
internally at table_rows capacity for actions and consistency checks).

    channels 0-5   entity counts per type (furnace/belt/inserter/assembler/chest/other)
    channel  6     status sum (working=1.0 scale)
    channels 7-8   direction sin/cos sums
    channel  9     energy (MJ)
    channel  10    crafting progress (0-1)
    channel  11    inventory fullness (log2 of total count)
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
HALF = GRID * CELL // 2  # window covers [center - HALF, center + HALF) tiles
RECENTER_DEADZONE = 24.0  # tiles the player may drift before the grid recenters
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
N_GLOBAL = 10

# Entity table: object-level view with exact positions and properties,
# mirroring the fields of the fle.env.entities object model.
F_X, F_Y = 0, 1  # exact tile coordinates
F_SIN, F_COS = 2, 3  # direction
F_TYPE = 4  # type id (session vocab)
F_STATUS = 5
F_RECIPE = 6  # recipe id (0 = none)
F_ENERGY = 7  # exact joules
F_PROGRESS = 8  # exact crafting percent
F_HEALTH = 9  # exact hit points
F_TILE_W, F_TILE_H = 10, 11  # footprint (tile_dimensions)
F_DROP_DX, F_DROP_DY = 12, 13  # drop_position relative to entity (0,0 = none)
F_PICK_DX, F_PICK_DY = 14, 15  # pickup_position relative to entity
F_ELEC_ID = 16  # electric network id (0 = not connected)
F_TEMP = 17  # temperature
F_FLUID_ID, F_FLUID_AMT = 18, 19  # first fluidbox: fluid id, exact amount
F_INV_START = 20  # 8 slots x (item id, exact count), largest counts first
N_INV_SLOTS = 8
F_INV_TOTAL = F_INV_START + 2 * N_INV_SLOTS  # 36: total item count
F_INV_DISTINCT = F_INV_TOTAL + 1  # 37: number of distinct item stacks
TABLE_ROWS = 2048
TABLE_FEATS = F_INV_DISTINCT + 1
VIEW_K = 2048  # observation() returns the K entities nearest the player


class TensorClient(TieredClient):
    """TieredClient that incrementally maintains MLP observation tensors.

    Two views of the same lossless client state:
      grid  (N_CHANNELS, GRID, GRID) - additive spatial context, cell-coarse
      table (TABLE_ROWS, TABLE_FEATS) + mask - object-level view with EXACT
            positions and per-entity properties; slot indices are stable for
            an entity's lifetime (free-list allocation, no compaction), so a
            policy can point at specific entities across steps.
    """

    def __init__(self, table_rows=TABLE_ROWS, view_k=VIEW_K):
        super().__init__()
        self.view_k = view_k
        self.grid = np.zeros((N_CHANNELS, GRID, GRID), dtype=np.float32)
        self.global_vec = np.zeros(N_GLOBAL, dtype=np.float32)
        self.table = np.zeros((table_rows, TABLE_FEATS), dtype=np.float32)
        self.table_mask = np.zeros(table_rows, dtype=np.float32)
        self.view_units = []  # unit_number per view row, set by observation()
        self._contrib = {}  # unit_number -> (gy, gx, channel_values dict)
        self._ore_contrib = {}  # "x:y" -> (gy, gx, bucket)
        self._water_contrib = {}  # (cx, cy) -> list of (gy, gx, count)
        self._slot_of = {}  # unit_number -> table row
        self._unit_at = {}  # table row -> unit_number
        self._free_slots = list(range(table_rows - 1, -1, -1))
        self._vocab = {}  # "kind:name" -> stable int id (session-scoped, >0)
        self.center_x = 0  # grid window center, CELL-quantized world coords
        self.center_y = 0

    def _cell_of(self, x, y):
        gx = int((x - self.center_x + HALF) // CELL)
        gy = int((y - self.center_y + HALF) // CELL)
        if 0 <= gx < GRID and 0 <= gy < GRID:
            return gx, gy
        return None

    def _maybe_recenter(self):
        """Recenter the grid on the player once they leave the dead zone.
        Only grid contributions rebuild - table slots stay stable."""
        if (abs(self.player_x - self.center_x) <= RECENTER_DEADZONE
                and abs(self.player_y - self.center_y) <= RECENTER_DEADZONE):
            return
        self.center_x = CELL * round(self.player_x / CELL)
        self.center_y = CELL * round(self.player_y / CELL)
        self._rebuild_grid()

    # -- entity rows ---------------------------------------------------------

    @staticmethod
    def _parse_row(row):
        """Parse an exact-valued row into a field dict. Items arrive as
        I<invidx>.<name>:<count>; positions in D/K tags are absolute."""
        fields = row.split(",")
        p = {
            "name": fields[0],
            "x": float(fields[1]),
            "y": float(fields[2]),
            "direction": int(fields[3]),
            "status": int(fields[4]),
            "energy": 0.0,
            "progress": 0.0,
            "recipe": None,
            "health": 0.0,
            "tile_w": 0.0,
            "tile_h": 0.0,
            "drop": None,
            "pickup": None,
            "elec_id": 0.0,
            "temp": 0.0,
            "items": [],  # (invidx, name, exact count)
            "fluids": [],  # (name, exact amount)
        }
        for f in fields[5:]:
            tag = f[:1]
            if tag == "E":
                p["energy"] = float(f[1:])
            elif tag == "P":
                p["progress"] = float(f[1:])
            elif tag == "R":
                p["recipe"] = f[1:]
            elif tag == "H":
                p["health"] = float(f[1:])
            elif tag == "W":
                w, h = f[1:].split(":")
                p["tile_w"], p["tile_h"] = float(w), float(h)
            elif tag == "D":
                dx, dy = f[1:].split(":")
                p["drop"] = (float(dx), float(dy))
            elif tag == "K":
                kx, ky = f[1:].split(":")
                p["pickup"] = (float(kx), float(ky))
            elif tag == "N":
                p["elec_id"] = float(f[1:])
            elif tag == "T":
                p["temp"] = float(f[1:])
            elif tag == "I":
                slot, rest = f[1:].split(".", 1)
                item, count = rest.rsplit(":", 1)
                p["items"].append((int(slot), item, float(count)))
            elif tag == "F":
                fluid, amount = f[1:].rsplit(":", 1)
                p["fluids"].append((fluid, float(amount)))
        return p

    def _vid(self, kind, name):
        key = kind + ":" + name
        vid = self._vocab.get(key)
        if vid is None:
            vid = len(self._vocab) + 1
            self._vocab[key] = vid
        return vid

    def _entity_contrib(self, row):
        p = self._parse_row(row)
        cell = self._cell_of(p["x"], p["y"])
        if cell is None:
            return None
        gx, gy = cell
        angle = p["direction"] / 16.0 * 2.0 * math.pi
        total_items = sum(c for _, _, c in p["items"])
        return gy, gx, {
            ENTITY_CHANNEL.get(p["name"], OTHER_CHANNEL): 1.0,
            C_STATUS: p["status"] / 10.0,
            C_SIN: math.sin(angle),
            C_COS: math.cos(angle),
            C_ENERGY: p["energy"] / 1e6,
            C_PROGRESS: p["progress"] / 100.0,
            C_INV: math.log2(1.0 + total_items),
        }

    # -- entity table --------------------------------------------------------

    def _table_upsert(self, key, row):
        p = self._parse_row(row)
        slot = self._slot_of.get(key)
        if slot is None:
            if not self._free_slots:
                self.overflow = True
                return
            slot = self._free_slots.pop()
            self._slot_of[key] = slot
            self._unit_at[slot] = key
        angle = p["direction"] / 16.0 * 2.0 * math.pi
        r = self.table[slot]
        r[:] = 0.0
        r[F_X], r[F_Y] = p["x"], p["y"]  # exact tile positions
        r[F_SIN], r[F_COS] = math.sin(angle), math.cos(angle)
        r[F_TYPE] = self._vid("type", p["name"])
        r[F_STATUS] = p["status"]
        if p["recipe"]:
            r[F_RECIPE] = self._vid("recipe", p["recipe"])
        r[F_ENERGY] = p["energy"]
        r[F_PROGRESS] = p["progress"]
        r[F_HEALTH] = p["health"]
        r[F_TILE_W], r[F_TILE_H] = p["tile_w"], p["tile_h"]
        if p["drop"]:
            r[F_DROP_DX] = p["drop"][0] - p["x"]
            r[F_DROP_DY] = p["drop"][1] - p["y"]
        if p["pickup"]:
            r[F_PICK_DX] = p["pickup"][0] - p["x"]
            r[F_PICK_DY] = p["pickup"][1] - p["y"]
        r[F_ELEC_ID] = p["elec_id"]
        r[F_TEMP] = p["temp"]
        if p["fluids"]:
            r[F_FLUID_ID] = self._vid("fluid", p["fluids"][0][0])
            r[F_FLUID_AMT] = p["fluids"][0][1]
        # merge duplicate items across inventories, then top-N by count
        merged = {}
        for _, item, count in p["items"]:
            merged[item] = merged.get(item, 0.0) + count
        ranked = sorted(merged.items(), key=lambda kv: -kv[1])
        for i, (item, count) in enumerate(ranked[:N_INV_SLOTS]):
            r[F_INV_START + 2 * i] = self._vid("item", item)
            r[F_INV_START + 2 * i + 1] = count
        r[F_INV_TOTAL] = sum(merged.values())
        r[F_INV_DISTINCT] = len(merged)
        self.table_mask[slot] = 1.0

    def _table_remove(self, key):
        slot = self._slot_of.pop(key, None)
        if slot is not None:
            self._unit_at.pop(slot, None)
            self.table[slot] = 0.0
            self.table_mask[slot] = 0.0
            self._free_slots.append(slot)

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
                self._table_upsert(key, row)
                self.entities[key] = row
            elif tag == "r":
                key = rec[1:]
                old = self._contrib.pop(key, None)
                if old is not None:
                    self._apply_contrib(old, -1.0)
                self._table_remove(key)
                self.entities.pop(key, None)
            elif tag == "h":
                parts = rec[1:].split(":")
                self.tick = int(parts[0])
                self.research = None if parts[1] == "-" else parts[1]
                self.research_pct = int(parts[2])
                if len(parts) >= 5:
                    self.player_x = float(parts[3])
                    self.player_y = float(parts[4])
                    self._maybe_recenter()
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
        wx = cx * 32 + dx - self.center_x + HALF
        wy = cy * 32 + dy - self.center_y + HALF
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
        cell = self._cell_of(float(x), float(y))
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
                    cell = self._cell_of(*map(float, key.split(":")))
                    if cell:
                        self.grid[C_TREE, cell[1], cell[0]] += 1
            elif tag == "x":
                key = rec[1:]
                cell = self._cell_of(*map(float, key.split(":")))
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
                    cell = self._cell_of(*map(float, key.split(":")))
                    if cell:
                        self.grid[C_ROCK, cell[1], cell[0]] += 1
            elif tag == "n":
                key, name, x, y = rec[1:].split(",")
                self.nests[key] = (name, float(x), float(y))
                cell = self._cell_of(float(x), float(y))
                if cell:
                    self.grid[C_NEST, cell[1], cell[0]] += 1
            elif tag == "m":
                key = rec[1:]
                nest = self.nests.pop(key, None)
                if nest:
                    cell = self._cell_of(nest[1], nest[2])
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
        g[8] = self.player_x
        g[9] = self.player_y

    def observation(self):
        """Observation views for an MLP/transformer policy: (flat grid,
        global vec, K-nearest entity view, view mask).

        The view is a fixed (view_k, TABLE_FEATS) array holding the view_k
        entities nearest the player, nearest-first, with player-RELATIVE
        x/y. self.view_units gives the unit_number behind each view row
        (distance ordering means view rows are not lifetime-stable), and
        the full absolute table remains available via self.table."""
        k = self.view_k
        view = np.zeros((k, TABLE_FEATS), dtype=np.float32)
        view_mask = np.zeros(k, dtype=np.float32)
        live_idx = np.nonzero(self.table_mask)[0]
        if live_idx.size:
            dx = self.table[live_idx, F_X] - self.player_x
            dy = self.table[live_idx, F_Y] - self.player_y
            d2 = dx * dx + dy * dy
            if live_idx.size > k:
                sel = np.argpartition(d2, k - 1)[:k]
                sel = sel[np.argsort(d2[sel])]
            else:
                sel = np.argsort(d2)
            chosen = live_idx[sel]
            n = chosen.size
            view[:n] = self.table[chosen]
            view[:n, F_X] -= self.player_x
            view[:n, F_Y] -= self.player_y
            view_mask[:n] = 1.0
            self.view_units = [self._unit_at[int(s)] for s in chosen]
        else:
            self.view_units = []
        return self.grid.reshape(-1), self.global_vec, view, view_mask

    def _rebuild_grid(self):
        """Rebuild grid contributions for the current window center. Table
        slots are untouched, so slot indices stay stable across recenters."""
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
            cell = self._cell_of(*map(float, key.split(":")))
            if cell:
                self.grid[C_TREE, cell[1], cell[0]] += 1
        for key in self.obstacles:
            cell = self._cell_of(*map(float, key.split(":")))
            if cell:
                self.grid[C_ROCK, cell[1], cell[0]] += 1
        for _, x, y in self.nests.values():
            cell = self._cell_of(x, y)
            if cell:
                self.grid[C_NEST, cell[1], cell[0]] += 1
        for (cx, cy), mask in self.water.items():
            hexmask = format(mask, "0256x") if mask else ""
            self._apply_water_chunk(cx, cy, hexmask)

    def rebuild(self):
        """Full tensor rebuild from client dicts (recovery path).

        Note: table slots are reallocated, so slot indices are NOT stable
        across a full rebuild (they are stable under incremental updates
        and grid recenters)."""
        self._rebuild_grid()
        self.table[:] = 0.0
        self.table_mask[:] = 0.0
        self._slot_of.clear()
        self._unit_at.clear()
        self._free_slots = list(range(self.table.shape[0] - 1, -1, -1))
        for key, row in sorted(self.entities.items()):
            self._table_upsert(key, row)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=27099)
    args = ap.parse_args()

    rc = RCONClient("localhost", args.port, "factorio")
    rc.connect()
    rc.send_command("/sc game.speed = 10")
    client = TensorClient()

    flat, gvec, table, mask = client.observation()
    total = flat.size + gvec.size + table.size + mask.size
    total_kb = (flat.nbytes + gvec.nbytes + table.nbytes + mask.nbytes) / 1024
    print(f"tensor: grid {client.grid.shape} + global {gvec.shape} + "
          f"table {table.shape} + mask {mask.shape} = {total} float32 ({total_kb:.0f} KB)\n")

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

    # --- 3b. egocentric tracking: stationary, walking, sprinting ---
    rc.send_command("""/sc if #game.surfaces[1].find_entities_filtered{type = "character"} == 0 then
    game.surfaces[1].create_entity{name = "character", position = {-100, -100}, force = "player", raise_built = true}
end rcon.print(1)""".strip())

    def measure_moving(step_tiles, label, iters=30):
        totals, recenters = [], 0
        last_center = (client.center_x, client.center_y)
        for _ in range(iters):
            if step_tiles:
                rc.send_command(
                    "/sc local ch = game.surfaces[1].find_entities_filtered{type = \"character\"}[1] "
                    f"ch.teleport({{ch.position.x + {step_tiles}, ch.position.y}}) rcon.print(1)")
            t0 = time.perf_counter()
            resp = rc.send_command("/sc obs_all_drain()") or ""
            epart, _, tpart = resp.partition("~")
            client.apply_entity(epart)
            client.apply_terrain(tpart)
            _ = client.observation()
            totals.append((time.perf_counter() - t0) * 1000)
            center = (client.center_x, client.center_y)
            if center != last_center:
                recenters += 1
                last_center = center
        print(f"  {label:26s} mean {statistics.mean(totals):6.1f} ms  "
              f"p50 {statistics.median(totals):6.1f}  max {max(totals):6.1f}  "
              f"({recenters} recenters/{iters} polls)", flush=True)

    print("\negocentric tracking (poll incl. drain + apply + observation()):")
    measure_moving(0, "stationary player")
    measure_moving(6, "walking (6 tiles/poll)")
    measure_moving(60, "sprinting (60 tiles/poll)")

    ts = []
    for _ in range(50):
        t0 = time.perf_counter()
        _ = client.observation()
        ts.append((time.perf_counter() - t0) * 1000)
    print(f"  observation() view alone   mean {statistics.mean(ts):6.2f} ms  "
          f"p50 {statistics.median(ts):6.2f} (table copy + relativize)")

    # --- 4. full rebuild (recenter / recovery path) ---
    ts = []
    for _ in range(10):
        t0 = time.perf_counter()
        client.rebuild()
        ts.append((time.perf_counter() - t0) * 1000)
    print(f"\nfull tensor rebuild: mean {statistics.mean(ts):.1f} ms  p50 {statistics.median(ts):.1f} ms "
          f"(from {len(client.entities)} entities, {len(client.ores)} ores, {len(client.trees)} trees)")

    # --- 5. sanity checks (bring the player back to the factory first) ---
    rc.send_command("/sc local ch = game.surfaces[1].find_entities_filtered{type = \"character\"}[1] "
                    "if ch then ch.teleport({0, 0}) end rcon.print(1)")
    time.sleep(0.2)
    resp = rc.send_command("/sc obs_all_drain()") or ""
    epart, _, tpart = resp.partition("~")
    client.apply_entity(epart)
    client.apply_terrain(tpart)
    grid = client.grid
    n_in_window = sum(1 for c in client._contrib.values())
    type_sum = float(grid[0:6].sum())
    print(f"\nsanity: entity-channel sum {type_sum:.0f} vs tracked-in-window {n_in_window}"
          f" | ore cells {int((grid[C_ORE] > 0).sum())}, tree cells {int((grid[C_TREE] > 0).sum())},"
          f" water cells {int((grid[C_WATER] > 0).sum())}")
    print(f"nonzero grid values: {int((grid != 0).sum())}/{grid.size} "
          f"({100 * (grid != 0).sum() / grid.size:.1f}%)")
    n_slots = int(client.table_mask.sum())
    print(f"entity table: {n_slots}/{TABLE_ROWS} slots occupied, "
          f"vocab size {len(client._vocab)}")
    assert type_sum == n_in_window, "entity channel counts drifted from contrib map"
    assert n_slots == len(client.entities), "table occupancy drifted from entity dict"
    print("PASS: incremental tensor consistent")


if __name__ == "__main__":
    main()