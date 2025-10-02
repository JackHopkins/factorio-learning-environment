--[[
Cutscene Admin Tool — minimal runtime for Factorio 1.1.110

This runtime focuses on a small, predictable surface:
  * Python submits an ordered list of shot intents.
  * We translate the intents into Factorio cutscene waypoints verbatim.
  * Lifecycle events (started/waypoint/finished/cancelled) are recorded so the
    caller can poll for status.
  * A lightweight remote interface toggles screenshot capture on demand.

Higher-level policies (debouncing, ordering, merging) live in Python. The Lua
side deliberately avoids re-sorting or mutating the shot sequence.
]]

local serpent = serpent
local CUTSCENE_VERSION = "1.1.110"

local runtime = {
    screenshot_counter = 0
}

-- === Continuous frame capture defaults ==================================
local CAPTURE_BASE_DIR = "cinema_seq"
local CAPTURE_NTH_TICKS = 6
local CAPTURE_RESOLUTION = {1920, 1080}
local CAPTURE_QUALITY = 100
local CAPTURE_SHOW_GUI = false
local CAPTURE_USE_TICK_NAMES = true

local runtime_capture = {
    base_dir = CAPTURE_BASE_DIR,
    nth = CAPTURE_NTH_TICKS,
    resolution = CAPTURE_RESOLUTION,
    quality = CAPTURE_QUALITY,
    show_gui = CAPTURE_SHOW_GUI,
    use_tick_names = CAPTURE_USE_TICK_NAMES,
}

local frame_capture = {
    active = false,
    player_index = nil,
    nth = CAPTURE_NTH_TICKS,
    dir = CAPTURE_BASE_DIR,
    res = {CAPTURE_RESOLUTION[1], CAPTURE_RESOLUTION[2]},
    quality = CAPTURE_QUALITY,
    show_gui = CAPTURE_SHOW_GUI,
    use_tick_names = CAPTURE_USE_TICK_NAMES,
    plan_label = nil,
    frame = 0,
    last_tick = 0,
}

-- === Globals =============================================================
local function ensure_global()
    global.cinema = global.cinema or {}
    local g = global.cinema
    g.version = g.version or CUTSCENE_VERSION
    g.active_plan_by_player = g.active_plan_by_player or {}
    g.reports_by_player = g.reports_by_player or {}
    g.entity_cache = g.entity_cache or {}
    g.player_state = g.player_state or {}
    return g
end

local function ensure_player_state(player_index)
    local g = ensure_global()
    g.player_state[player_index] = g.player_state[player_index] or {
        last_zoom = nil,
        last_position = nil,
    }
    return g.player_state[player_index]
end

-- === Utility helpers =====================================================
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

    for _, player in pairs(game.players) do
        if player.valid then
            return player
        end
    end
    return nil
end

local function entity_from_uid(uid)
    if not uid then return nil end
    local g = ensure_global()
    local cache = g.entity_cache
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

local function compile_shot(player, plan, shot)
    local waypoints = {}
    local kind = shot.kind
    local zoom = shot.zoom

    if kind.type == "focus_entity" then
        local entity = entity_from_descriptor(kind)
        local transition = shot.pan_ticks or ticks_from_ms(shot.pan_ms)
        local dwell = shot.dwell_ticks or ticks_from_ms(shot.dwell_ms)
        if entity and entity.valid then
            table.insert(waypoints, {
                target = entity,
                transition_time = transition,
                time_to_wait = dwell,
                zoom = zoom
            })
        else
            local fallback = position_from_kind(player, {type = "focus_position", pos = {player.position.x, player.position.y}})
            table.insert(waypoints, {
                position = fallback,
                transition_time = transition,
                time_to_wait = dwell,
                zoom = zoom
            })
        end
    elseif kind.type == "focus_position" then
        local pos = position_from_kind(player, kind)
        table.insert(waypoints, {
            position = pos,
            transition_time = shot.pan_ticks or ticks_from_ms(shot.pan_ms),
            time_to_wait = shot.dwell_ticks or ticks_from_ms(shot.dwell_ms),
            zoom = zoom
        })
    elseif kind.type == "zoom_to_fit" then
        local pos = position_from_kind(player, kind)
        local fit_zoom = compute_zoom_for_bbox(kind.bbox, runtime_capture.resolution)
        table.insert(waypoints, {
            position = pos,
            transition_time = shot.pan_ticks or ticks_from_ms(shot.pan_ms),
            time_to_wait = shot.dwell_ticks or ticks_from_ms(shot.dwell_ms),
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
                waypoints[#waypoints].time_to_wait = shot.dwell_ticks or ticks_from_ms(shot.dwell_ms)
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
                waypoints[#waypoints].time_to_wait = shot.dwell_ticks or ticks_from_ms(shot.dwell_ms)
            end
        end
    end

    return waypoints
end

local function compile_plan(player, plan)
    local waypoints = {}
    local last_zoom = plan.start_zoom or ensure_player_state(player.index).last_zoom or player.zoom

    for _, shot in ipairs(plan.shots) do
        local shot_waypoints = compile_shot(player, plan, shot)
        for _, wp in ipairs(shot_waypoints) do
            if not wp.zoom then
                wp.zoom = last_zoom
            else
                wp.zoom = clamp_zoom(wp.zoom)
                last_zoom = wp.zoom
            end
            table.insert(waypoints, wp)
            if wp.position then
                ensure_player_state(player.index).last_position = wp.position
            elseif wp.target and wp.target.valid then
                ensure_player_state(player.index).last_position = {x = wp.target.position.x, y = wp.target.position.y}
            end
        end
    end

    return waypoints
end

-- === Validation ==========================================================
local function validate_shot_intent(shot)
    if type(shot) ~= "table" then
        return false, "shot must be table"
    end
    if type(shot.id) ~= "string" then
        return false, "shot missing id"
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

    local has_pan = shot.pan_ms or shot.pan_ticks
    local has_dwell = shot.dwell_ms or shot.dwell_ticks
    if not has_pan then return false, "timing.pan required" end
    if not has_dwell then return false, "timing.dwell required" end

    if shot.zoom and type(shot.zoom) ~= "number" then
        return false, "zoom must be number"
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
    return true
end

-- === Reporting ===========================================================
local function ensure_report(player_index, plan_id)
    local g = ensure_global()
    g.reports_by_player[player_index] = g.reports_by_player[player_index] or {}
    local reports = g.reports_by_player[player_index]

    reports[plan_id] = reports[plan_id] or {
        plan_id = plan_id,
        state = "queued",
        started_tick = nil,
        finished_tick = nil,
        cancelled_tick = nil,
        waypoints = {},
        notes = {},
    }

    return reports[plan_id]
end

local function record_event(player_index, plan_id, event_type, payload)
    local report = ensure_report(player_index, plan_id)
    payload = payload or {}

    if event_type == "started" then
        report.state = "running"
        report.started_tick = payload.tick or game.tick
    elseif event_type == "finished" then
        report.state = "finished"
        report.finished_tick = payload.tick or game.tick
    elseif event_type == "cancelled" then
        report.state = "cancelled"
        report.cancelled_tick = payload.tick or game.tick
    elseif event_type == "waypoint" then
        table.insert(report.waypoints, payload)
        return
    elseif event_type == "note" then
        table.insert(report.notes, payload)
        return
    end

    table.insert(report.notes, {type = event_type, payload = deep_copy(payload), tick = game.tick})
end

-- === Frame capture =======================================================
local function start_frame_capture(opts)
    opts = opts or {}
    frame_capture.active = true
    frame_capture.player_index = opts.player_index or frame_capture.player_index or 1
    local configured_nth = opts.nth or runtime_capture.nth or CAPTURE_NTH_TICKS
    frame_capture.nth = math.max(1, configured_nth)
    frame_capture.dir = tostring(opts.dir or runtime_capture.base_dir or CAPTURE_BASE_DIR)
    frame_capture.plan_label = opts.plan_label and tostring(opts.plan_label) or nil

    local res = opts.res or opts.resolution
    if res and res[1] and res[2] then
        frame_capture.res = {res[1], res[2]}
    else
        frame_capture.res = {
            runtime_capture.resolution[1],
            runtime_capture.resolution[2],
        }
    end

    frame_capture.quality = opts.quality or runtime_capture.quality or CAPTURE_QUALITY

    if opts.show_gui ~= nil then
        frame_capture.show_gui = opts.show_gui == true
    else
        frame_capture.show_gui = runtime_capture.show_gui
    end

    if opts.use_tick_names ~= nil then
        frame_capture.use_tick_names = opts.use_tick_names and true or false
    else
        frame_capture.use_tick_names = runtime_capture.use_tick_names
    end
    frame_capture.frame = 0
    frame_capture.last_tick = 0
end

local function stop_frame_capture()
    if not frame_capture.active then return end
    frame_capture.active = false
    frame_capture.plan_label = nil
    frame_capture.player_index = nil
    frame_capture.frame = 0
    frame_capture.last_tick = 0
    local ok, err = pcall(function()
        if game and game.set_wait_for_screenshots_to_finish then
            game.set_wait_for_screenshots_to_finish()
        end
    end)
    if not ok then
        if game and game.write_file then
            game.write_file("cinema_capture.log", "flush failed: " .. tostring(err) .. "\n", true)
        end
    end
end

script.on_nth_tick(1, function(e)
    if not frame_capture.active then return end
    if e.tick - (frame_capture.last_tick or 0) < (frame_capture.nth or 6) then return end
    frame_capture.last_tick = e.tick

    local p = game.get_player(frame_capture.player_index or 1)
    if not (p and p.valid) then return end
    if p.controller_type ~= defines.controllers.cutscene then return end

    local basename
    if frame_capture.use_tick_names then
        basename = string.format("%010d-%04d", e.tick, frame_capture.frame)
    else
        basename = string.format("%06d", frame_capture.frame)
    end

    if frame_capture.plan_label then
        basename = string.format("%s-%s", frame_capture.plan_label, basename)
    end

    local path = string.format("%s/%s.png", frame_capture.dir, basename)
    frame_capture.frame = frame_capture.frame + 1

    game.take_screenshot{
        player = p,
        by_player = p.index,
        path = path,
        resolution = {frame_capture.res[1], frame_capture.res[2]},
        quality = frame_capture.quality,
        show_gui = frame_capture.show_gui,
        force_render = true,
        allow_in_replay = true,
        wait_for_finish = false,
    }
end)

local function sanitise_plan_id(candidate)
    local id = tostring(candidate or "")
    id = id:gsub("[^%w%-%_]", "_")
    if id == "" then
        id = string.format("plan_%d", game.tick)
    end
    return id
end

local function capture_dir_for_plan(plan_id)
    local safe_id = sanitise_plan_id(plan_id)
    return string.format("%s/%s", runtime_capture.base_dir or CAPTURE_BASE_DIR, safe_id)
end

local function resolve_plan_id(plan)
    if plan.plan_id then
        return sanitise_plan_id(plan.plan_id)
    end
    return sanitise_plan_id(string.format("plan_%d", game.tick))
end

-- === Plan execution ======================================================
local function start_plan(player_index, plan)
    local g = ensure_global()
    local player = game.players[player_index]
    if not (player and player.valid) then
        return false, "player missing"
    end

    if g.active_plan_by_player[player_index] then
        return false, "plan already running"
    end

    local waypoints = compile_plan(player, plan)
    if #waypoints == 0 then
        return false, "no waypoints"
    end

    plan.plan_id = resolve_plan_id(plan)
    plan.__compiled = waypoints
    g.active_plan_by_player[player_index] = plan

    if frame_capture.active then
        stop_frame_capture()
    end

    -- Simplified capture: just enable/disable with static defaults
    if plan.capture then
        start_frame_capture({
            player_index = player_index,
            nth = runtime_capture.nth,
            dir = capture_dir_for_plan(plan.plan_id),
            res = runtime_capture.resolution,
            quality = runtime_capture.quality,
            show_gui = runtime_capture.show_gui,
            use_tick_names = runtime_capture.use_tick_names,
            plan_label = plan.plan_id,
        })
    end

    plan.capture = nil

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

    record_event(player_index, plan.plan_id, "started", {tick = game.tick})
    ensure_player_state(player_index).last_zoom = waypoints[#waypoints].zoom
    return true
end

local function cancel_active(player_index)
    local g = ensure_global()
    local plan = g.active_plan_by_player[player_index]
    if not plan then
        return {ok = false, error = "no active plan"}
    end

    local player = game.players[player_index]
    if player and player.valid then
        player.exit_cutscene()
    end

    g.active_plan_by_player[player_index] = nil
    record_event(player_index, plan.plan_id, "cancelled", {tick = game.tick})
    stop_frame_capture()
    return {ok = true, plan_id = plan.plan_id}
end

local function fetch_report(plan_id, player_index)
    local g = ensure_global()
    local reports = g.reports_by_player[player_index]
    if not reports then
        return {ok = false, error = "no reports"}
    end
    local report = reports[plan_id]
    if not report then
        return {ok = false, error = "plan not found"}
    end
    return {ok = true, report = report}
end

-- === Event handlers ======================================================
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

local function on_cutscene_started(event)
    local g = ensure_global()
    local plan = g.active_plan_by_player[event.player_index]
    if plan then
        record_event(event.player_index, plan.plan_id, "started", {tick = event.tick})
    end
end

local function on_cutscene_finished(event)
    local g = ensure_global()
    local plan = g.active_plan_by_player[event.player_index]
    if not plan then return end

    record_event(event.player_index, plan.plan_id, "finished", {tick = event.tick})
    ensure_player_state(event.player_index).last_zoom = plan.__compiled[#plan.__compiled].zoom
    ensure_player_state(event.player_index).last_position = plan.__compiled[#plan.__compiled].position
    g.active_plan_by_player[event.player_index] = nil

    if frame_capture.active and frame_capture.player_index == event.player_index then
        stop_frame_capture()
    end
end

local function on_cutscene_cancelled(event)
    cancel_active(event.player_index)
end

local function on_cutscene_waypoint(event)
    local g = ensure_global()
    local plan = g.active_plan_by_player[event.player_index]
    if not plan then return end

    local idx = normalise_waypoint_index(event)
    local wp = plan.__compiled[idx + 1]
    if not wp then return end

    if wp.target and not wp.target.valid then
        wp.target = nil
        wp.position = ensure_player_state(event.player_index).last_position or {x = 0, y = 0}
    end

    record_event(event.player_index, plan.plan_id, "waypoint", {
        index = idx,
        tick = event.tick,
    })

    if wp.position then
        ensure_player_state(event.player_index).last_position = wp.position
    elseif wp.target and wp.target.valid then
        ensure_player_state(event.player_index).last_position = {x = wp.target.position.x, y = wp.target.position.y}
    end

    if wp.zoom then
        ensure_player_state(event.player_index).last_zoom = wp.zoom
    end
end

script.on_event(defines.events.on_cutscene_started, on_cutscene_started)
script.on_event(defines.events.on_cutscene_finished, on_cutscene_finished)
script.on_event(defines.events.on_cutscene_cancelled, on_cutscene_cancelled)
script.on_event(defines.events.on_cutscene_waypoint_reached, on_cutscene_waypoint)

-- === Payload handling ====================================================
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

local function handle_plan_submission(plan)
    local ok, err = validate_plan(plan)
    if not ok then
        return {ok = false, error = err}
    end

    local player = resolve_player(plan.player)
    if not player then
        return {ok = false, error = "player not found"}
    end

    plan.plan_id = resolve_plan_id(plan)
    local started, reason = start_plan(player.index, plan)
    if not started then
        return {ok = false, error = reason}
    end

    return {ok = true, plan_id = plan.plan_id, started = true}
end

local function handle_action(payload)
    local mode = payload.mode or "play"
    if mode == "play" or mode == "queue" then
        return handle_plan_submission(payload)
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
    end
    return {ok = false, error = "unknown mode"}
end

global.actions = global.actions or {}
global.actions.cutscene = function(raw_payload)
    ensure_global()
    local payload, err = parse_payload(raw_payload)
    if not payload then
        return {ok = false, error = err}
    end
    return handle_action(payload)
end

-- === Remote interface ====================================================
local function _register_cinema_interfaces()
    pcall(function() remote.remove_interface("cinema_capture") end)
    remote.add_interface("cinema_capture", {
        start = function(opts)
            start_frame_capture(opts or {})
            return {ok = true}
        end,
        stop = function()
            stop_frame_capture()
            return {ok = true}
        end,
        status = function()
            return {
                active = frame_capture.active,
                player_index = frame_capture.player_index,
                frame = frame_capture.frame,
            }
        end,
    })

    pcall(function() remote.remove_interface("cinema_admin") end)
    remote.add_interface("cinema_admin", {
        rehook = function()
            _register_cinema_interfaces()
            return {ok = true, tick = game.tick}
        end,
        ping = function()
            return {version = CUTSCENE_VERSION, tick = game.tick, active = frame_capture.active}
        end,
    })
end

_register_cinema_interfaces()
