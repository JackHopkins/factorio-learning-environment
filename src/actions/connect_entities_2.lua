-- Function to get the direction from one position to another
local function get_direction(from_position, to_position)
    local dx = to_position.x - from_position.x
    local dy = to_position.y - from_position.y

    if math.abs(dx) > math.abs(dy) then
        -- East or West
        if dx > 0 then
            return 2 -- East
        else
            return 6 -- West
        end
    else
        -- North or South
        if dy > 0 then
            return 4 -- South
        else
            return 0 -- North
        end
    end
end

local function place_at_position(player, connection_type, current_position, direction)
    -- Place the connection entity
        local direction_to_next = {x = current_position.x + direction.x, y = current_position.y + direction.y}
        local dir = get_direction(current_position, direction_to_next)

        create_beam_point_with_direction(player, dir, current_position)

        -- Check for overlapping entities
        local entities = game.surfaces[1].find_entities_filtered{area={{current_position.x - 0.5, current_position.y - 0.5}, {current_position.x + 0.5, current_position.y + 0.5}}, force = "player"}
        if #entities > 0 then
           for _, entity in pairs(entities) do
               if entity.name ~= connection_type and entity.name ~= 'laser-beam' then
                   error("Cannot place entity at position (" .. current_position.x .. ", " .. current_position.y .. ") due to overlapping "..entity.name..".")
               end
           end
        end


        --place_position = {x = math.floor(current_position.x), y = math.floor(current_position.y)}
        local placed_entity = game.surfaces[1].create_entity({name = connection_type, position = current_position, direction = dir, force = player.force})

        -- Serialize the entity and add it to the list
        local serialized = global.utils.serialize_entity(placed_entity)

        -- Remove the placed entity from the player's inventory
        player.remove_item({name = connection_type, count = 1})

        return serialized
end

local function move_and_place(player, serialized_entities, connection_type, current_position, direction, distance, axis)
    for i = 1, distance do

        local placed_entity = place_at_position(player, connection_type, current_position, direction)
        table.insert(serialized_entities, placed_entity)

        -- Move to the next position
        current_position[axis] = current_position[axis] + direction[axis]
    end
end

global.actions.connect_entities = function(player_index, source_x, source_y, target_x, target_y, connection_type)
    local player = game.players[player_index]

    --local distance = math.sqrt(direction.x ^ 2 + direction.y ^ 2)
    -- Calculate the Manhattan distance
    if source_x == target_x and source_y == target_y then
        error("Source and target positions are the same.")
    end

    create_beam_point(player, {x = source_x, y = source_y})
    create_beam_point(player, {x = target_x, y = target_y})

    local dx = target_x - source_x
    local dy = target_y - source_y

    local offset_x = dx ~= 0 and 0.5 * (dx / math.abs(dx)) or 0
    local offset_y = dy ~= 0 and 0.5 * (dy / math.abs(dy)) or 0

    local current_position = {x = source_x + offset_x, y = source_y + offset_y}

    local distance = math.abs(target_x - source_x) + math.abs(target_y - source_y)

    -- Check if player has the required items in their inventory
    local count = player.get_main_inventory().get_item_count(connection_type)
    if count < distance then
        error("\"You need "..math.ceil(distance).." "..connection_type.." in your inventory, but you only have "..count..".\"")
    end

    -- Check for overlapping entities and place the connection entities
    --game.print("Current position: (" .. current_position.x .. ", " .. current_position.y .. ")")
    --game.print("Target position: (" .. target_x .. ", " .. target_y .. ")")

    local serialized_entities = {}

    local direction = {x = 0, y = 0}
    local x_distance = math.abs(target_x - source_x)
    local y_distance = math.abs(target_y - source_y)
    game.print("Y dist: "..y_distance)

    if x_distance < y_distance then
        game.print(tostring(current_position.x)..' < '..target_x)
        direction.x = current_position.x < target_x and 1 or -1
        direction.y = 0 -- Reset the y direction
        move_and_place(player, serialized_entities, connection_type, current_position, direction, x_distance, 'x')

        game.print(tostring(current_position.y)..' < '..target_y)
        direction.y = current_position.y < target_y and 1 or -1
        direction.x = 0 -- Reset the x direction
        y_distance = math.abs(target_y - current_position.y)
        game.print("Y dist: "..y_distance)
        --game.print(current_position.y + direction.y - target_y)
        --if current_position.y + direction.y - target_y > 1 then
        move_and_place(player, serialized_entities, connection_type, current_position, direction, y_distance+1, 'y')
        --end

    else
        game.print(tostring(current_position.y)..' < '..target_y)
        direction.y = current_position.y < target_y and 1 or -1
        direction.x = 0 -- Reset the x direction
        move_and_place(player, serialized_entities, connection_type, current_position, direction, y_distance, 'y')

        game.print(tostring(current_position.x)..' < '..target_x)
        direction.x = current_position.x < target_x and 1 or -1
        direction.y = 0 -- Reset the y direction
        x_distance = math.abs(target_x - current_position.x)
        move_and_place(player, serialized_entities, connection_type, current_position, direction, x_distance+1, 'x')
    end

    return serialized_entities
end
