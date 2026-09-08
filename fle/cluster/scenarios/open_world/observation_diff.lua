-- Tiered event-driven observation diffs.
--
-- Maintains two change buffers in storage so a client can poll game-state
-- deltas in O(changes) instead of rescanning the world:
--
--   Entity buffer (obs_diff_drain) - player-force structures as quantized
--   "rich rows". Build/mine/die/rotate events append records immediately; a
--   round-robin slice scan reconciles eventless mutations (script-set fields,
--   inventory/fuel/progress bucket transitions, entities created without
--   raise_built).
--
--   Terrain buffer (obs_terrain_drain) - static-ish world state, streamed per
--   chunk from on_chunk_generated (new chunks generate continually, so this
--   tier is event-driven too): water bitmasks, ore tiles with quantized
--   amounts, trees, rocks/cliffs, enemy structures. Ore amounts drift with no
--   events, so the reconciler also rescans one resource chunk per pass.
--
-- Hot per-tick fields use quantized change signatures (energy MJ, progress
-- deciles, log2 item counts, fluid buckets): an active factory only emits
-- records on bucket transitions, but each emitted row carries EXACT values,
-- so client snapshots are precise with staleness bounded by bucket width.
--
-- RCON API (via /sc):
--   obs_diff_full_sync()     -- entity snapshot; resets entity-tier state
--   obs_diff_drain()         -- header + entity records
--   obs_terrain_full_sync()  -- all generated chunks (expensive; mid-episode attach)
--   obs_terrain_drain()      -- terrain records
--
-- Record types (";"-joined):
--   entity buffer:  h<tick>:<research|->:<pct>  u<id>,<row>  r<id>  q<tech>
--   terrain buffer: c<cx>:<cy>:<waterhex>  o<name>:<x>:<y>:<bucket>  d<x>:<y>
--                   t<x>:<y>  k<x>:<y>  x<x>:<y>  n<id>,<name>,<x>,<y>  m<id>
--   either:         !overflow  (client must full_sync)
--
-- Row: name,x,y,direction,status followed by tagged optional fields:
--   E<joules> P<pct> R<recipe> H<health> W<tilew>:<tileh> D<dropx>:<dropy>
--   K<pickupx>:<pickupy> N<electric-network-id> T<temperature>
--   I<invidx>.<item>:<count>... F<fluid>:<amount>...
-- Rows carry exact values; emission triggers on quantized-signature change.

local RECONCILE_INTERVAL = 47 -- ticks; avoids tools' on_nth_tick(5/15/60) slots
local ENTITY_SLICE = 50 -- entities re-rowed per reconcile pass
local RES_BUCKET = 100 -- ore units per amount bucket
local RES_CHUNKS_PER_PASS = 4 -- resource chunks rescanned per reconcile pass
local DISCOVERY_EVERY = 32 -- reconcile passes between untracked-entity sweeps
local MAX_BUF = 50000 -- records; overflow => client full_sync

local WATER_TILES = { "water", "deepwater", "water-green", "deepwater-green" }

local function state()
  local s = storage.obs_diff
  if not s then
    s = {
      cache = {}, ents = {}, keys = {}, cursor = 0,
      ebuf = {}, ebuf_n = 0, tbuf = {}, tbuf_n = 0,
      res_chunks = {}, res_cursor = 0,
    }
    storage.obs_diff = s
  end
  return s
end

local function qlog(n)
  if n <= 0 then return 0 end
  return math.floor(math.log(n) / math.log(2)) + 1
end

local function push_e(s, rec)
  if s.ebuf_n >= MAX_BUF then s.ebuf[MAX_BUF] = "!overflow" return end
  s.ebuf_n = s.ebuf_n + 1
  s.ebuf[s.ebuf_n] = rec
end

local function push_t(s, rec)
  if s.tbuf_n >= MAX_BUF then s.tbuf[MAX_BUF] = "!overflow" return end
  s.tbuf_n = s.tbuf_n + 1
  s.tbuf[s.tbuf_n] = rec
end

local function rich_row(e)
  -- Returns (row, sig). The row carries EXACT values (energy in joules,
  -- progress in percent, raw item/fluid counts) so the client snapshot is
  -- precise; the sig quantizes hot fields, and only a sig change triggers
  -- emission, so drains stay sparse while transmitted values stay exact.
  local base = e.name .. "," .. e.position.x .. "," .. e.position.y .. ","
    .. (e.direction or 0) .. "," .. (e.status or 0)
  local row = { base }
  local sig = { base }
  local ok, energy = pcall(function() return e.energy end)
  if ok and energy and energy > 0 then
    row[#row + 1] = "E" .. math.floor(energy)
    sig[#sig + 1] = "E" .. math.floor(energy / 1e6)
  end
  local okp, progress = pcall(function() return e.crafting_progress end)
  if okp and progress and progress > 0 then
    row[#row + 1] = "P" .. math.floor(progress * 100)
    sig[#sig + 1] = "P" .. math.floor(progress * 10)
  end
  local okr, recipe = pcall(function() return e.get_recipe() end)
  if okr and recipe then
    row[#row + 1] = "R" .. recipe.name
    sig[#sig + 1] = "R" .. recipe.name
  end
  local okh, health = pcall(function() return e.health end)
  if okh and health then
    row[#row + 1] = "H" .. math.floor(health)
    sig[#sig + 1] = "H" .. math.floor(health / 50)
  end
  local okw, tw, th = pcall(function()
    return e.prototype.tile_width, e.prototype.tile_height
  end)
  if okw and tw then
    local dims = "W" .. tw .. ":" .. th
    row[#row + 1] = dims
    sig[#sig + 1] = dims
  end
  local okd, drop = pcall(function() return e.drop_position end)
  if okd and drop then
    local rec = "D" .. drop.x .. ":" .. drop.y
    row[#row + 1] = rec
    sig[#sig + 1] = rec
  end
  local okk, pickup = pcall(function() return e.pickup_position end)
  if okk and pickup then
    local rec = "K" .. pickup.x .. ":" .. pickup.y
    row[#row + 1] = rec
    sig[#sig + 1] = rec
  end
  local okn, netid = pcall(function() return e.electric_network_id end)
  if okn and netid then
    local rec = "N" .. netid
    row[#row + 1] = rec
    sig[#sig + 1] = rec
  end
  local okt, temp = pcall(function() return e.temperature end)
  if okt and temp then
    row[#row + 1] = "T" .. math.floor(temp)
    sig[#sig + 1] = "T" .. math.floor(temp / 25)
  end
  for idx = 1, 4 do
    local inv = e.get_inventory(idx)
    if inv then
      for _, item in ipairs(inv.get_contents()) do
        row[#row + 1] = "I" .. idx .. "." .. item.name .. ":" .. item.count
        sig[#sig + 1] = "I" .. idx .. "." .. item.name .. ":" .. qlog(item.count)
      end
    end
  end
  local okf, fb = pcall(function() return e.fluidbox end)
  if okf and fb and #fb > 0 then
    for j = 1, #fb do
      local f = fb[j]
      if f then
        row[#row + 1] = "F" .. f.name .. ":" .. math.floor(f.amount)
        sig[#sig + 1] = "F" .. f.name .. ":" .. qlog(f.amount)
      end
    end
  end
  return table.concat(row, ","), table.concat(sig, ",")
end

local function upsert(e)
  if not (e and e.valid and e.unit_number) then return end
  local s = state()
  local key = e.unit_number
  local row, sig = rich_row(e)
  if s.cache[key] ~= sig then
    s.cache[key] = sig
    s.ents[key] = e
    push_e(s, "u" .. key .. "," .. row)
  end
end

local function remove_key(s, key)
  if s.cache[key] == nil then return end
  s.cache[key] = nil
  s.ents[key] = nil
  push_e(s, "r" .. key)
end

-- Terrain helpers ------------------------------------------------------------

local function pos_key(p)
  return math.floor(p.x) .. ":" .. math.floor(p.y)
end

local function encode_chunk(surface, cx, cy, area, emit)
  local s = state()
  -- Water bitmask: 32 rows of 32 bits, hex-encoded (empty string = all land)
  local water_hex = ""
  local okw, tiles = pcall(function()
    return surface.find_tiles_filtered{ area = area, name = WATER_TILES }
  end)
  if okw and tiles and #tiles > 0 then
    local rows = {}
    for i = 0, 31 do rows[i] = 0 end
    local x0, y0 = area.left_top.x, area.left_top.y
    for i = 1, #tiles do
      local p = tiles[i].position
      local dx = math.floor(p.x) - x0
      local dy = math.floor(p.y) - y0
      if dx >= 0 and dx < 32 and dy >= 0 and dy < 32 then
        rows[dy] = bit32.bor(rows[dy], bit32.lshift(1, dx))
      end
    end
    local hex = {}
    for i = 0, 31 do hex[i + 1] = string.format("%08x", rows[i]) end
    water_hex = table.concat(hex)
  end
  emit("c" .. cx .. ":" .. cy .. ":" .. water_hex)

  -- Ore tiles: tracked for amount reconciliation
  local ores = surface.find_entities_filtered{ area = area, type = "resource" }
  if #ores > 0 then
    local cache = {}
    for i = 1, #ores do
      local o = ores[i]
      local key = pos_key(o.position)
      local bucket = math.floor(o.amount / RES_BUCKET)
      cache[key] = bucket
      emit("o" .. o.name .. ":" .. key .. ":" .. bucket)
    end
    s.res_chunks[#s.res_chunks + 1] = { area = area, cache = cache }
  end

  for _, tree in ipairs(surface.find_entities_filtered{ area = area, type = "tree" }) do
    emit("t" .. pos_key(tree.position))
  end
  for _, rock in ipairs(surface.find_entities_filtered{ area = area, type = { "simple-entity", "cliff" } }) do
    emit("k" .. pos_key(rock.position))
  end
  for _, nest in ipairs(surface.find_entities_filtered{ area = area, force = "enemy", type = { "unit-spawner", "turret" } }) do
    if nest.unit_number then
      emit("n" .. nest.unit_number .. "," .. nest.name .. ","
        .. nest.position.x .. "," .. nest.position.y)
    end
  end
end

-- Event wiring ---------------------------------------------------------------

local ev = defines.events

script.on_event(ev.on_chunk_generated, function(event)
  local s = state()
  encode_chunk(event.surface, event.position.x, event.position.y, event.area,
    function(rec) push_t(s, rec) end)
end)

for _, id in pairs({ ev.on_built_entity, ev.on_robot_built_entity,
                     ev.script_raised_built, ev.script_raised_revive }) do
  script.on_event(id, function(event) upsert(event.entity) end)
end
script.on_event(ev.on_entity_cloned, function(event) upsert(event.destination) end)
script.on_event(ev.on_player_rotated_entity, function(event) upsert(event.entity) end)

local function handle_removal(event)
  local e = event.entity
  if not (e and e.valid) then return end
  local s = state()
  local t = e.type
  if t == "tree" or t == "simple-entity" or t == "cliff" then
    push_t(s, "x" .. pos_key(e.position))
  elseif e.unit_number then
    if e.force.name == "enemy" then
      push_t(s, "m" .. e.unit_number)
    else
      remove_key(s, e.unit_number)
    end
  end
end
for _, id in pairs({ ev.on_player_mined_entity, ev.on_robot_mined_entity,
                     ev.on_entity_died, ev.script_raised_destroy }) do
  script.on_event(id, handle_removal)
end

script.on_event(ev.on_resource_depleted, function(event)
  local e = event.entity
  if e and e.valid then
    push_t(state(), "d" .. pos_key(e.position))
  end
end)

script.on_event(ev.on_research_finished, function(event)
  push_e(state(), "q" .. event.research.name)
end)

-- Reconciliation: entity slice + one resource chunk per pass ----------------

script.on_nth_tick(RECONCILE_INTERVAL, function()
  local s = state()

  -- Discovery sweep: entities created without raise_built never fire an
  -- event, so periodically scan for player entities we aren't tracking.
  s.discovery = (s.discovery or 0) + 1
  if s.discovery >= DISCOVERY_EVERY then
    s.discovery = 0
    for _, e in ipairs(game.surfaces[1].find_entities_filtered{ force = "player" }) do
      if e.unit_number and s.cache[e.unit_number] == nil then
        upsert(e)
      end
    end
  end

  for _ = 1, ENTITY_SLICE do
    s.cursor = s.cursor + 1
    if s.cursor > #s.keys then
      s.keys = {}
      for key in pairs(s.ents) do
        s.keys[#s.keys + 1] = key
      end
      s.cursor = 0
      break
    end
    local key = s.keys[s.cursor]
    local e = s.ents[key]
    if e then
      if not e.valid then
        remove_key(s, key)
      else
        local row, sig = rich_row(e)
        if s.cache[key] ~= sig then
          s.cache[key] = sig
          push_e(s, "u" .. key .. "," .. row)
        end
      end
    end
  end

  local n_chunks = #s.res_chunks
  for _ = 1, math.min(RES_CHUNKS_PER_PASS, n_chunks) do
    s.res_cursor = (s.res_cursor % n_chunks) + 1
    local rc = s.res_chunks[s.res_cursor]
    local surface = game.surfaces[1]
    local found = {}
    for _, o in ipairs(surface.find_entities_filtered{ area = rc.area, type = "resource" }) do
      local key = pos_key(o.position)
      local bucket = math.floor(o.amount / RES_BUCKET)
      found[key] = true
      if rc.cache[key] ~= bucket then
        rc.cache[key] = bucket
        push_t(s, "o" .. o.name .. ":" .. key .. ":" .. bucket)
      end
    end
    for key in pairs(rc.cache) do
      if not found[key] then
        rc.cache[key] = nil
        push_t(s, "d" .. key)
      end
    end
  end
end)

-- Drain / full sync ----------------------------------------------------------

local function header()
  local force = game.forces.player
  local research = force.current_research
  return "h" .. game.tick .. ":" .. (research and research.name or "-")
    .. ":" .. math.floor((force.research_progress or 0) * 100)
end

function obs_diff_drain()
  local s = state()
  if s.ebuf_n == 0 then
    rcon.print(header())
    return
  end
  rcon.print(header() .. ";" .. table.concat(s.ebuf, ";", 1, s.ebuf_n))
  s.ebuf = {}
  s.ebuf_n = 0
end

function obs_terrain_drain()
  local s = state()
  if s.tbuf_n == 0 then
    rcon.print("")
    return
  end
  rcon.print(table.concat(s.tbuf, ";", 1, s.tbuf_n))
  s.tbuf = {}
  s.tbuf_n = 0
end

function obs_all_drain()
  local s = state()
  local e = header()
  if s.ebuf_n > 0 then
    e = e .. ";" .. table.concat(s.ebuf, ";", 1, s.ebuf_n)
    s.ebuf = {}
    s.ebuf_n = 0
  end
  local t = ""
  if s.tbuf_n > 0 then
    t = table.concat(s.tbuf, ";", 1, s.tbuf_n)
    s.tbuf = {}
    s.tbuf_n = 0
  end
  rcon.print(e .. "~" .. t)
end

function obs_diff_full_sync()
  local s = state()
  s.cache = {}
  s.ents = {}
  s.keys = {}
  s.cursor = 0
  s.ebuf = {}
  s.ebuf_n = 0
  local out = { header() }
  local n = 1
  local ents = game.surfaces[1].find_entities_filtered{ force = "player" }
  for i = 1, #ents do
    local e = ents[i]
    local key = e.unit_number
    if key then
      local row, sig = rich_row(e)
      s.cache[key] = sig
      s.ents[key] = e
      n = n + 1
      out[n] = "u" .. key .. "," .. row
    end
  end
  rcon.print(table.concat(out, ";", 1, n))
end

function obs_terrain_full_sync()
  local s = state()
  s.res_chunks = {}
  s.res_cursor = 0
  s.tbuf = {}
  s.tbuf_n = 0
  local surface = game.surfaces[1]
  local out = {}
  local n = 0
  local function emit(rec)
    n = n + 1
    out[n] = rec
  end
  for chunk in surface.get_chunks() do
    if surface.is_chunk_generated(chunk) then
      encode_chunk(surface, chunk.x, chunk.y, chunk.area, emit)
    end
  end
  rcon.print(table.concat(out, ";", 1, n))
end