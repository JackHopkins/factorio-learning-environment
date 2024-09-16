-- connect_entities.lua

-- Direction vectors for North, East, South, and West respectively.
local directions = {{x = 0, y = -1}, {x = 1, y = 0}, {x = 0, y = 1}, {x = -1, y = 0}}

local wire_reach = {
    ['small-electric-pole'] = 7.5,
    ['medium-electric-pole'] = 9,
    ['big-electric-pole'] = 30,
    ['substation'] = 18
}

function get_step_size(connection_type)
    -- Adjust the step size based on the connection type's wire reach
    return wire_reach[connection_type] or 1
end

function math.round(x)
    return x >= 0 and math.floor(x + 0.5) or math.ceil(x - 0.5)
end

-- Function to get the direction from one position to another.
local function get_direction(from_position, to_position)
    local dx = to_position.x - from_position.x
    local dy = to_position.y - from_position.y
    local adx = math.abs(dx)
    local ady = math.abs(dy)

    if adx > ady then
        if dx > 0 then return 2 end -- East
        if dx < 0 then return 6 end -- West
    else
        if dy > 0 then return 4 end -- South
        if dy < 0 then return 0 end -- North
    end
end

local function place_at_position(player, connection_type, current_position, dir, serialized_entities)
    -- Place the connection entity
    --local dir = next_position and get_direction(current_position, next_position) or 0
    --local dir = get_direction(current_position, next_position)
    --create_beam_point_with_direction(player, dir, current_position)

    -- Check for overlapping entities
    local entities = game.surfaces[1].find_entities_filtered{
        position=current_position,
        --area={{current_position.x - 0.25, current_position.y - 0.25}, {current_position.x + 0.25, current_position.y + 0.25}},
        force = "player"
    }
    if #entities > 0 then
        for _, entity in pairs(entities) do
            if entity.name ~= connection_type and entity.name ~= 'laser-beam' then
                error("Cannot place entity at position (" .. current_position.x .. ", " .. current_position.y .. ") due to overlapping "..entity.name..".")
            end

            if entity.name == connection_type and entity.direction ~= dir then
                entity.direction = dir
                local serialized = global.utils.serialize_entity(entity)
                table.insert(serialized_entities, serialized)
            end
        end
    end

    local placed_entity = game.surfaces[1].create_entity({
        name = connection_type,
        position = current_position,
        direction = dir,
        force = player.force
    })

    if placed_entity ~= nil then
        -- Serialize the entity and add it to the list
        local serialized = global.utils.serialize_entity(placed_entity)

        -- Remove the placed entity from the player's inventory
        player.remove_item({name = connection_type, count = 1})

        table.insert(serialized_entities, serialized)
    end
end

local function get_entity_connection_point(entity)
    if entity.type == "steam-engine" then
        local direction = entity.direction
        local x, y = entity.position.x, entity.position.y
        if direction == defines.direction.north or direction == defines.direction.south then
            return {x = x - 1, y = y}  -- Left side input for vertical orientation
        else
            return {x = x, y = y - 1}  -- Top side input for horizontal orientation
        end
    elseif entity.type == "boiler" then
        -- Implement boiler-specific logic if ne
        return entity.position
    elseif entity.type == "offshore-pump" then
        -- Use the pump's fluid box connection
        return entity.fluidbox.get_connections(1)[1].target_position
    end
    -- Default to entity position if no specific logic
    return entity.position
end

-- Function to find the shortest path.
local function shortest_path(player, source_position, target_position)
    -- Initialize the distances and previous nodes arrays.
    -- Calculate the grid size based on the source and target positions.
    local grid_size_x = math.ceil(math.abs(target_position.x - source_position.x))
    local grid_size_y = math.ceil(math.abs(target_position.y - source_position.y))
    local grid_size = math.max(grid_size_x, grid_size_y)+8

    -- Initialize the distances and previous nodes arrays.
    local distances = {}
    local previous = {}
    for dx = -grid_size, grid_size do
        distances[dx] = {}
        previous[dx] = {}
        for dy = -grid_size, grid_size do
            distances[dx][dy] = {distance = math.huge, direction = 1, turns = 0}
        end
    end

    -- Get the initial direction towards the target.
    local initial_direction = get_direction(source_position, target_position)

    -- The source node is at (0, 0) in our local grid.
    distances[0][0] = {distance = 0, direction = nil, turns = 0}

    local queue = {{x = 0, y = 0}}

    while #queue > 0 do
        local pos = table.remove(queue, 1)

        for i = 1, 4 do
            local nx = pos.x + directions[i].x
            local ny = pos.y + directions[i].y
            local new_direction = i

            -- Make sure we are still inside the local grid.
            if nx >= -grid_size and nx <= grid_size and ny >= -grid_size and ny <= grid_size then
                local entities = game.surfaces[1].find_entities_filtered{
                    area={
                        {source_position.x + nx - 0.5, source_position.y + ny - 0.5},
                        {source_position.x + nx + 0.5, source_position.y + ny + 0.5}
                    },
                     area={
                        {source_position.x + nx - 0.5, source_position.y + ny - 0.5},
                        {source_position.x + nx + 0.5, source_position.y + ny + 0.5}
                    },
                     --position={source_position.x + nx, source_position.y + ny},
                     --radius = 1,
                    force = "player"
                }

                local turns
                local new_distance
                if distances[pos.x][pos.y] then
                    turns = distances[pos.x][pos.y].turns
                    if distances[pos.x][pos.y].direction ~= nil and distances[pos.x][pos.y].direction ~= new_direction then
                        turns = turns + 1
                    end

                    new_distance = distances[pos.x][pos.y].distance + 1
                    if #entities > 0 then
                        new_distance = new_distance + 4
                    end

                end
                -- The new score is a weighted sum of the distance and the number of turns

                if distances[nx][ny] then
                    local new_score = new_distance + turns
                    local old_score = distances[nx][ny].distance + distances[nx][ny].turns

                    if new_score < old_score or (new_distance == distances[nx][ny].distance and turns < distances[nx][ny].turns) and #entities == 0 then
                    --if new_distance < distances[nx][ny].distance or (new_distance == distances[nx][ny].distance and turns < distances[nx][ny].turns) and #entities == 0 then
                    --if new_distance < distances[nx][ny].distance and #entities == 0 then
                        distances[nx][ny] = {distance = new_distance, direction = new_direction, turns = turns}
                        table.insert(queue, {x = nx, y = ny})
                    end
                end
            end
        end
    end

    -- Build the path from the target position to the source position.
    local path = {}
    local pos = {x = math.floor(target_position.x - source_position.x), y = math.floor(target_position.y - source_position.y)}
    table.insert(path, 1, target_position)

    while pos.x ~= 0 or pos.y ~= 0 do
        local new_pos = {x = pos.x + source_position.x, y = pos.y + source_position.y}
        table.insert(path, 1, new_pos)

        local dir = distances[pos.x][pos.y].direction
        pos = {x = pos.x - directions[dir].x, y = pos.y - directions[dir].y}
        --create_beam_point(player, pos)
    end

    table.insert(path, 1, source_position)

    -- Handle the fractional part of the target position.
    local last_path_position = path[#path]
    local diff_x = target_position.x - last_path_position.x
    local diff_y = target_position.y - last_path_position.y
    local fractional_distance = math.sqrt(diff_x ^ 2 + diff_y ^ 2)

    if fractional_distance > 0.707 then
        local dir = get_direction(last_path_position, target_position)
        local fractional_pos = {
            x = last_path_position.x + math.floor(fractional_distance * directions[dir].x),
            y = last_path_position.y + math.floor(fractional_distance * directions[dir].y)
        }
        table.insert(path, fractional_pos)
    end

    return path
end

local function get_closest_entity(player, position)
    local closest_distance = math.huge
    local closest_entity = nil
    local surface = player.surface
   -- local position = {x = math.floor(position.x), y = math.floor(position.y)}
    local area = {{position.x - 1, position.y - 1}, {position.x + 1, position.y + 1}}

    local entities = surface.find_entities_filtered{area = area, force = "player"}

    -- Find the closest entities
    for _, entity in ipairs(entities) do
        if entity.name ~= 'character' then
            local distance = ((position.x - entity.position.x) ^ 2 + (position.y - entity.position.y) ^ 2) ^ 0.5
            if distance < closest_distance then
                closest_distance = distance
                closest_entity = entity
            end
        end
    end

    if closest_entity == nil then
        error("No entity at the given coordinates." .. position.x .. ", " .. position.y)
    end

    return closest_entity
end

-- Using the new shortest_path function.
global.actions.connect_entities = function(player_index, source_x, source_y, target_x, target_y, path_handle, connection_type)
    local player = game.players[player_index]
    local start_position = {x = math.floor(source_x), y = math.floor(source_y)}
    local end_position = {x = math.floor(target_x), y = math.floor(target_y)}
    local path = global.paths[path_handle]

    -- Check if path is valid
    if not path or type(path) ~= "table" or #path == 0 then
        error("Invalid path: " .. serpent.line(path))
    end

    local serialized_entities = {}
    local xdiff = math.abs(source_x-target_x)
    local ydiff = math.abs(source_y-target_y)

    local source_entity = get_closest_entity(player, {x = source_x, y = source_y})
    local target_entity = get_closest_entity(player, {x = target_x, y = target_y})

    --game.print("Source entity: " .. source_entity.name)
    --game.print("Target entity: " .. target_entity.name)

    if xdiff <= 0.707 and ydiff <= 0.707 then
        local dir = get_direction(start_position, end_position)
        place_at_position(player, connection_type, start_position, dir, serialized_entities)
        return {entities = serialized_entities, connected = true}
    end


    --local source_connection = get_entity_connection_point(source_entity)
    --local target_connection = get_entity_connection_point(target_entity)

    --game.print("Source connection: " .. source_connection.x .. ", " .. source_connection.y)
    --game.print("Target connection: " .. target_connection.x .. ", " .. target_connection.y)

    --local path = shortest_path(player, start_position, end_position)

    local step_size = get_step_size(connection_type)
    for i = 1, #path - 1, step_size do
        local dir = (path[i + step_size] and get_direction(path[i].position, path[i + step_size].position)) or 0
        place_at_position(player, connection_type, path[i].position, dir, serialized_entities)
    end

    -- Check if entities are connected
    local is_connected = false
    if source_entity.fluidbox and target_entity.fluidbox and
       source_entity.fluidbox[1] and target_entity.fluidbox[1] then
        is_connected = (source_entity.fluidbox[1].get_fluid_system_id() == target_entity.fluidbox[1].get_fluid_system_id())
    else
        is_connected = (#serialized_entities > 0)
    end

    game.print("Connection status: " .. tostring(is_connected))

    return {
        entities = serialized_entities,
        connected = is_connected
    }
end
