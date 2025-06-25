-- move_to

-- Register the tick handler when the module is loaded
if not global.fast then
    script.on_nth_tick(5, function(event)
        if global.walking_queues then
            global.actions.update_walking_queues()
        end
    end)
end

--local function get_direction(from_pos, to_pos)
--    local dx = to_pos.x - from_pos.x
--    local dy = to_pos.y - from_pos.y
--    if dx == 0 and dy == 0 then
--        return nil
--    elseif math.abs(dx) > math.abs(dy) then
--        return dx > 0 and defines.direction.east or defines.direction.west
--    else
--        return dy > 0 and defines.direction.south or defines.direction.north
--    end
--end


global.actions.move_to = function(player_index, path_handle, trailing_entity, is_trailing)
    --local player = global.agent_characters[player_index]
    local player = global.agent_characters[player_index]
    local path = global.paths[path_handle]
    local surface = player.surface

    -- Check if path is valid
    if not path or type(path) ~= "table" or #path == 0 then
        error("Invalid path: " .. serpent.line(path))
    end

    -- If fast mode is disabled, set up walking queue
    if not global.fast then
        -- Initialize walking queue if it doesn't exist
        if not global.walking_queues then
            global.walking_queues = {}
        end

        -- Create or clear existing queue for this player
        if not global.walking_queues[player_index] then
            global.walking_queues[player_index] = {
                positions = {},
                current_target = nil,
                trailing_entity = trailing_entity,
                is_trailing = is_trailing
            }
        else
            global.walking_queues[player_index].positions = {}
            global.walking_queues[player_index].current_target = nil
            global.walking_queues[player_index].trailing_entity = trailing_entity
            global.walking_queues[player_index].is_trailing = is_trailing
        end

        -- Add all path positions to the queue
        for _, point in ipairs(path) do
            table.insert(global.walking_queues[player_index].positions, point.position)
        end

        -- Start walking to first position
        if #global.walking_queues[player_index].positions > 0 then
            local target = global.walking_queues[player_index].positions[1]
            global.walking_queues[player_index].current_target = target
            player.walking_state = {
                walking = true,
                direction = global.utils.get_direction(player.position, target)
            }
        end

        return player.position
    end

    local function rotate_entity(entity, direction)
        local direction_map = {defines.direction.north, defines.direction.east, defines.direction.south, defines.direction.west}
        local inserter_direction_map = {defines.direction.south, defines.direction.west, defines.direction.north, defines.direction.east}

        if entity.type == "inserter" then
            orientation = inserter_direction_map[direction/2+1]
        else
            orientation = direction_map[direction/2+1]
        end

        while entity.direction ~= orientation do
            entity.rotate()
        end
    end

    local function place(place_position, direction)
        if global.utils.can_place_entity(player, trailing_entity, place_position, direction) then
            if player.get_item_count(trailing_entity) > 0 then
                local created = surface.create_entity{name=trailing_entity, position=place_position, direction=direction, force='player', player=player, build_check_type=defines.build_check_type.manual, fast_replace=true}
                if created then
                    player.remove_item({name=trailing_entity, count=1})
                end
                return created
            else
                error("\"No ".. trailing_entity .." in the inventory\"")
            end
        elseif surface.can_fast_replace{name=trailing_entity, position=place_position, direction=direction, force='player'} then
            local existing_entity = surface.find_entity(trailing_entity, place_position)
            if existing_entity and existing_entity.direction ~= direction then
                rotate_entity(existing_entity, direction)
            end
            return existing_entity
        end
        return nil
    end

    local function place_diagonal(from_pos, to_pos, is_leading)
        local dx = to_pos.x - from_pos.x
        local dy = to_pos.y - from_pos.y
        local mid_pos = {x = from_pos.x , y = to_pos.y }

        local dir_x = dx > 0 and defines.direction.east or defines.direction.west
        local dir_y = dy > 0 and defines.direction.south or defines.direction.north

        if is_leading then
            place(to_pos, (dir_x + 4) % 8)

            local corner_dir
            if (dx > 0 and dy > 0) or (dx < 0 and dy < 0) then
                corner_dir = dir_x
            else
                corner_dir = dir_y
            end

            if dx == 1 and dy == 1 then
                corner_dir = defines.direction.east
            end

            place(mid_pos, (corner_dir + 4) % 8)
        else
            place(from_pos, dir_y)

            local corner_dir
            if (dx > 0 and dy > 0) or (dx < 0 and dy < 0) then
                corner_dir = dir_y
            else
                corner_dir = dir_x
            end

            if dx == 1 and dy == 1 then
                corner_dir = defines.direction.east
            end

            place(mid_pos, corner_dir)
        end
    end

    if is_trailing == 1 or is_trailing == 0 then
        if game.entity_prototypes[trailing_entity] == nil then
            error('No entity exists that can be laid')
        end
    end

    local prev_belt = nil
    local prev_pos = player.position
    for i = 1, #path do
        local current_position = player.position
        local target_position = path[i].position

        -- Calculate and accumulate movement ticks before teleporting
        global.elapsed_ticks = global.elapsed_ticks + global.utils.calculate_movement_ticks(player, prev_pos, target_position)


        local direction = global.utils.get_direction(prev_pos, target_position)

        if not direction then
            goto continue
        end

        local new_belt
        if is_trailing == 1 then
             if math.abs(prev_pos.x - target_position.x) == 1 and math.abs(prev_pos.y - target_position.y) == 1 then
                --game.print("Placing diagonal belt at " .. serpent.line(prev_pos) .. " to " .. serpent.line(target_position))
                place_diagonal(prev_pos, target_position, false)
            else
                --game.print("Placing at direction: " .. direction .. " Current position: " .. serpent.line(prev_pos) .. " Target position: " .. serpent.line(target_position))
                new_belt = place(prev_pos, direction)
                if prev_belt then
                    rotate_entity(prev_belt, global.utils.get_direction(prev_belt.position, prev_pos))
                end
            end
            player.teleport(target_position)
        elseif is_trailing == 0 then
            if math.abs(prev_pos.x - target_position.x) == 1 and math.abs(prev_pos.y - target_position.y) == 1 then
                place_diagonal(prev_pos, target_position, true)
            else
                -- game.print("Placing at direction: " .. direction .. " Current position: " .. serpent.line(prev_pos) .. " Target position: " .. serpent.line(target_position))
                directions = {defines.direction.north, defines.direction.east, defines.direction.south, defines.direction.west}
                opposite_direction = {defines.direction.south, defines.direction.west, defines.direction.north, defines.direction.east}
                new_direction = opposite_direction[direction/2+1]
                new_belt = place(target_position, new_direction)
                if prev_belt then
                    rotate_entity(prev_belt, global.utils.get_direction(prev_belt.position, current_position))
                end
            end
            player.teleport(target_position)
        else
            player.teleport(target_position)
        end
        prev_belt = new_belt
        prev_pos = target_position
        ::continue::
    end

    return player.position
end

-- Add this new function to handle the walking queue updates
-- This should be called on every tick
global.actions.update_walking_queues = function()
    if not global.walking_queues then return end

    for player_index, queue in pairs(global.walking_queues) do
        local player = global.agent_characters[player_index]
        if not player or not queue.current_target then goto continue end

        local distance = ((player.position.x - queue.current_target.x)^2 +
                         (player.position.y - queue.current_target.y)^2)^0.5

        -- If player is close enough to current target
        if distance < 1 then
            -- Remove the current position from queue
            table.remove(queue.positions, 1)

            -- If there are more positions, start walking to next one
            if #queue.positions > 0 then
                queue.current_target = queue.positions[1]
                player.walking_state = {
                    walking = true,
                    direction = global.utils.get_direction_with_diagonals(player.position, queue.current_target)
                }
            else
                -- Queue is empty, stop walking
                player.walking_state = {walking = false}
                queue.current_target = nil
            end
        else
            -- Update walking direction to current target
            player.walking_state = {
                walking = true,
                direction = global.utils.get_direction_with_diagonals(player.position, queue.current_target)
            }
        end

        ::continue::
    end
end

global.actions.clear_walking_queue = function(player_index)
    if global.walking_queues and global.walking_queues[player_index] then
        global.walking_queues[player_index] = nil
    end
end

global.actions.get_walking_queue_length = function(player_index)
    if global.walking_queues and global.walking_queues[player_index] then
        return #global.walking_queues[player_index].positions
    end
    return 0
end