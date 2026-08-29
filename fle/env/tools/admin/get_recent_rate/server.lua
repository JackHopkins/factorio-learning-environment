-- Return a normalized recent production rate without serializing all force
-- statistics. Manual harvest/craft events are removed from the detector rate.

local PRECISIONS = {
    {seconds = 5, index = defines.flow_precision_index.five_seconds},
    {seconds = 60, index = defines.flow_precision_index.one_minute},
    {seconds = 600, index = defines.flow_precision_index.ten_minutes},
    {seconds = 3600, index = defines.flow_precision_index.one_hour},
}

local function choose_precision(window_seconds)
    for _, precision in ipairs(PRECISIONS) do
        if window_seconds <= precision.seconds then
            return precision
        end
    end
    return PRECISIONS[#PRECISIONS]
end

storage.actions.get_recent_rate = function(player_index, item_name, window_seconds)
    if type(item_name) ~= "string" or item_name == "" then
        return {error = "item_name must be a non-empty string"}
    end
    window_seconds = math.max(1, math.min(tonumber(window_seconds) or 5, 3600))
    local precision = choose_precision(window_seconds)
    local effective_seconds = precision.seconds
    local force = game.forces.player
    local surface = game.surfaces[1]
    local stats = force.get_item_production_statistics(surface)
    local total_per_minute = stats.get_flow_count({
        name = item_name,
        category = "input",
        precision_index = precision.index,
        count = false,
    }) or 0

    local cutoff_tick = game.tick - effective_seconds * 60
    -- Keep enough history for a later long-window query. This endpoint is
    -- called for both 60s and 300s context fields; pruning to the current
    -- short window would make the next 300s query lose older manual events
    -- and reintroduce them as false automated production.
    local retention_cutoff_tick = game.tick - 3600 * 60
    local manual_count = 0
    local retained = {}
    storage.manual_production_events = storage.manual_production_events or {}
    for _, event in ipairs(storage.manual_production_events) do
        if event.tick >= retention_cutoff_tick then
            table.insert(retained, event)
            if event.tick >= cutoff_tick then
                manual_count = manual_count + ((event.outputs or {})[item_name] or 0)
            end
        end
    end
    storage.manual_production_events = retained

    total_per_minute = math.max(total_per_minute, 0)
    local manual_per_minute = manual_count / effective_seconds * 60
    return {
        item_name = item_name,
        requested_window_seconds = window_seconds,
        effective_window_seconds = effective_seconds,
        total_per_minute = total_per_minute,
        manual_per_minute = manual_per_minute,
        dynamic_per_minute = math.max(total_per_minute - manual_per_minute, 0),
        observed_at_tick = game.tick,
    }
end
