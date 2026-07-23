storage.actions.objective_telemetry = function(player_index, reset)
    storage.objective_telemetry = storage.objective_telemetry or {
        deaths = {},
        death_count = 0,
        respawn_count = 0,
        resource_depletions = {},
        last_death_tick_by_agent = {},
    }

    if reset then
        storage.objective_telemetry.deaths = {}
        storage.objective_telemetry.death_count = 0
        storage.objective_telemetry.respawn_count = 0
        storage.objective_telemetry.last_respawn_tick = nil
        storage.objective_telemetry.resource_depletions = {}
        storage.objective_telemetry.last_death_tick_by_agent = {}
    end

    local character = storage.agent_characters
        and storage.agent_characters[player_index] or nil
    local surface = character and character.valid
        and character.surface or game.surfaces[1]
    local force = character and character.valid
        and character.force or game.forces.player
    local item_stats = force.get_item_production_statistics(surface)
    local fluid_stats = force.get_fluid_production_statistics(surface)
    local pollution_stats = surface.pollution_statistics

    local produced = {}
    local consumed = {}
    for name, count in pairs(item_stats.input_counts) do
        produced[name] = count
    end
    for name, count in pairs(item_stats.output_counts) do
        consumed[name] = count
    end
    for name, count in pairs(fluid_stats.input_counts) do
        produced[name] = count
    end
    for name, count in pairs(fluid_stats.output_counts) do
        consumed[name] = count
    end

    local pollution_emitted = 0
    for _, count in pairs(pollution_stats.input_counts) do
        pollution_emitted = pollution_emitted + count
    end

    return {
        tick = game.tick,
        character_alive = character ~= nil and character.valid,
        character_health = character and character.valid and character.health or nil,
        deaths = storage.objective_telemetry.deaths,
        death_count = storage.objective_telemetry.death_count or 0,
        respawn_count = storage.objective_telemetry.respawn_count or 0,
        last_respawn_tick = storage.objective_telemetry.last_respawn_tick,
        resource_depletions = storage.objective_telemetry.resource_depletions,
        pollution_total = surface.get_total_pollution(),
        pollution_emitted = pollution_emitted,
        produced = produced,
        consumed = consumed,
        rockets_launched = force.rockets_launched,
    }
end
