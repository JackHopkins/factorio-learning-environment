-- Function to get the direction from one position to another
local function get_direction(from_position, to_position)
    local dx = to_position.x - from_position.x
    local dy = to_position.y - from_position.y

    if math.abs(dx) > math.abs(dy) then
        -- East or West
        if dx > 0 then
            return defines.direction.east -- East
        else
            return defines.direction.west -- West
        end
    else
        -- North or South
        if dy > 0 then
            return defines.direction.south -- South
        else
            return defines.direction.north -- North
        end
    end
end

local function place_or_rotate_belt(player, connection_type, current_position, direction_vector)
    local surface = game.surfaces[1]
    local area = {
        {current_position.x - 0.1, current_position.y - 0.1},
        {current_position.x + 0.1, current_position.y + 0.1}
    }
    local entities = surface.find_entities_filtered{
        area = area,
        force = player.force,
        type = "transport-belt"
    }

    local dir = get_direction(current_position, {
        x = current_position.x + direction_vector.x,
        y = current_position.y + direction_vector.y
    })

    if #entities > 0 then
        -- Rotate existing belt
        local existing_belt = entities[1]
        existing_belt.direction = dir
        return global.utils.serialize_entity(existing_belt)
    else
        -- Place new belt
        local placed_entity = surface.create_entity{
            name = connection_type,
            position = current_position,
            direction = dir,
            force = player.force
        }
        -- Remove the placed entity from the player's inventory
        player.remove_item{name = connection_type, count = 1}
        return global.utils.serialize_entity(placed_entity)
    end
end

local function move_and_place(player, serialized_entities, connection_type, current_position, direction_vector, steps, axis)
    for i = 1, steps do
        local serialized = place_or_rotate_belt(player, connection_type, current_position, direction_vector)
        table.insert(serialized_entities, serialized)
        -- Move to the next position
        current_position[axis] = current_position[axis] + direction_vector[axis]
    end
end

global.actions.connect_entities = function(player_index, source_x, source_y, target_x, target_y, connection_type)
    local player = game.players[player_index]
    local surface = game.surfaces[1]

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

    local x_distance = math.abs(target_x - source_x)
    local y_distance = math.abs(target_y - source_y)
    local total_steps = x_distance + y_distance

    -- Check if player has the required items in their inventory
    local inventory_count = player.get_main_inventory().get_item_count(connection_type)
    if inventory_count < total_steps then
        error("You need " .. math.ceil(total_steps) .. " " .. connection_type .. "s in your inventory, but you only have " .. inventory_count .. ".")
    end

    local serialized_entities = {}

    local direction_vector = {x = 0, y = 0}
    if x_distance >= y_distance then
        -- Move along x-axis first
        direction_vector.x = dx > 0 and 1 or -1
        move_and_place(player, serialized_entities, connection_type, current_position, direction_vector, x_distance, 'x')

        direction_vector.x = 0
        direction_vector.y = dy > 0 and 1 or -1
        move_and_place(player, serialized_entities, connection_type, current_position, direction_vector, y_distance, 'y')
    else
        -- Move along y-axis first
        direction_vector.y = dy > 0 and 1 or -1
        move_and_place(player, serialized_entities, connection_type, current_position, direction_vector, y_distance, 'y')

        direction_vector.y = 0
        direction_vector.x = dx > 0 and 1 or -1
        move_and_place(player, serialized_entities, connection_type, current_position, direction_vector, x_distance, 'x')
    end

    return serialized_entities
end