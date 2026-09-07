-- Event-driven entity observation diffs.
--
-- Maintains a change buffer in storage so a client can poll entity deltas in
-- O(changes) instead of rescanning every entity. Build/mine/die events update
-- the buffer immediately; a round-robin slice scan (RECONCILE_* below) catches
-- mutations that fire no event: script-set direction, status transitions, and
-- entities created without raise_built (e.g. place_entity's create_entity).
--
-- RCON API (via /sc):
--   obs_diff_full_sync()  -- full snapshot; resets server-side state
--   obs_diff_drain()      -- pending "u<id>,<row>" / "r<id>" records, ";"-joined
--
-- Row format: name,x,y,direction,status

local RECONCILE_INTERVAL = 47 -- ticks; avoids tools' on_nth_tick(5/15/60) slots
local RECONCILE_SLICE = 100 -- entities re-checked per interval

local function state()
  local s = storage.obs_diff
  if not s then
    s = { cache = {}, ents = {}, buf = {}, buf_n = 0, keys = {}, cursor = 0 }
    storage.obs_diff = s
  end
  return s
end

local function row_of(e)
  return e.name .. "," .. e.position.x .. "," .. e.position.y .. ","
    .. (e.direction or 0) .. "," .. (e.status or 0)
end

local function push(s, rec)
  s.buf_n = s.buf_n + 1
  s.buf[s.buf_n] = rec
end

local function upsert(e)
  if not (e and e.valid and e.unit_number) then return end
  local s = state()
  local key = e.unit_number
  local row = row_of(e)
  if s.cache[key] ~= row then
    s.cache[key] = row
    s.ents[key] = e
    push(s, "u" .. key .. "," .. row)
  end
end

local function remove_key(s, key)
  if s.cache[key] == nil then return end
  s.cache[key] = nil
  s.ents[key] = nil
  push(s, "r" .. key)
end

local function remove(e)
  if not (e and e.valid and e.unit_number) then return end
  remove_key(state(), e.unit_number)
end

local ev = defines.events
for _, id in pairs({ ev.on_built_entity, ev.on_robot_built_entity,
                     ev.script_raised_built, ev.script_raised_revive }) do
  script.on_event(id, function(event) upsert(event.entity) end)
end
script.on_event(ev.on_entity_cloned, function(event) upsert(event.destination) end)
script.on_event(ev.on_player_rotated_entity, function(event) upsert(event.entity) end)
for _, id in pairs({ ev.on_player_mined_entity, ev.on_robot_mined_entity,
                     ev.on_entity_died, ev.script_raised_destroy }) do
  script.on_event(id, function(event) remove(event.entity) end)
end

-- Round-robin reconciliation for eventless mutations. Each interval re-checks
-- up to RECONCILE_SLICE tracked entities, so drift converges within
-- (#tracked / RECONCILE_SLICE) * RECONCILE_INTERVAL ticks.
script.on_nth_tick(RECONCILE_INTERVAL, function()
  local s = state()
  for _ = 1, RECONCILE_SLICE do
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
        local row = row_of(e)
        if s.cache[key] ~= row then
          s.cache[key] = row
          push(s, "u" .. key .. "," .. row)
        end
      end
    end
  end
end)

function obs_diff_drain()
  local s = state()
  if s.buf_n == 0 then
    rcon.print("")
    return
  end
  rcon.print(table.concat(s.buf, ";", 1, s.buf_n))
  s.buf = {}
  s.buf_n = 0
end

function obs_diff_full_sync()
  local s = { cache = {}, ents = {}, buf = {}, buf_n = 0, keys = {}, cursor = 0 }
  storage.obs_diff = s
  local out = {}
  local n = 0
  local ents = game.surfaces[1].find_entities_filtered{ force = "player" }
  for i = 1, #ents do
    local e = ents[i]
    local key = e.unit_number
    if key then
      local row = row_of(e)
      s.cache[key] = row
      s.ents[key] = e
      n = n + 1
      out[n] = "u" .. key .. "," .. row
    end
  end
  rcon.print(table.concat(out, ";", 1, n))
end