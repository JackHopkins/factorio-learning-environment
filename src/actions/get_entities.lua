global.actions.get_entities = function(player_index, radius, entity_names_json, position_x, position_y)
    local player = game.get_player(player_index)
    local position
    if position_x and position_y then
        position = {x = tonumber(position_x), y = tonumber(position_y)}
    else
        position = player.position
    end

    radius = tonumber(radius) or 5
    local entity_names = game.json_to_table(entity_names_json) or {}
    local area = {
        {position.x - radius, position.y - radius},
        {position.x + radius, position.y + radius}
    }

    -- Directly use the entity_names in find_entities_filtered
    local filter = {
        area = area,
        force = player.force,
        -- Only add name filter if we have entity names
        name = #entity_names > 0 and entity_names or nil
    }

    local entities = player.surface.find_entities_filtered(filter)
    local result = {}
    for _, entity in ipairs(entities) do
        if entity.name ~= 'character' then
            local serialized = global.utils.serialize_entity(entity)
            table.insert(result, serialized)
        end
    end
    return dump(result)
end