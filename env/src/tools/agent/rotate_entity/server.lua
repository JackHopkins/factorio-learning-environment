global.actions.rotate_entity = function(player_index, x, y, direction, entity)
    local player = global.agent_characters[player_index]
    local position = {x=x, y=y}  -- Round to nearest tile
    local surface = player.surface

    local function table_contains(tbl, element)
        for _, value in ipairs(tbl) do
            if value == element then
                return true
            end
        end
        return false
    end

    local closest_distance = math.huge
    local closest_entity = nil
    local area = {{position.x - 0.5, position.y - 0.5}, {position.x + 0.5, position.y + 0.5}}
    local buildings = surface.find_entities_filtered{area = area, force = "player", name=entity}

    -- Find the closest building
    for _, building in ipairs(buildings) do
        if building.rotatable and building.name ~= 'character' then
            local distance = ((position.x - building.position.x) ^ 2 + (position.y - building.position.y) ^ 2) ^ 0.5
            if distance < closest_distance then
                closest_distance = distance
                closest_entity = building
            end
        end
    end

    if closest_entity == nil then
        error("No entity to rotate at the given coordinates.")
    end

    local valid_directions = {0, 1, 2, 3}

    if not table_contains(valid_directions, direction) then
        error("Invalid direction " .. direction .. " provided. Please use 0 (north), 1 (east), 2 (south), or 3 (west).")
    end

    --  game.print("Direction "..direction.. ", "..closest_entity.name..", "..closest_entity.direction)
    -- game.print(global.utils.get_entity_direction(closest_entity.name, closest_entity.direction))

    -- Rotate the entity
    closest_entity.direction = global.utils.get_entity_direction(closest_entity.name, direction)

    -- Ensure the entity is properly aligned to the grid
    local entity_position = closest_entity.position
    local aligned_position = {
        x = math.floor(entity_position.x),
        y = math.floor(entity_position.y)
    }
    -- game.print("Entity position: " .. entity_position.x .. ", " .. entity_position.y)
    -- game.print("Aligned position: " .. aligned_position.x .. ", " .. aligned_position.y)

    if entity_position.x ~= aligned_position.x or entity_position.y ~= aligned_position.y then
        closest_entity.teleport(aligned_position)
    end

    -- game.print("Rotated " .. closest_entity.name .. " to " .. closest_entity.direction)

    local serialized = global.utils.serialize_entity(closest_entity)
    return serialized
end