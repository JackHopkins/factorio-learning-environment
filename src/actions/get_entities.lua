global.actions.get_entities = function(player_index, radius, entity_names_json, position_x, position_y)
    local player = game.get_player(player_index)
    local position
    if position_x and position_y then
        position = {x = tonumber(position_x), y = tonumber(position_y)}
    else
        position = player.position
    end
    --local position = (x == 0 and y == 0) and player.position or {x = x, y = y}
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
        entities = player.surface.find_entities_filtered{area = area, force = player.force, filter=filter}
    else
        entities = player.surface.find_entities_filtered{area = area, force = player.force}
    end

    local result = {}
    for _, entity in ipairs(entities) do
        if entity.name ~= 'character' and (#filter == 0 or global.utils.table_contains(filter.name, entity.name)) then
            local serialized = global.utils.serialize_entity(entity)
            table.insert(result, serialized)
        end
    end

    return dump(result)--game.table_to_json(result)
end

-- Helper function to check if a table contains a value
global.utils.table_contains = function(table, val)
    for i = 1, #table do
        if table[i] == val then
            return true
        end
    end
    return false
end