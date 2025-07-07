
global.actions.inspect_entities = function(player_index, radius, position_x, position_y)
    local player = global.agent_characters[player_index]
    local position

    if position_x and position_y then
        position = {x = tonumber(position_x), y = tonumber(position_y)}
    else
        position = player.position
    end

    radius = tonumber(radius) or 5
    function find_connected_entities(entity)
        local entities_to_search = {
            {entity = entity, dx = 0, dy = -1, dir = defines.direction.north},
            {entity = entity, dx = 0, dy = 1, dir = defines.direction.south},
            {entity = entity, dx = 1, dy = 0, dir = defines.direction.east},
            {entity = entity, dx = -1, dy = 0, dir = defines.direction.west}
        }

        local connected_entities = {}

        for _, search in ipairs(entities_to_search) do
            local search_pos = {x = entity.position.x + search.dx, y = entity.position.y + search.dy}
            local found_entity = entity.surface.find_entity(entity.name, search_pos)

            if found_entity then
                if entity.type == "transport-belt" and found_entity.direction == search.dir then
                    table.insert(connected_entities, found_entity)
                elseif entity.type == "pipe" then
                    table.insert(connected_entities, found_entity)
                end
            end
        end

        return connected_entities
    end


    function recursive_search(entity, visited, path_ends)
        if visited[entity.unit_number] then
            return
        end

        visited[entity.unit_number] = true
        local connected_entities = find_connected_entities(entity)

        if connected_entities and #connected_entities > 0 then
            local unconnected_neighbours = 0
            for _, connected_entity in ipairs(connected_entities) do
                if not visited[connected_entity.unit_number] then
                    unconnected_neighbours = unconnected_neighbours + 1
                    recursive_search(connected_entity, visited, path_ends)
                end
            end

            if unconnected_neighbours == 1 then
                path_ends[entity.unit_number] = entity
            end
        else
            path_ends[entity.unit_number] = entity
        end
    end

    function find_path_ends(entity)
        local visited = {}
        local path_ends = {}
        recursive_search(entity, visited, path_ends)
        return path_ends
    end

    local entity_data = inspect(player, radius, position)

    local result = {}

    for i, data in ipairs(entity_data) do

        local warnings = {}
        if not data.warnings then
            data.warnings = {}
        end
        if data.warnings.fuel_warning then
            table.insert(warnings, data.warnings.fuel_warning:gsub(" ", "_"))
        end
        if data.warnings.output_warning then
            table.insert(warnings, data.warnings.output_warning:gsub(" ", "_"))
        end
        if data.warnings.input_warning then
            table.insert(warnings, data.warnings.input_warning:gsub(" ", "_"))
        end

        local position = {x=data.position.x, y=data.position.y}

        --game.print(data.name .. ": " .. data.direction .. " - ".. global.utils.get_entity_direction(data.name:gsub("_", "-"), data.direction))
        local entity_info = {
            name = data.name:gsub("-", "_"),
            position = position,
            direction = global.utils.get_entity_direction(data.name:gsub("_", "-"), data.direction),
            health = data.health,
            force = data.force,
            energy = data.energy,
            contents = data.contents,
            crafting_progress = data.crafting_progress,
            productivity_bonus = data.productivity_bonus,
            orientation = data.orientation,
            ingredients = data.ingredients,
            path_ends = data.path_ends,
            warnings = data.warnings,
            status = data.status
        }
        -- if crafted_items exists on data
        if data.crafted_items then
            entity_info.crafted_items = data.crafted_items
        end

        --local serialized = global.utils.serialize_entity(data)
        --table.insert(result, serialized)

        table.insert(result, entity_info)
    end

    return dump(result)
end