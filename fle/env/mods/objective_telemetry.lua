storage.objective_telemetry = storage.objective_telemetry or {
    deaths = {},
    death_count = 0,
    respawn_count = 0,
    resource_depletions = {},
    last_death_tick_by_agent = {},
}

local function entity_summary(entity)
    if not entity or not entity.valid then
        return nil
    end
    local summary = {
        name = entity.name,
        type = entity.type,
        unit_number = entity.unit_number,
        position = {x = entity.position.x, y = entity.position.y},
        surface = entity.surface and entity.surface.name or nil,
    }
    return summary
end

local function train_summary(cause)
    if not cause or not cause.valid or not cause.train then
        return nil
    end
    local train = cause.train
    local locomotives = {}
    for _, locomotive in pairs(train.locomotives.front_movers or {}) do
        table.insert(locomotives, entity_summary(locomotive))
    end
    for _, locomotive in pairs(train.locomotives.back_movers or {}) do
        table.insert(locomotives, entity_summary(locomotive))
    end
    return {
        id = train.id,
        state = train.state,
        speed = train.speed,
        manual_mode = train.manual_mode,
        locomotives = locomotives,
    }
end

local function record_death(player_index, character, cause, damage_type, tick)
    storage.objective_telemetry.last_death_tick_by_agent =
        storage.objective_telemetry.last_death_tick_by_agent or {}
    if storage.objective_telemetry.last_death_tick_by_agent[player_index] == tick then
        return
    end
    local death = {
        tick = tick,
        player_index = player_index,
        damage_type = damage_type and damage_type.name or nil,
        cause = entity_summary(cause) or {},
        train = train_summary(cause),
    }
    if character and character.valid then
        death.position = {x = character.position.x, y = character.position.y}
        death.surface = character.surface and character.surface.name or nil
    end
    storage.objective_telemetry.death_count =
        (storage.objective_telemetry.death_count or 0) + 1
    storage.objective_telemetry.last_death_tick_by_agent[player_index] = tick
    table.insert(storage.objective_telemetry.deaths, death)
end

script.on_event(defines.events.on_pre_player_died, function(event)
    local player = game.get_player(event.player_index)
    record_death(
        event.player_index,
        player and player.character or nil,
        event.cause,
        event.damage_type,
        event.tick
    )
end)

script.on_event(defines.events.on_entity_died, function(event)
    if not event.entity or event.entity.type ~= "character" then
        return
    end
    for player_index, character in pairs(storage.agent_characters or {}) do
        if character == event.entity then
            record_death(
                player_index,
                event.entity,
                event.cause,
                event.damage_type,
                event.tick
            )
            return
        end
    end
end)

script.on_event(defines.events.on_player_respawned, function(event)
    storage.objective_telemetry.respawn_count =
        (storage.objective_telemetry.respawn_count or 0) + 1
    storage.objective_telemetry.last_respawn_tick = event.tick
end)

script.on_event(defines.events.on_resource_depleted, function(event)
    local entity = event.entity
    table.insert(storage.objective_telemetry.resource_depletions, {
        tick = event.tick,
        name = entity and entity.valid and entity.name or "unknown",
        position = entity and entity.valid and {
            x = entity.position.x,
            y = entity.position.y,
        } or {},
        surface = entity and entity.valid and entity.surface.name or nil,
    })
end)
