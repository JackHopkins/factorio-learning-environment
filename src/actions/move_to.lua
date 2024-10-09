-- move_to
global.actions.move_to = function(player_index, path_handle, trailing_entity, is_trailing)
    local player = game.get_player(player_index)
    local path = global.paths[path_handle]
    local surface = player.surface

    -- Check if path is valid
    if not path or type(path) ~= "table" or #path == 0 then
        error("Invalid path: " .. serpent.line(path))
    end

    local function rotate_entity(entity, direction)
        local direction_map = {defines.direction.north, defines.direction.east, defines.direction.south, defines.direction.west}
        -- Inserters have upside down directions, weirdly
        local inserter_direction_map = {defines.direction.south, defines.direction.west, defines.direction.north, defines.direction.east}

        if entity.type == "inserter" then
            orientation = inserter_direction_map[direction/2+1] -- 1 based index
            game.print("orientation: " .. orientation .. " direction: " .. direction)
        else
            orientation = direction_map[direction/2+1] -- 1 based index
        end

        while entity.direction ~= orientation do
            entity.rotate()
        end
    end

    local function place(place_position, direction)
        if surface.can_place_entity{name=trailing_entity, position=place_position, direction=direction, force='player', build_check_type=defines.build_check_type.manual} then
            if player.get_item_count(trailing_entity) > 0 then
                local created = surface.create_entity{name=trailing_entity, position=place_position, direction=direction, force='player', player=player, build_check_type=defines.build_check_type.manual, fast_replace=true}
                if created then
                    player.remove_item({name=trailing_entity, count=1})
                end
                return created
            else
                error("No ".. trailing_entity .." in the inventory")
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

    local function get_direction(from_pos, to_pos)
        local dx = to_pos.x - from_pos.x
        local dy = to_pos.y - from_pos.y
        if dx == 0 and dy == 0 then
            return nil
        elseif math.abs(dx) > math.abs(dy) then
            return dx > 0 and defines.direction.east or defines.direction.west
        else
            return dy > 0 and defines.direction.south or defines.direction.north
        end
    end


    local function place_diagonal(from_pos, to_pos, is_leading)
        local dx = to_pos.x - from_pos.x
        local dy = to_pos.y - from_pos.y
        local mid_pos = {x = from_pos.x , y = to_pos.y }  -- Changed to corner position

        local dir_x = dx > 0 and defines.direction.east or defines.direction.west
        local dir_y = dy > 0 and defines.direction.south or defines.direction.north


        if is_leading then
            -- Place the first belt at the target position
            place(to_pos, (dir_x + 4) % 8)

            -- Determine the direction for the corner piece
            local corner_dir
            if (dx > 0 and dy > 0) or (dx < 0 and dy < 0) then
                corner_dir = dir_x
            else
                corner_dir = dir_y
            end

            -- then the corner piece should be east facing
            if dx == 1 and dy == 1 then
                corner_dir = defines.direction.east
            end

            -- Place the corner piece
            place(mid_pos, (corner_dir + 4) % 8)
        else
            -- Place the first belt at the starting position
            place(from_pos, dir_y)

            -- Determine the direction for the corner piece
            local corner_dir
            if (dx > 0 and dy > 0) or (dx < 0 and dy < 0) then
                corner_dir = dir_y
            else
                corner_dir = dir_x
            end

            -- then the corner piece should be east facing
            if dx == 1 and dy == 1 then
                corner_dir = defines.direction.east
            end

            -- Place the corner piece
            place(mid_pos, corner_dir)
        end
    end

    if is_trailing == 1 or is_trailing == 0 then
        if game.entity_prototypes[trailing_entity] == nil then
            error('No entity exists that can be laid')
        end
    end


    local prev_belt = nil
    for i = 1, #path do
        local current_position = player.position
        local target_position = path[i].position

        local direction = get_direction(current_position, target_position)

        --create_beam_point_with_direction(player, direction, current_position)
        if not direction then
            -- Skip if there's no movement
            goto continue
        end
        --game.print(direction)
        --game.print(defines.direction[direction])
        local new_belt
        if is_trailing == 1 then
             if math.abs(current_position.x - target_position.x) == 1 and math.abs(current_position.y - target_position.y) == 1 then
                game.print("Placing diagonal belt at " .. serpent.line(current_position) .. " to " .. serpent.line(target_position))
                place_diagonal(current_position, target_position, false)
            else
                game.print("Placing at direction: " .. direction .. " Current position: " .. serpent.line(current_position) .. " Target position: " .. serpent.line(target_position))
                new_belt = place(current_position, direction)
                if prev_belt then
                    rotate_entity(prev_belt, get_direction(prev_belt.position, current_position))
                end
            end
            player.teleport(target_position)
        elseif is_trailing == 0 then
            if math.abs(current_position.x - target_position.x) == 1 and math.abs(current_position.y - target_position.y) == 1 then
                place_diagonal(current_position, target_position, true)
            else
                game.print("Placing at direction: " .. direction .. " Current position: " .. serpent.line(current_position) .. " Target position: " .. serpent.line(target_position))
                directions = {defines.direction.north, defines.direction.east, defines.direction.south, defines.direction.west}
                opposite_direction = {defines.direction.south, defines.direction.west, defines.direction.north, defines.direction.east}
                new_direction = opposite_direction[direction/2+1]
                new_belt = place(target_position, new_direction) --(direction + 4) % 8)  -- Opposite direction
                if prev_belt then
                    rotate_entity(prev_belt, get_direction(prev_belt.position, current_position))
                end
            end
            player.teleport(target_position)
        else
            player.teleport(target_position)
        end
        prev_belt = new_belt
        ::continue::
    end

    return player.position
end