global.actions.rotate_entity = function(player_index, x, y, direction)
    local player = game.players[player_index]
    local position = {x=math.floor(x + 0.5), y=math.floor(y + 0.5)}  -- Round to nearest tile
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
    local buildings = surface.find_entities_filtered{area = area, force = "player"}

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

    --local direction_map = {defines.direction.north, defines.direction.east, defines.direction.south, defines.direction.west}
    --local inserter_direction_map = {defines.direction.south, defines.direction.west, defines.direction.north, defines.direction.east}
    --
    --local orientation
    --if closest_entity.type == "inserter" then
    --    orientation = inserter_direction_map[direction + 1]
    --else
    --    orientation = direction_map[direction + 1]
    --end

    -- Rotate the entity
    closest_entity.direction = global.utils.get_entity_direction(closest_entity.name, direction)

    -- Ensure the entity is properly aligned to the grid
    local entity_position = closest_entity.position
    local aligned_position = {
        x = math.floor(entity_position.x * 2) / 2,
        y = math.floor(entity_position.y * 2) / 2
    }
    game.print("Entity position: " .. entity_position.x .. ", " .. entity_position.y)
    game.print("Aligned position: " .. aligned_position.x .. ", " .. aligned_position.y)

    if entity_position.x ~= aligned_position.x or entity_position.y ~= aligned_position.y then
        closest_entity.teleport(aligned_position)
    end

    game.print("Rotated " .. closest_entity.name .. " to " .. closest_entity.direction)

    local serialized = global.utils.serialize_entity(closest_entity)
    return serialized
end

global.actions.rotate_entity2 = function(player_index, x, y, direction)
    local player = game.players[player_index]
    local position = {x=x, y=y}
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
    local buildings = surface.find_entities_filtered{area = area, force = "player"}

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

    local valid_directions = {0, 1, 2, 3, 4, 5, 6, 7}

    if not table_contains(valid_directions, direction) then
        error("Invalid direction " .. direction .. " provided. Please use 0 (north) to 7 (northwest).")
    end

    -- Set the entity's direction directly
    closest_entity.direction = direction

    game.print("Rotated " .. closest_entity.name .. " to " .. closest_entity.direction)

    local serialized = global.utils.serialize_entity(closest_entity)
    return serialized
end

global.actions.rotate_entity2 = function(player_index, x, y, direction)
    local player = game.players[player_index]
    local position = {x=x, y=y}
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
    local buildings = surface.find_entities_filtered{area = area, force = "player"}

    game.print("Found "..#buildings.." entities")
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

    local valid_directions = {0, 2, 4, 6}

    --    North - 0
    --    Northeast - 1
    --    East - 2
    --    Southeast - 3
    --    South - 4
    --    Southwest - 5
    --    West - 6
    --    Northwest - 7

    if not table_contains(valid_directions, direction*2) then
        error("\"Invalid direction "..(direction).." provided. Please use 0 (north), 2 (east), 4 (south), or 6 (west).\"")
    end

    local direction_map = {defines.direction.north, defines.direction.east, defines.direction.south, defines.direction.west}
    -- Inserters have upside down directions, weirdly
    local inserter_direction_map = {defines.direction.south, defines.direction.west, defines.direction.north, defines.direction.east}

    if closest_entity.type == "inserter" then
        orientation = inserter_direction_map[direction+1] -- 1 based index
        --game.print("orientation: " .. orientation .. " direction: " .. direction)
    else
        orientation = direction_map[direction+1] -- 1 based index
    end

    --orientation = inserter_direction_map[direction+1]
    game.print(orientation)
    local current_direction = closest_entity.direction

    --closest_entity.rotate{direction = (direction)*2}
    local max_rotations = 4
    while closest_entity.direction ~= orientation do
        if max_rotations == 0 then
            break
        end
        closest_entity.rotate()
        max_rotations = max_rotations - 1
    end
    game.print("Current direction: "..closest_entity.direction..", direction: "..direction)


    --closest_entity.direction = direction*2



    --closest_entity.rotate()
    --closest_entity.rotate()

        --else
        --    closest_entity.rotate{reverse=true}
        --end
    --end

    game.print("Direction "..direction)
    game.print("Rotated "..closest_entity.name.." to ".. closest_entity.direction)--closest_entity.direction)
    --game.print(dump(closest_entity))
    --closest_entity.direction = direction

    local serialized = global.utils.serialize_entity(closest_entity)
    local entity_json = game.table_to_json(serialized)-- game.table_to_json(entity)
    --game.print(entity_json)

    return serialized
end