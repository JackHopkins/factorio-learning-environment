--[[
Cutscene Admin Tool wiring (Phase 0 discovery)

- During instance bootstrap `LuaScriptManager.load_tool_into_game("cutscene")` loads this file,
  registering `global.actions.cutscene` in Factorio's runtime alongside the other admin tools.
- Python callers will mirror the existing reset tool: `Controller.execute(...)` wraps a
  `/silent-command` that invokes `global.actions.cutscene(plan_json, ...)`.  Via
  `FactorioInstance.lua_script_manager.setup_tools` the admin controller is exposed on each
  namespace as `_cutscene(...)`, so CLI/tests can trigger plans with
  `instance.first_namespace._cutscene(plan_payload)`.
- Replay pipelines already in FLE (e.g. `fle.eval.analysis.run_to_mp4`) drive programs through a
  gym environment; Phase 3 will submit generated shot plans through the same `_cutscene`
  controller while the Factorio runtime executes replays.

Implementation note: this stub will be replaced with the full Cutscene action in Phase 1,
including payload validation, waypoint compilation, and lifecycle hooks per `cinema.md`.
]]

local serpent = serpent
local CAPTURE_PATH_PREFIX = "cinema"
local CUTSCENE_VERSION = "1.1.110"

local DEFAULT_CAPTURE = {
    cadence = "once"
}

local DEFAULT_CAPTURE_GLOBALS = {
    resolution = {1920, 1080},
    show_gui = false,
    quality = 100,
    wait_for_finish = false
}

local runtime = {
    screenshot_counter = 0
}

local DEFAULT_COOLDOWN_TICKS = 120
local MERGE_WINDOW_TICKS = 30
local ENTITY_INVALIDATION_EVENTS = {
    defines.events.on_entity_died,
    defines.events.on_player_mined_entity,
    defines.events.on_robot_mined_entity,
    defines.events.script_raised_destroy,
}

local Runtime = {}

local function ensure_global()
    global.cinema = global.cinema or {}
    local g = global.cinema

    g.version = g.version or CUTSCENE_VERSION
    g.capture_defaults = g.capture_defaults or DEFAULT_CAPTURE_GLOBALS
    g.plans_by_player = g.plans_by_player or {}
    g.queue_by_player = g.queue_by_player or {}
    g.active_plan_by_player = g.active_plan_by_player or {}
    g.reports_by_player = g.reports_by_player or {}
    g.waypoint_captures = g.waypoint_captures or {}
    g.entity_cache = g.entity_cache or {}
    g.player_state = g.player_state or {}
end

local function deep_copy(value)
    if type(value) ~= "table" then return value end
    local copy = {}
    for k, v in pairs(value) do
        copy[k] = deep_copy(v)
    end
    return copy
end

local function ticks_from_ms(ms)
    if not ms then return 0 end
    return math.floor((ms / 1000) * 60)
end

local function clamp_zoom(z)
    if not z then return z end
    if z < 0.05 then return 0.05 end
    if z > 4.0 then return 4.0 end
    return z
end

local function compute_zoom_for_bbox(bbox, resolution)
    if not bbox then return 1 end
    local width = math.abs(bbox[2][1] - bbox[1][1])
    local height = math.abs(bbox[2][2] - bbox[1][2])
    if width == 0 or height == 0 then return 1 end

    local res_x = resolution and resolution[1] or 1920
    local res_y = resolution and resolution[2] or 1080
    local aspect = res_x / res_y

    local base_visible_height = 25
    local base_visible_width = base_visible_height * aspect

    local zoom_width = base_visible_width / (width + 10)
    local zoom_height = base_visible_height / (height + 10)
    local zoom = math.min(zoom_width, zoom_height) * 1.2

    return clamp_zoom(zoom)
end

local function resolve_player(player_ref)
    if type(player_ref) == "number" then
        return game.players[player_ref]
    elseif type(player_ref) == "string" then
        local idx = tonumber(player_ref)
        if idx and game.players[idx] then
            return game.players[idx]
        end
        for _, player in pairs(game.players) do
            if player.name == player_ref then
                return player
            end
        end
    end

    -- Fallback to first connected player
    for _, player in pairs(game.players) do
        if player and player.valid then
            return player
        end
    end
    return nil
end

local function entity_from_uid(uid)
    if not uid then return nil end

    ensure_global()
    local cache = global.cinema.entity_cache
    local cached = cache[uid]
    if cached and cached.valid then
        return cached
    end
    cache[uid] = nil

    for _, surface in pairs(game.surfaces) do
        local entities = surface.find_entities()
        for _, ent in pairs(entities) do
            if ent.unit_number == uid then
                cache[uid] = ent
                return ent
            end
        end
    end

    return nil
end

local function entity_from_descriptor(kind)
    if kind.entity_uid then
        local ent = entity_from_uid(kind.entity_uid)
        if ent then return ent end
    end

    if kind.lookup then
        local surface = game.surfaces[kind.lookup.surface or 1]
        if surface and kind.lookup.name and kind.lookup.position then
            local position = kind.lookup.position
            if position[1] and position[2] then
                position = {x = position[1], y = position[2]}
            end
            local found = surface.find_entities_filtered{
                name = kind.lookup.name,
                position = position,
                radius = kind.lookup.radius or 1,
                limit = 1,
            }
            if found and found[1] and found[1].valid then
                return found[1]
            end
        end
    end

    return nil
end

local function position_from_kind(player, kind)
    if kind.type == "focus_position" then
        return {x = kind.pos[1], y = kind.pos[2]}
    elseif kind.type == "focus_entity" or kind.type == "follow_entity" or kind.type == "orbit_entity" then
    local entity = entity_from_descriptor(kind)
        if entity and entity.valid then
            return {x = entity.position.x, y = entity.position.y}
        end
    elseif kind.type == "zoom_to_fit" then
        local bbox = kind.bbox
        return {
            x = (bbox[1][1] + bbox[2][1]) / 2,
            y = (bbox[1][2] + bbox[2][2]) / 2
        }
    end
    return {x = player.position.x, y = player.position.y}
end

local function build_follow_segment(entity, duration_ms)
    local waypoints = {}
    local ticks_total = ticks_from_ms(duration_ms)
    if ticks_total <= 0 then return waypoints end

    local step = math.max(1, math.floor(60 / 12))
    for elapsed = 0, ticks_total, step do
        if not entity.valid then break end
        table.insert(waypoints, {
            position = {x = entity.position.x, y = entity.position.y},
            transition_time = step,
            time_to_wait = 0
        })
    end

    return waypoints
end

local function build_orbit_segment(entity, duration_ms, radius_tiles, degrees)
    local waypoints = {}
    local total_ticks = ticks_from_ms(duration_ms)
    if total_ticks <= 0 then return waypoints end

    local step = math.max(1, math.floor(60 / 12))
    local samples = math.max(2, math.floor(total_ticks / step))
    local radians_per_sample = math.rad(degrees) / (samples - 1)

    for idx = 0, samples - 1 do
        if not entity.valid then break end
        local angle = radians_per_sample * idx
        table.insert(waypoints, {
            position = {
                x = entity.position.x + radius_tiles * math.cos(angle),
                y = entity.position.y + radius_tiles * math.sin(angle)
            },
            transition_time = step,
            time_to_wait = 0
        })
    end

    return waypoints
end

local function append_capture_to_waypoints(waypoints, capture)
    if not capture then return waypoints end
    for _, wp in ipairs(waypoints) do
        wp.capture = capture
    end
    return waypoints
end

local function compile_shot(player, plan, shot, defaults)
    local waypoints = {}
    local kind = shot.kind
    local capture = shot.capture or defaults.capture
    local zoom = shot.zoom

    -- Prefer explicit tick fields for timing if present (pan_ticks, dwell_ticks)
    if kind.type == "focus_entity" then
        local entity = entity_from_descriptor(kind)
        if entity and entity.valid then
            table.insert(waypoints, {
                target = entity,
                transition_time = (shot.pan_ticks or ticks_from_ms(shot.pan_ms)),
                time_to_wait = (shot.dwell_ticks or ticks_from_ms(shot.dwell_ms)),
                zoom = zoom
            })
        else
            local fallback = position_from_kind(player, {type = "focus_position", pos = {player.position.x, player.position.y}})
            table.insert(waypoints, {
                position = fallback,
                transition_time = (shot.pan_ticks or ticks_from_ms(shot.pan_ms)),
                time_to_wait = (shot.dwell_ticks or ticks_from_ms(shot.dwell_ms)),
                zoom = zoom
            })
        end
    elseif kind.type == "focus_position" then
        local pos = position_from_kind(player, kind)
        table.insert(waypoints, {
            position = pos,
            transition_time = (shot.pan_ticks or ticks_from_ms(shot.pan_ms)),
            time_to_wait = (shot.dwell_ticks or ticks_from_ms(shot.dwell_ms)),
            zoom = zoom
        })
    elseif kind.type == "zoom_to_fit" then
        local pos = position_from_kind(player, kind)
        local fit_zoom = compute_zoom_for_bbox(kind.bbox, plan.capture_defaults and plan.capture_defaults.resolution)
        table.insert(waypoints, {
            position = pos,
            transition_time = (shot.pan_ticks or ticks_from_ms(shot.pan_ms)),
            time_to_wait = (shot.dwell_ticks or ticks_from_ms(shot.dwell_ms)),
            zoom = zoom or fit_zoom
        })
    elseif kind.type == "follow_entity" then
        local entity = entity_from_descriptor(kind)
        if entity and entity.valid then
            waypoints = build_follow_segment(entity, kind.duration_ms)
            if zoom then
                for _, wp in ipairs(waypoints) do
                    wp.zoom = zoom
                end
            end
            if #waypoints > 0 then
                -- Prefer explicit dwell_ticks if present
                waypoints[#waypoints].time_to_wait = (shot.dwell_ticks or ticks_from_ms(shot.dwell_ms))
            end
        end
    elseif kind.type == "orbit_entity" then
        local entity = entity_from_descriptor(kind)
        if entity and entity.valid then
            waypoints = build_orbit_segment(entity, kind.duration_ms, kind.radius_tiles, kind.degrees)
            if zoom then
                for _, wp in ipairs(waypoints) do
                    wp.zoom = zoom
                end
            end
            if #waypoints > 0 then
                waypoints[#waypoints].time_to_wait = (shot.dwell_ticks or ticks_from_ms(shot.dwell_ms))
            end
        end
    end

    append_capture_to_waypoints(waypoints, capture)
    return waypoints
end

local function compile_plan(player, plan)
    local waypoints = {}
    local defaults = {capture = plan.capture_defaults or DEFAULT_CAPTURE}

    -- Sort shots by sequence number if present, otherwise by insertion order
    table.sort(plan.shots, function(a, b)
        local seq_a = a.seq or a._seq or 0
        local seq_b = b.seq or b._seq or 0
        if seq_a == seq_b then
            return (a.pri or 0) > (b.pri or 0)
        end
        return seq_a < seq_b
    end)

    local state = Runtime.ensure_player_state(player.index)
    state.pending_segments = {}
    for _, shot in ipairs(plan.shots) do
        Runtime.merge_with_previous(state, shot)
    end

    local merged_shots = state.pending_segments

    local last_zoom = plan.start_zoom or state.last_zoom or player.zoom
    for _, shot in ipairs(merged_shots) do
        local shot_waypoints = compile_shot(player, plan, shot, defaults)
        for _, wp in ipairs(shot_waypoints) do
            if not wp.zoom then
                wp.zoom = last_zoom
            else
                last_zoom = wp.zoom
            end
            table.insert(waypoints, wp)
        end
    end

    return waypoints
end

local function validate_shot_intent(shot)
    if type(shot) ~= "table" then
        return false, "shot must be table"
    end
    if type(shot.id) ~= "string" then
        return false, "shot missing id"
    end
    if shot.when and shot.when.start_tick and type(shot.when.start_tick) ~= "number" then
        return false, "when.start_tick must be number if present"
    end
    -- Either pan_ms/pan_ticks must be provided
    if shot.pan_ms and type(shot.pan_ms) ~= "number" then
        return false, "pan_ms must be number if present"
    end
    if shot.pan_ticks and type(shot.pan_ticks) ~= "number" then
        return false, "pan_ticks must be number if present"
    end
    if not shot.pan_ms and not shot.pan_ticks then
        return false, "either pan_ms or pan_ticks must be provided"
    end
    
    -- Either dwell_ms/dwell_ticks must be provided
    if shot.dwell_ms and type(shot.dwell_ms) ~= "number" then
        return false, "dwell_ms must be number if present"
    end
    if shot.dwell_ticks and type(shot.dwell_ticks) ~= "number" then
        return false, "dwell_ticks must be number if present"
    end
    if not shot.dwell_ms and not shot.dwell_ticks then
        return false, "either dwell_ms or dwell_ticks must be provided"
    end
    if shot.zoom and type(shot.zoom) ~= "number" then
        return false, "zoom must be number"
    end
    if type(shot.kind) ~= "table" or type(shot.kind.type) ~= "string" then
        return false, "kind.type required"
    end

    local kind = shot.kind.type
    if kind == "focus_entity" or kind == "follow_entity" or kind == "orbit_entity" then
        if type(shot.kind.entity_uid) ~= "number" then
            return false, "entity_uid required"
        end
    end
    if kind == "focus_position" then
        if type(shot.kind.pos) ~= "table" or type(shot.kind.pos[1]) ~= "number" then
            return false, "pos must be [x,y]"
        end
    end
    if kind == "zoom_to_fit" then
        if type(shot.kind.bbox) ~= "table" then
            return false, "bbox required"
        end
    end
    if (kind == "follow_entity" or kind == "orbit_entity") and (type(shot.kind.duration_ms) ~= "number" or shot.kind.duration_ms <= 0) then
        return false, "duration_ms required"
    end
    if kind == "orbit_entity" and (type(shot.kind.radius_tiles) ~= "number" or type(shot.kind.degrees) ~= "number") then
        return false, "orbit requires radius_tiles and degrees"
    end

    if shot.capture ~= nil then
        if type(shot.capture) ~= "table" then
            return false, "capture must be object"
        end
        if shot.capture.cadence and type(shot.capture.cadence) ~= "string" then
            return false, "capture cadence must be string"
        end
        if shot.capture.n_ticks and type(shot.capture.n_ticks) ~= "number" then
            return false, "capture n_ticks must be number"
        end
    end

    return true
end

local function validate_plan(plan)
    if type(plan) ~= "table" then
        return false, "payload must be table"
    end
    if plan.player == nil then
        return false, "player required"
    end
    if type(plan.shots) ~= "table" or #plan.shots == 0 then
        return false, "shots must be non-empty array"
    end

    for _, shot in ipairs(plan.shots) do
        local ok, err = validate_shot_intent(shot)
        if not ok then
            return false, string.format("shot %s invalid: %s", shot.id or "<unknown>", err)
        end
    end

    if plan.capture_defaults and type(plan.capture_defaults) ~= "table" then
        return false, "capture_defaults must be table"
    end

    return true
end

local function record_event(player_index, plan_id, event_type, payload)
    ensure_global()
    local reports = global.cinema.reports_by_player
    reports[player_index] = reports[player_index] or {}
    reports[player_index][plan_id] = reports[player_index][plan_id] or {
        plan_id = plan_id,
        player = player_index,
        started_tick = nil,
        finished = false,
        cancelled = false,
        waypoints = {},
        notes = {}
    }
    local report = reports[player_index][plan_id]

    if event_type == "started" then
        report.started_tick = payload.tick
    elseif event_type == "finished" then
        report.finished = true
    elseif event_type == "cancelled" then
        report.cancelled = true
    elseif event_type == "waypoint" then
        table.insert(report.waypoints, payload)
    elseif event_type == "note" then
        table.insert(report.notes, payload)
    end
end

local function handle_capture(player_index, plan_id, waypoint_index, waypoint, capture_defaults)
    local capture = waypoint.capture
    if not capture then return nil end

    local player = game.players[player_index]
    if not player or not player.valid then return nil end

    local defaults = capture_defaults or DEFAULT_CAPTURE_GLOBALS
    local resolution = defaults.resolution or DEFAULT_CAPTURE_GLOBALS.resolution
    local quality = defaults.quality or DEFAULT_CAPTURE_GLOBALS.quality
    local show_gui = defaults.show_gui

    local path = string.format("%s/%s/%06d.png", CAPTURE_PATH_PREFIX, plan_id or "plan", runtime.screenshot_counter)
    runtime.screenshot_counter = runtime.screenshot_counter + 1

    local position = waypoint.position
    if waypoint.target and waypoint.target.valid then
        position = waypoint.target.position
    end

    local params = {
        player = player.index,
        resolution = {resolution[1], resolution[2]},
        zoom = waypoint.zoom,
        show_gui = show_gui,
        quality = quality,
        path = path,
        force_render = true,
        allow_in_replay = true,
    }

    if position then
        params.position = position
    end

    game.take_screenshot(params)
    return path
end

local function start_plan(player_index, plan)
    ensure_global()
    local player = game.players[player_index]
    if not player then
        return false, "player missing"
    end

    local waypoints = compile_plan(player, plan)
    if #waypoints == 0 then
        return false, "no waypoints"
    end

    plan.__compiled = waypoints
    global.cinema.active_plan_by_player[player_index] = plan

    player.set_controller{
        type = defines.controllers.cutscene,
        waypoints = waypoints,
        start_position = plan.start_position,
        start_zoom = plan.start_zoom,
        final_transition_time = plan.final_transition_time,
        chart_mode_cutoff = plan.chart_mode_cutoff,
        skip_soft_zoom = true,
        disable_camera_movements = false,
    }

    record_event(player_index, plan.plan_id or ("plan-" .. game.tick), "started", {tick = game.tick})
    Runtime.remember_view(player_index, waypoints[#waypoints])
    Runtime.set_cooldown(player_index)
    return true
end


local MinimalQueue = {}
MinimalQueue.__index = MinimalQueue

function MinimalQueue.new()
    return setmetatable({items = {}, active = nil, started_tick = nil}, MinimalQueue)
end

function MinimalQueue:push(plan)
    table.insert(self.items, plan)
end

function MinimalQueue:pop()
    if #self.items == 0 then return nil end
    return table.remove(self.items, 1)
end

function MinimalQueue:peek()
    return self.items[1]
end

function MinimalQueue:set_active(plan)
    self.active = plan
    self.started_tick = plan and plan.plan.start_tick or game.tick
end

function MinimalQueue:is_idle()
    return self.active == nil
end

local function ensure_queue(player_index)
    ensure_global()
    local queue = global.cinema.queue_by_player[player_index]
    if not queue or getmetatable(queue) ~= MinimalQueue then
        queue = MinimalQueue.new()
        global.cinema.queue_by_player[player_index] = queue
    end
    return queue
end


local function enqueue_plan(player_index, plan)
    local queue = ensure_queue(player_index)
    queue:push({
        plan = plan,
        enqueued_tick = game.tick,
    })

    if not global.cinema.active_plan_by_player[player_index] and Runtime.cooldown_ready(player_index) then
        local candidate = queue:pop()
        if candidate then
            local ok, err = start_plan(player_index, candidate.plan)
            if not ok then
                return false, err
            end
            queue:set_active(candidate)
            return true, nil
        end
    end

    return true, nil
end

local function poll_queue(player_index)
    ensure_global()
    local queue = global.cinema.queue_by_player[player_index]
    if not queue or #queue == 0 then
        return nil
    end
    return table.remove(queue, 1)
end

local function tick_worker()
    ensure_global()
    for player_index, queue in pairs(global.cinema.queue_by_player) do
        queue = ensure_queue(player_index)
        if queue:peek() then
            local player = game.players[player_index]
            if player and player.valid then
                local active = global.cinema.active_plan_by_player[player_index]
                if not active and Runtime.cooldown_ready(player_index) then
                    local next_entry = queue:pop()
                    if next_entry then
                        local ok, err = start_plan(player_index, next_entry.plan)
                        if ok then
                            queue:set_active(next_entry)
                        else
                            record_event(player_index, next_entry.plan.plan_id or ("plan-" .. game.tick), "note", {tick = game.tick, message = err})
                        end
                    end
                end
            end
        end
    end
end

script.on_event(defines.events.on_tick, tick_worker)

local function on_cutscene_started(event)
    record_event(event.player_index, "cutscene", "started", {tick = event.tick})
end

local function on_cutscene_finished(event)
    ensure_global()
    local plan = global.cinema.active_plan_by_player[event.player_index]
    if plan then
        record_event(event.player_index, plan.plan_id or ("plan-" .. event.tick), "finished", {tick = event.tick})
        global.cinema.active_plan_by_player[event.player_index] = nil
        Runtime.remember_view(event.player_index, {zoom = plan.__compiled[#plan.__compiled].zoom, position = plan.__compiled[#plan.__compiled].position})
        Runtime.set_cooldown(event.player_index)
        local queue = ensure_queue(event.player_index)
        queue:set_active(nil)
        -- Attempt to start the next queued plan immediately (without waiting for tick worker)
        local next_entry = queue:pop()
        if next_entry and Runtime.cooldown_ready(event.player_index) then
            local ok2, err2 = start_plan(event.player_index, next_entry.plan)
            if ok2 then
                queue:set_active(next_entry)
            else
                record_event(event.player_index, next_entry.plan.plan_id or ("plan-" .. event.tick), "note", {tick = event.tick, message = err2 or "failed to start next plan"})
            end
        end
    end
end

local function on_cutscene_cancelled(event)
    ensure_global()
    local plan = global.cinema.active_plan_by_player[event.player_index]
    if plan then
        record_event(event.player_index, plan.plan_id or ("plan-" .. event.tick), "cancelled", {tick = event.tick})
        global.cinema.active_plan_by_player[event.player_index] = nil
        Runtime.set_cooldown(event.player_index)
        ensure_queue(event.player_index):set_active(nil)
    end
end

local function normalise_waypoint_index(event)
    if event.waypoint_index ~= nil then
        return event.waypoint_index
    end
    if event.waypoint_index_1 ~= nil then
        return event.waypoint_index_1
    end
    if event.waypoint_index_0 ~= nil then
        return event.waypoint_index_0
    end
    return 0
end

local function on_cutscene_waypoint(event)
    ensure_global()
    local plan = global.cinema.active_plan_by_player[event.player_index]
    if not plan then
        return
    end

    local idx = normalise_waypoint_index(event)
    local wp = plan.__compiled[idx + 1]
    if not wp then
        return
    end

    if wp.target and (not wp.target.valid) then
        wp.target = nil
        wp.position = Runtime.ensure_player_state(event.player_index).last_position or {x = 0, y = 0}
    end

    local capture_defaults = plan.capture_defaults or global.cinema.capture_defaults
    local path = handle_capture(event.player_index, plan.plan_id, idx, wp, capture_defaults)

    record_event(event.player_index, plan.plan_id or ("plan-" .. event.tick), "waypoint", {
        index = idx,
        tick = event.tick,
        captured = path and {path} or {}
    })

    Runtime.remember_view(event.player_index, wp)
end

script.on_event(defines.events.on_cutscene_started, on_cutscene_started)
script.on_event(defines.events.on_cutscene_finished, on_cutscene_finished)
script.on_event(defines.events.on_cutscene_cancelled, on_cutscene_cancelled)
script.on_event(defines.events.on_cutscene_waypoint_reached, on_cutscene_waypoint)

local function parse_payload(payload)
    if type(payload) == "table" then
        return payload
    elseif type(payload) == "string" then
        local ok, result = pcall(function()
            return game.json_to_table(payload)
        end)
        if not ok then
            return nil, "invalid JSON"
        end
        return result
    else
        return nil, "payload must be table or JSON"
    end
end

local function resolve_plan_id(plan)
    if plan.plan_id then
        return plan.plan_id
    end
    return string.format("plan_%d", game.tick)
end

local function queue_plan(plan)
    local player = resolve_player(plan.player)
    if not player then
        return {ok = false, error = "player not found"}
    end

    local plan_id = resolve_plan_id(plan)
    plan.plan_id = plan_id

    local ok, err = enqueue_plan(player.index, plan)
    if not ok then
        return {ok = false, error = err or "failed to start plan"}
    end

    return {ok = true, plan_id = plan_id, queued = true}
end

local function fetch_report(plan_id, player_index)
    ensure_global()
    local reports = global.cinema.reports_by_player[player_index]
    if not reports then return {ok = false, error = "no reports"} end
    local report = reports[plan_id]
    if not report then return {ok = false, error = "plan not found"} end
    return {ok = true, report = report}
end

local function cancel_active(player_index)
    ensure_global()
    local plan = global.cinema.active_plan_by_player[player_index]
    if not plan then
        return {ok = false, error = "no active plan"}
    end

    local player = game.players[player_index]
    if player and player.valid then
        player.exit_cutscene()
        record_event(player_index, plan.plan_id, "cancelled", {tick = game.tick})
    end
    global.cinema.active_plan_by_player[player_index] = nil
    return {ok = true}
end


local function dump_table(tbl)
    return serpent.line(tbl, {comment = false})
end

local function handle_action(payload)
    local mode = payload.mode or "queue"

    if mode == "queue" then
        local plan = payload
        local ok, err = validate_plan(plan)
        if not ok then
            return {ok = false, error = err}
        end
        return queue_plan(plan)
    elseif mode == "report" then
        if not payload.plan_id or not payload.player then
            return {ok = false, error = "plan_id and player required"}
        end
        local player = resolve_player(payload.player)
        if not player then
            return {ok = false, error = "player not found"}
        end
        return fetch_report(payload.plan_id, player.index)
    elseif mode == "cancel" then
        local player = resolve_player(payload.player)
        if not player then
            return {ok = false, error = "player not found"}
        end
        return cancel_active(player.index)
    else
        return {ok = false, error = "unknown mode"}
    end
end

global.actions.cutscene = function(raw_payload)
    ensure_global()
    local payload, err = parse_payload(raw_payload)
    if not payload then
        return {ok = false, error = err}
    end

    local result = handle_action(payload)
    return result
end

local function ensure_player_state(player_index)
    ensure_global()
    local g = global.cinema
    g.player_state[player_index] = g.player_state[player_index] or {
        cooldown_until = 0,
        last_zoom = nil,
        last_position = nil,
        pending_segments = {},
    }
    return g.player_state[player_index]
end

local function set_cooldown(player_index)
    local state = ensure_player_state(player_index)
    state.cooldown_until = game.tick + DEFAULT_COOLDOWN_TICKS
end

local function cooldown_ready(player_index)
    local state = ensure_player_state(player_index)
    return game.tick >= (state.cooldown_until or 0)
end

local function remember_view(player_index, waypoint)
    local state = ensure_player_state(player_index)
    if waypoint.position then
        state.last_position = waypoint.position
    end
    if waypoint.zoom then
        state.last_zoom = waypoint.zoom
    end
end

local function merge_with_previous(state, shot)
    -- Simple implementation - just add to pending segments
    table.insert(state.pending_segments, shot)
end

local function record_event(player_index, plan_id, event_type, payload)
    ensure_global()
    local g = global.cinema
    g.reports_by_player[player_index] = g.reports_by_player[player_index] or {}
    local reports = g.reports_by_player[player_index]
    reports[plan_id] = reports[plan_id] or {
        events = {},
        state = "queued"
    }
    
    local report = reports[plan_id]
    table.insert(report.events, {
        type = event_type,
        tick = game.tick,
        payload = payload or {}
    })
    
    if event_type == "started" then
        report.state = "running"
    elseif event_type == "finished" or event_type == "cancelled" then
        report.state = event_type
    end
end

-- Removed duplicate stubbed implementations - proper implementations exist above

-- Runtime function assignments
Runtime.ensure_player_state = ensure_player_state
Runtime.cooldown_ready = cooldown_ready
Runtime.set_cooldown = set_cooldown
Runtime.remember_view = remember_view
Runtime.merge_with_previous = merge_with_previous

local function on_entity_invalidated(event)
    ensure_global()
    for player_index, plan in pairs(global.cinema.active_plan_by_player) do
        if plan and plan.__compiled then
            for _, wp in ipairs(plan.__compiled) do
                if wp.target and wp.target == event.entity then
                    wp.target = nil
                    wp.position = Runtime.ensure_player_state(player_index).last_position or {x = event.entity.position.x, y = event.entity.position.y}
                end
            end
        end
    end
end

for _, ev in ipairs(ENTITY_INVALIDATION_EVENTS) do
    script.on_event(ev, on_entity_invalidated)
end


