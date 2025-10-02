--[[
Cutscene Admin Tool — minimal runtime for Factorio 1.1.110

This runtime focuses on a small, predictable surface:
  * Python submits an ordered list of shot intents.
  * We translate the intents into Factorio cutscene waypoints verbatim.
  * Lifecycle events (started/waypoint/finished/cancelled) are recorded so the
    caller can poll for status.
  * Screenshot capture is automatically managed per cutscene plan.

Key insight: With automatic screenshot capture, the camera needs to be SMART
about positioning - get to the exact right place and zoom level where the action
is happening, then stay there to capture it effectively.

Higher-level policies (debouncing, ordering, merging) live in Python. The Lua
side deliberately avoids re-sorting or mutating the shot sequence.
]]

local CUTSCENE_VERSION = "1.1.110"


-- === Frame capture configuration =========================================
local CAPTURE_CONFIG = {
    base_dir = "cinema_seq",
    nth_ticks = 6,
    resolution = {1920, 1080},
    quality = 100,
    show_gui = false,
    use_tick_names = true,
}

local frame_capture = {
    active = false,
    player_index = nil,
    plan_label = nil,
    frame = 0,
    last_tick = 0,
    session_id = nil,
}

-- === Globals =============================================================
local function ensure_global()
    global.cinema = global.cinema or {
        version = CUTSCENE_VERSION,
        active_plan_by_player = {},
        reports_by_player = {},
        entity_cache = {},
        player_state = {}
    }
    return global.cinema
end

local function ensure_player_state(player_index)
    local g = ensure_global()
    g.player_state[player_index] = g.player_state[player_index] or {
        last_zoom = nil,
        last_position = nil,
        camera_interp = nil,
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

-- Easing and interpolation helpers for smoother camera
local function lerp(a, b, t)
    return a + (b - a) * t
end

local function ease_in_out_cubic(t)
    if t < 0.5 then
        return 4 * t * t * t
    else
        local u = -2 * t + 2
        return 1 - (u * u * u) / 2
    end
end

local function interp_vec2(a, b, t)
    return { x = lerp(a.x, b.x, t), y = lerp(a.y, b.y, t) }
end

local function compute_zoom_for_bbox(bbox, resolution)
    if not bbox then 
        if game and game.write_file then
            game.write_file("cinema_debug.log", "compute_zoom_for_bbox: no bbox provided\n", true)
        end
        return 1 
    end
    local width = math.abs(bbox[2][1] - bbox[1][1])
    local height = math.abs(bbox[2][2] - bbox[1][2])
    if width == 0 or height == 0 then 
        if game and game.write_file then
            game.write_file("cinema_debug.log", string.format("compute_zoom_for_bbox: zero dimensions width=%f height=%f\n", width, height), true)
        end
        return 1 
    end

    local res = resolution or CAPTURE_CONFIG.resolution
    local aspect = res[1] / res[2]

    local base_visible_height = 25
    local base_visible_width = base_visible_height * aspect

    -- Calculate zoom to fit the bbox in the visible area
    -- Higher zoom = more zoomed in (smaller visible area)
    -- Lower zoom = more zoomed out (larger visible area)
    local zoom_width = base_visible_width / width
    local zoom_height = base_visible_height / height
    local zoom = math.min(zoom_width, zoom_height) * 1.2

    local final_zoom = clamp_zoom(zoom)
    if game and game.write_file then
        game.write_file("cinema_debug.log", string.format("compute_zoom_for_bbox: bbox=%s, width=%f, height=%f, zoom_width=%f, zoom_height=%f, zoom=%f, final=%f\n", 
            game.table_to_json(bbox), width, height, zoom_width, zoom_height, zoom, final_zoom), true)
    end

    return final_zoom
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
        if not bbox or not bbox[1] or not bbox[2] then
            if game and game.write_file then
                game.write_file("cinema_debug.log", string.format("zoom_to_fit: invalid bbox %s\n", game.table_to_json(bbox or {})), true)
            end
            return {x = player.position.x, y = player.position.y}
        end
        local pos = {
            x = (bbox[1][1] + bbox[2][1]) / 2,
            y = (bbox[1][2] + bbox[2][2]) / 2
        }
        if game and game.write_file then
            game.write_file("cinema_debug.log", string.format("zoom_to_fit: bbox=%s, pos=%s\n", game.table_to_json(bbox), game.table_to_json(pos)), true)
        end
        return pos
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
        local fit_zoom = compute_zoom_for_bbox(kind.bbox, CAPTURE_CONFIG.resolution)
        local final_zoom = zoom or fit_zoom
        
        -- Debug logging
        if game and game.write_file then
            game.write_file("cinema_debug.log", string.format(
                "zoom_to_fit: shot_zoom=%.3f, fit_zoom=%.3f, final_zoom=%.3f, bbox=%s\n",
                zoom or 0, fit_zoom, final_zoom, 
                game.table_to_json(kind.bbox or {})
            ), true)
        end
        
        table.insert(waypoints, {
            position = pos,
            transition_time = shot.pan_ticks or ticks_from_ms(shot.pan_ms),
            time_to_wait = shot.dwell_ticks or ticks_from_ms(shot.dwell_ms),
            zoom = final_zoom
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

-- === Interpolation state ==================================================
local function resolve_wp_position(wp)
    if not wp then return nil end
    if wp.position then return { x = wp.position.x, y = wp.position.y } end
    if wp.target and wp.target.valid then
        return { x = wp.target.position.x, y = wp.target.position.y }
    end
    return nil
end

local function prime_camera_interp(player_index, plan, waypoints)
    local ps = ensure_player_state(player_index)
    local now = game.tick
    local first = waypoints[1]
    if not first then return end

    local start_pos = plan.start_position or ps.last_position
    if not start_pos then
        local p = game.get_player(player_index)
        if p and p.valid then
            start_pos = { x = p.position.x, y = p.position.y }
        else
            start_pos = resolve_wp_position(first) or { x = 0, y = 0 }
        end
    end

    local end_pos = resolve_wp_position(first) or start_pos
    local start_zoom = plan.start_zoom or ps.last_zoom or (first.zoom or 1.0)
    local end_zoom = first.zoom or start_zoom
    local seg_duration = first.transition_time or 0
    local dwell = first.time_to_wait or 0

    ps.camera_interp = {
        active = true,
        wp_index = 0, -- before first waypoint
        seg_start_tick = now,
        seg_end_tick = now + seg_duration,
        dwell_end_tick = now + seg_duration + dwell,
        start_pos = start_pos,
        end_pos = end_pos,
        start_zoom = start_zoom,
        end_zoom = end_zoom,
    }
end

-- === Validation ==========================================================
local function validate_shot_intent(shot)
    if type(shot) ~= "table" or type(shot.id) ~= "string" or type(shot.kind) ~= "table" or type(shot.kind.type) ~= "string" then
        return false, "shot must have id and kind.type"
    end

    local kind = shot.kind.type
    if kind == "focus_entity" or kind == "follow_entity" or kind == "orbit_entity" then
        if type(shot.kind.entity_uid) ~= "number" then
            return false, "entity_uid required"
        end
    elseif kind == "focus_position" then
        if type(shot.kind.pos) ~= "table" or type(shot.kind.pos[1]) ~= "number" then
            return false, "pos must be [x,y]"
        end
    elseif kind == "zoom_to_fit" then
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

    if not shot.pan_ticks or not shot.dwell_ticks then
        return false, "timing.pan and timing.dwell required"
    end

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
    frame_capture.plan_label = opts.plan_label and tostring(opts.plan_label) or nil
    frame_capture.capture_dir = opts.capture_dir or CAPTURE_CONFIG.base_dir
    frame_capture.session_id = opts.session_id or tostring(game.tick)
    frame_capture.frame = 0
    frame_capture.last_tick = 0
    
    -- Log capture start
    if game and game.write_file then
        game.write_file("cinema_capture.log", string.format("Started capture session %s for player %d\n", 
            frame_capture.session_id, frame_capture.player_index), true)
    end
end

local function stop_frame_capture()
    if not frame_capture.active then return end
    
    -- Log capture stop
    if game and game.write_file then
        game.write_file("cinema_capture.log", string.format("Stopping capture session %s (frame %d)\n", 
            frame_capture.session_id or "unknown", frame_capture.frame), true)
    end
    
    frame_capture.active = false
    frame_capture.plan_label = nil
    frame_capture.player_index = nil
    frame_capture.capture_dir = nil
    frame_capture.session_id = nil
    frame_capture.frame = 0
    frame_capture.last_tick = 0
    
    -- Safe flush with error handling
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
    if e.tick - (frame_capture.last_tick or 0) < CAPTURE_CONFIG.nth_ticks then return end
    frame_capture.last_tick = e.tick

    local p = game.get_player(frame_capture.player_index or 1)
    if not (p and p.valid) then return end
    if p.controller_type ~= defines.controllers.cutscene then return end

    local basename = string.format("%010d-%04d", e.tick, frame_capture.frame)
    if frame_capture.plan_label then
        basename = string.format("%s-%s", frame_capture.plan_label, basename)
    end

    local capture_dir = frame_capture.capture_dir or CAPTURE_CONFIG.base_dir
    local path = string.format("%s/%s.png", capture_dir, basename)
    frame_capture.frame = frame_capture.frame + 1

    -- Debug: log the path being used
    if game and game.write_file then
        game.write_file("cinema_debug.log", string.format("Screenshot path: %s (capture_dir: %s)\n", path, capture_dir), true)
    end

    -- Compute smooth camera sample (position + zoom) for this frame
    local ps = ensure_player_state(frame_capture.player_index or 1)
    local ci = ps.camera_interp

    local curr_pos
    local curr_zoom

    if ci and ci.active then
        local seg_len = math.max(0, (ci.seg_end_tick or e.tick) - (ci.seg_start_tick or e.tick))
        if seg_len > 0 and e.tick < (ci.seg_end_tick or 0) then
            -- In transition: interpolate with easing
            local t = (e.tick - (ci.seg_start_tick or e.tick)) / seg_len
            t = math.max(0, math.min(1, t))
            local te = ease_in_out_cubic(t)
            curr_pos = interp_vec2(ci.start_pos, ci.end_pos, te)
            curr_zoom = lerp(ci.start_zoom, ci.end_zoom, te)
        else
            -- In dwell or after transition
            curr_pos = { x = ci.end_pos.x, y = ci.end_pos.y }
            curr_zoom = ci.end_zoom
        end
    end

    -- Fallbacks
    if not curr_pos then
        curr_pos = ps.last_position or { x = p.position.x, y = p.position.y }
    end
    if not curr_zoom then
        curr_zoom = ps.last_zoom or p.zoom or 1.0
    end

    -- Take explicit screenshot using surface+position+zoom for deterministic capture
    game.take_screenshot{
        surface = p.surface,
        position = curr_pos,
        zoom = clamp_zoom(curr_zoom),
        path = path,
        resolution = CAPTURE_CONFIG.resolution,
        quality = CAPTURE_CONFIG.quality,
        show_gui = CAPTURE_CONFIG.show_gui,
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

    -- Prime camera interpolation so screenshots can track smooth zoom/position
    prime_camera_interp(player_index, plan, waypoints)

    -- Always stop any existing capture before starting new one
    if frame_capture.active then
        stop_frame_capture()
    end

    -- Always start capture for any plan submission
    start_frame_capture({
        player_index = player_index,
        plan_label = plan.plan_id,
        capture_dir = plan.capture_dir or CAPTURE_CONFIG.base_dir,
        session_id = plan.plan_id,
    })

    player.set_controller{
        type = defines.controllers.cutscene,
        waypoints = waypoints,
        start_position = plan.start_position,
        start_zoom = plan.start_zoom,
        final_transition_time = plan.final_transition_time,
        chart_mode_cutoff = plan.chart_mode_cutoff,
        -- skip_soft_zoom = true,
        disable_camera_movements = false,
    }

    record_event(player_index, plan.plan_id, "started", {tick = game.tick})
    ensure_player_state(player_index).last_zoom = waypoints[#waypoints].zoom
    return true
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

    -- Always stop capture when cutscene finishes
    if frame_capture.active and frame_capture.player_index == event.player_index then
        stop_frame_capture()
    end
end

local function on_cutscene_cancelled(event)
    local g = ensure_global()
    local plan = g.active_plan_by_player[event.player_index]
    if not plan then return end

    record_event(event.player_index, plan.plan_id, "cancelled", {tick = event.tick})
    g.active_plan_by_player[event.player_index] = nil
    stop_frame_capture()
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

    -- Update interpolation to the NEXT segment (wp[idx] -> wp[idx+1])
    local next_wp = plan.__compiled[idx + 2]
    local ps = ensure_player_state(event.player_index)
    if next_wp then
        local start_pos = resolve_wp_position(wp) or ps.last_position or { x = 0, y = 0 }
        local end_pos = resolve_wp_position(next_wp) or start_pos
        local start_zoom = wp.zoom or ps.last_zoom or 1.0
        local end_zoom = next_wp.zoom or start_zoom
        local seg_duration = next_wp.transition_time or 0
        local dwell = next_wp.time_to_wait or 0
        ps.camera_interp = {
            active = true,
            wp_index = idx + 1,
            seg_start_tick = event.tick,
            seg_end_tick = event.tick + seg_duration,
            dwell_end_tick = event.tick + seg_duration + dwell,
            start_pos = start_pos,
            end_pos = end_pos,
            start_zoom = start_zoom,
            end_zoom = end_zoom,
        }
    else
        -- No more segments; hold at last position/zoom
        ps.camera_interp = ps.camera_interp or {}
        ps.camera_interp.active = false
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
    -- Simplified interface: only support plan submission
    -- Cutscenes are fire-and-forget with automatic lifecycle management
    return handle_plan_submission(payload)
end

-- === Global API ===========================================================
global.actions = global.actions or {}
global.actions.cutscene = function(raw_payload)
    ensure_global()
    local payload, err = parse_payload(raw_payload)
    if not payload then
        return {ok = false, error = err}
    end
    return handle_action(payload)
end

-- Start a recording session (always captures screenshots)
global.actions.start_recording = function(raw_payload)
    ensure_global()
    local payload, err = parse_payload(raw_payload)
    if not payload then
        return {ok = false, error = err}
    end
    
    local player_index = payload.player_index or 1
    local player = game.players[player_index]
    if not (player and player.valid) then
        return {ok = false, error = "player not found"}
    end
    
    -- Stop any existing capture
    if frame_capture.active then
        stop_frame_capture()
    end
    
    -- Start new recording session
    start_frame_capture({
        player_index = player_index,
        plan_label = payload.session_id or "recording",
        capture_dir = payload.capture_dir or CAPTURE_CONFIG.base_dir,
        session_id = payload.session_id or tostring(game.tick),
    })
    
    return {ok = true, session_id = frame_capture.session_id}
end

-- Stop the current recording session
global.actions.stop_recording = function(raw_payload)
    ensure_global()
    
    if not frame_capture.active then
        return {ok = false, error = "no active recording session"}
    end
    
    local session_id = frame_capture.session_id
    stop_frame_capture()
    
    return {ok = true, session_id = session_id}
end
