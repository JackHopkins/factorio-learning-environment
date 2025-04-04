global.actions.get_entities = function(character_index, radius, entity_names_json, position_x, position_y)
    local character = global.character_registry.get_character_by_index(character_index)
    if not character then
        error("Character not found in registry at index " .. character_index)
    end

    local position
    if position_x and position_y then
        position = {x = tonumber(position_x), y = tonumber(position_y)}
    else
        position = character.position
    end

    radius = tonumber(radius) or 5
    local entity_names = game.json_to_table(entity_names_json) or {}
    local area = {
        {position.x - radius, position.y - radius},
        {position.x + radius, position.y + radius}
    }

    local filter = {}
    if entity_names and #entity_names > 0 then
        filter = {name = entity_names}
    end

    local entities
    if #entity_names > 0 then
        entities = character.surface.find_entities_filtered{area = area, force = character.force, filter=filter}
    else
        entities = character.surface.find_entities_filtered{area = area, force = character.force}
    end

    local result = {}
    for _, entity in ipairs(entities) do
        if entity.name ~= 'character' then
            local serialized = global.utils.serialize_entity(entity)
            table.insert(result, serialized)
        end
    end
    return dump(result)
end