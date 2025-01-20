-- Wire reach values for different electric pole types
local wire_reach = {
    ['small-electric-pole'] = 4,
    ['medium-electric-pole'] = 9,
    ['big-electric-pole'] = 30,
    ['substation'] = 18
}

function get_step_size(connection_type)
    return wire_reach[connection_type] or 1
end

function math.round(x)
    return x >= 0 and math.floor(x + 0.5) or math.ceil(x - 0.5)
end

local function has_valid_fluidbox(entity)
    return entity.fluidbox and #entity.fluidbox > 0 and entity.fluidbox[1] and entity.fluidbox[1].get_fluid_system_id
end

local function are_fluidboxes_connected(entity1, entity2)
    if has_valid_fluidbox(entity1) and has_valid_fluidbox(entity2) then
        return entity1.fluidbox[1].get_fluid_system_id() == entity2.fluidbox[1].get_fluid_system_id()
    end
    return false
end

-- Helper function to serialize a belt group
local function serialize_belt_group(entity)
    if not entity or not entity.valid or entity.type ~= "transport-belt" then
        return nil
    end

    local serialized = {}
    local seen = {}

    local function get_connected_belt_entities(belt, is_output)
        local connected_entities = {}
        local seen_owners = {}

        -- Get connected lines
        local connected_lines = {}
        if is_output then
            if #belt.belt_neighbours['outputs'] then
                for _, line in pairs(belt.belt_neighbours['outputs']) do
                    table.insert(connected_lines, line)
                end
            end
        else
            if #belt.belt_neighbours['inputs'] then
                for _, line in pairs(belt.belt_neighbours['inputs']) do
                    table.insert(connected_lines, line)
                end
            end
        end

        game.print("connected lines "..#connected_lines)
        -- Convert lines to unique belt entities
        for _, line in pairs(connected_lines) do
            if line and line.valid and not seen_owners[line.unit_number] then
                seen_owners[line.unit_number] = true
                table.insert(connected_entities, line)
            end
        end
        game.print("connected entities "..#connected_entities)
        return connected_entities
    end

    local function serialize_connected_belts(belt, is_output)
        if not belt or not belt.valid or seen[belt.unit_number] then
            return
        end

        seen[belt.unit_number] = true
        local belt_data = global.utils.serialize_entity(belt)
        table.insert(serialized, belt_data)

        -- Get connected belt entities
        local next_belts = get_connected_belt_entities(belt, is_output)
        for _, connected_belt in pairs(next_belts) do
            if connected_belt.valid and not seen[connected_belt.unit_number] then
                serialize_connected_belts(connected_belt, is_output)
            end
        end
    end

    -- Start serialization from the given entity
    serialize_connected_belts(entity, false) -- Follow input direction
    serialize_connected_belts(entity, true)  -- Follow output direction

    return serialized
end


local function are_poles_connected(entity1, entity2)
    if not (entity1 and entity2) then return false end
    if not (entity1.electric_network_id and entity2.electric_network_id) then return false end
    return entity1.electric_network_id == entity2.electric_network_id
end

local function is_placeable(position)
    local invalid_tiles = {
        ["water"] = true,
        ["deepwater"] = true,
        ["water-green"] = true,
        ["deepwater-green"] = true,
        ["water-shallow"] = true,
        ["water-mud"] = true,
    }

    local entities = game.surfaces[1].find_entities_filtered{
        position = position,
        collision_mask = "player-layer"
    }
    if #entities == 1 then
        if entities[1].name == "character" then
            return not invalid_tiles[game.surfaces[1].get_tile(position.x, position.y).name]
        end
    end
    return #entities == 0 and not invalid_tiles[game.surfaces[1].get_tile(position.x, position.y).name]
end

local function find_placeable_neighbor(pos, previous_pos)
    local directions = {
        {dx = 0, dy = -1},  -- up
        {dx = 1, dy = 0},   -- right
        {dx = 0, dy = 1},   -- down
        {dx = -1, dy = 0}   -- left
    }

    if previous_pos then
        local desired_dx = pos.x - previous_pos.x
        local desired_dy = pos.y - previous_pos.y
        table.sort(directions, function(a, b)
            local a_score = math.abs(a.dx - desired_dx) + math.abs(a.dy - desired_dy)
            local b_score = math.abs(b.dx - desired_dx) + math.abs(b.dy - desired_dy)
            return a_score < b_score
        end)
    end

    for _, dir in ipairs(directions) do
        local test_pos = {x = pos.x + dir.dx, y = pos.y + dir.dy}
        if is_placeable(test_pos) then
            return test_pos
        end
    end
    return nil
end


local function interpolate_manhattan(pos1, pos2)
    local interpolated = {}
    local dx = pos2.x - pos1.x
    local dy = pos2.y - pos1.y
    local manhattan_distance = math.abs(dx) + math.abs(dy)
    game.print("Distance2 "..manhattan_distance)
    if manhattan_distance > 2 then
        local steps = math.max(math.abs(dx), math.abs(dy))
        local x_step = math.floor((dx / steps)*2)/2
        local y_step = math.floor((dy / steps)*2)/2

        for i = 1, steps - 1 do
            local new_pos_x = {x = pos1.x + math.round(x_step * i), y = pos1.y}
            if is_placeable(new_pos_x) then
                table.insert(interpolated, {position = new_pos_x})
            else
                local neighbor = find_placeable_neighbor(new_pos_x, pos1)
                if neighbor then
                    table.insert(interpolated, {position = neighbor})
                end
            end

            local new_pos_y = {x = pos1.x + math.round(x_step * i), y = pos1.y + math.round(y_step * i)}
            if is_placeable(new_pos_y) then
                table.insert(interpolated, {position = new_pos_y})
            else
                local neighbor = find_placeable_neighbor(new_pos_y, pos1)
                if neighbor then
                    table.insert(interpolated, {position = neighbor})
                end
            end
        end
        --elseif math.abs(dx) == 1 and math.abs(dy) == 1 then
        --    local mid_pos = {x = pos2.x, y = pos1.y}
        --    if is_placeable(mid_pos) then
        --        table.insert(interpolated, {position = mid_pos})
        --    else
        --        mid_pos = {x = pos1.x, y = pos2.y}
        --        if is_placeable(mid_pos) then
        --            table.insert(interpolated, {position = mid_pos})
        --        else
        --            mid_pos = find_placeable_neighbor(mid_pos, pos1)
        --            if mid_pos then
        --                table.insert(interpolated, {position = mid_pos})
        --            end
        --        end
        --    end
        --end
        elseif math.abs(dx) == 1 and math.abs(dy) == 1 then --and math.abs(dx) <= 1.5 and math.abs(dy) <= 1.5 then
            -- Try first horizontal then vertical movement
            local mid_pos = {x = pos2.x, y = pos1.y}
            if is_placeable(mid_pos) then
                table.insert(interpolated, {position = mid_pos})
            else
                -- Try vertical then horizontal movement
                mid_pos = {x = pos1.x, y = pos2.y}
                if is_placeable(mid_pos) then
                    table.insert(interpolated, {position = mid_pos})
                else
                    -- If neither orthogonal position works, try to find a neighbor
                    local neighbor = find_placeable_neighbor(mid_pos, pos1)
                    if neighbor then
                        table.insert(interpolated, {position = neighbor})
                    end
                end
            end

    end

    return interpolated
end

--local function get_direction(from_position, to_position)
--    local dx = to_position.x - from_position.x
--    local dy = to_position.y - from_position.y
--    local adx = math.abs(dx)
--    local ady = math.abs(dy)
--    local diagonal_threshold = 0.5
--
--    if adx > ady then
--        if dx > 0 then
--            return (ady / adx > diagonal_threshold) and (dy > 0 and 3 or 1) or 2
--        else
--            return (ady / adx > diagonal_threshold) and (dy > 0 and 5 or 7) or 6
--        end
--    else
--        if dy > 0 then
--            return (adx / ady > diagonal_threshold) and (dx > 0 and 3 or 5) or 4
--        else
--            return (adx / ady > diagonal_threshold) and (dx > 0 and 1 or 7) or 0
--        end
--    end
--end



local function place_at_position(player, connection_type, current_position, dir, serialized_entities, dry_run, counter_state)
    counter_state.place_counter = counter_state.place_counter + 1
    if dry_run then return end

    local is_electric_pole = wire_reach[connection_type] ~= nil
    local placement_position = current_position
    local existing_entity = nil

    for _, entity in pairs(serialized_entities) do
        if entity.position.x == placement_position.x and entity.position.y == placement_position.y then
            return
        end
    end

    if is_electric_pole then
        placement_position = game.surfaces[1].find_non_colliding_position(connection_type, current_position, 3, 0.1)
        if not placement_position then
            error("Cannot find suitable position to place " .. connection_type)
        end
    else
        local entities = game.surfaces[1].find_entities_filtered{
            position = current_position,
            type = {"beam", "resource", "player"}, invert=true,
            force = "player"
        }
        for _, entity in pairs(entities) do
            if entity.name == connection_type then
                existing_entity = entity
                break
            end
        end
    end

    if existing_entity then
        if existing_entity.direction ~= dir then
            existing_entity.direction = dir
            for i, serialized in ipairs(serialized_entities) do
                if serialized.position.x == current_position.x and serialized.position.y == current_position.y then
                    serialized_entities[i] = global.utils.serialize_entity(existing_entity)
                    return
                end
            end
            table.insert(serialized_entities, global.utils.serialize_entity(existing_entity))
        end
        return
    end

    -- Check inventory
    local has_item = false
    for _, inv in pairs({defines.inventory.character_main}) do
        if player.get_inventory(inv) then
            local count = player.get_inventory(inv).get_item_count(connection_type)
            if count > 0 then
                has_item = true
                break
            end
        end
    end
    if not has_item then
        error("Player does not have the required item in their inventory.")
    end

    local can_place = game.surfaces[1].can_place_entity{
        name = connection_type,
        position = placement_position,
        direction = dir,
        force = player.force
    }

    -- Place entity
    if can_place then
        local placed_entity = game.surfaces[1].create_entity({
            name = connection_type,
            position = placement_position,
            direction = dir,
            force = player.force
        })

        if placed_entity then
            player.remove_item({name = connection_type, count = 1})
            table.insert(serialized_entities, global.utils.serialize_entity(placed_entity))
            return placed_entity
        end
    else
        game.print("Avoiding entity at " .. placement_position.x.. ", " .. placement_position.y)
        global.utils.avoid_entity(player.index, connection_type, placement_position, dir)
        local placed_entity = player.surface.create_entity({
            name = connection_type,
            position = placement_position,
            direction = dir,
            force = player.force
        })

        if placed_entity then
            player.remove_item({name = connection_type, count = 1})
            table.insert(serialized_entities, global.utils.serialize_entity(placed_entity))
            return placed_entity
        end
    end
end

local function connect_entities(player_index, source_x, source_y, target_x, target_y, path_handle, connection_type, dry_run)
    local counter_state = {place_counter = 0}
    local player = game.get_player(player_index)
    local last_placed_entity = nil

    local start_position = {x = math.floor(source_x*2)/2, y = math.floor(source_y*2)/2}
    local end_position = {x = target_x, y = target_y}

    local raw_path = global.paths[path_handle]
    game.print("Path length "..#raw_path)
    game.print(serpent.line(start_position).." - "..serpent.line(end_position))

    if not raw_path or type(raw_path) ~= "table" or #raw_path == 0 then
        error("Invalid path: " .. serpent.line(path))
    end

    game.print("Normalising", {print_skip=defines.print_skip.never})
    local path = global.utils.normalise_path(raw_path, start_position, end_position)

    rendering.clear()
    for i = 1, #path - 1 do
        rendering.draw_line{surface = game.players[1].surface, from = path[i].position, to =  path[i + 1].position, color = {1, 0, 1}, width = 2,  dash_length=0.25, gap_length = 0.25}
    end
    for i = 1, #raw_path - 1 do
        rendering.draw_line{surface = game.players[1].surface, from = raw_path[i].position, to =  raw_path[i + 1].position, color = {1, 1, 0}, width = 0,  dash_length=0.2, gap_length = 0.2}
    end

    game.print("Norm path length "..#path)

    local last_position = start_position
    local step_size = wire_reach[connection_type] or 1

    for i = 1, #path-1, step_size do
        global.elapsed_ticks = global.elapsed_ticks + global.utils.calculate_movement_ticks(player, last_position, path[i].position)
        last_position = path[i].position
    end

    local serialized_entities = {}

    -- Get source and target entities
    local source_entity = global.utils.get_closest_entity(player, {x = source_x, y = source_y})
    local target_entity = global.utils.get_closest_entity(player, {x = target_x, y = target_y})

    local is_electric_pole = wire_reach[connection_type] ~= nil

    -- Handle source belt orientation if it exists
    if not is_electric_pole and connection_type ~= 'pipe' then
        local source_pos = {x = source_x, y = source_y}
        local entities = game.surfaces[1].find_entities_filtered{
            position = source_pos,
            name = connection_type,
            force = "player"
        }

        if #entities > 0 and #path > 1 then
            -- Calculate initial direction based on first two points in path
            local initial_dir = global.utils.get_direction(path[1].position, path[2].position)
            local entity_dir = global.utils.get_entity_direction(connection_type, initial_dir/2)

            -- Update source belt direction if needed
            local source_belt = entities[1]
            if source_belt and source_belt.valid and source_belt.direction ~= initial_dir then
                source_belt.direction = initial_dir
                table.insert(serialized_entities, global.utils.serialize_entity(source_belt))
            end
        end
    end

    if is_electric_pole then
        -- Place poles until we achieve connectivity
        local last_pole = source_entity

        for i = 1, #path-1, step_size do
            local current_pos = path[i].position
            local dir = global.utils.get_direction(current_pos, path[math.min(i + step_size, #path)].position)
            local entity_dir = global.utils.get_entity_direction(connection_type, dir/2)

            -- Place the pole
            local placed_entity = place_at_position(player, connection_type, current_pos, entity_dir, serialized_entities, dry_run, counter_state)

            if not dry_run then
                -- Get the newly placed pole
                local current_pole = placed_entity or global.utils.get_closest_entity(player, current_pos)

                -- Check if we've achieved connectivity to the target
                if are_poles_connected(current_pole, target_entity) then
                    break  -- Stop placing poles once we have connectivity
                end

                last_pole = current_pole
            end
        end

        -- If we haven't achieved connectivity yet, place one final pole at the target
        if not dry_run and last_pole and target_entity and not are_poles_connected(last_pole, target_entity) then
            local final_dir = global.utils.get_direction(path[#path].position, end_position)
            place_at_position(player, connection_type, end_position,
                global.utils.get_entity_direction(connection_type, final_dir/2),
                serialized_entities, dry_run, counter_state)
        end
    else
        if connection_type == 'pipe' then
            place_at_position(player, connection_type, start_position, 0, serialized_entities, dry_run, counter_state)
        end

        for i = 1, #path-1, step_size do
            local dir = global.utils.get_direction(path[i].position, path[math.min(i + step_size, #path)].position)
            local placed = place_at_position(player, connection_type, path[i].position,
                global.utils.get_entity_direction(connection_type, dir/2),
                serialized_entities, dry_run, counter_state)
            if placed then
                last_placed_entity = placed
            end
        end

        -- Handle final placement
        if connection_type == 'pipe' then
            local preemptive_target = {
                x = (target_x + path[#path].position.x)/2,
                y = (target_y + path[#path].position.y)/2
            }

            -- Place intermediate and final pipes
            place_at_position(player, connection_type, path[#path].position,
                global.utils.get_direction(path[#path].position, preemptive_target),
                serialized_entities, dry_run, counter_state)

            place_at_position(player, connection_type, preemptive_target,
                global.utils.get_direction(path[#path].position, preemptive_target),
                serialized_entities, dry_run, counter_state)

            place_at_position(player, connection_type, end_position,
                global.utils.get_direction(preemptive_target, end_position),
                serialized_entities, dry_run, counter_state)
        else
            local last_path_index = #path
            local second_to_last_index = math.max(1, last_path_index - 1)
            local final_dir = global.utils.get_direction(
                path[second_to_last_index].position,
                path[last_path_index].position
            )

            local final_entity = place_at_position(player, connection_type, end_position,
                global.utils.get_entity_direction(connection_type, final_dir/2),
                serialized_entities, dry_run, counter_state)

            if final_entity then
                last_placed_entity = final_entity
            end

            -- After all belts are placed, serialize the entire belt group if we're not in dry run
            if not dry_run and last_placed_entity and last_placed_entity.valid then
                -- Clear the existing serialized entities (which only contain individual placements)

                serialized_entities = {}
                -- Serialize the entire connected belt group
                local group_data = serialize_belt_group(last_placed_entity)
                if group_data then
                    for _, serialized in ipairs(group_data) do
                        table.insert(serialized_entities, serialized)
                    end
                end
            end
        end
    end

    -- Check final connectivity
    local is_connected = false
    if source_entity and target_entity then
        if is_electric_pole then
            is_connected = are_poles_connected(source_entity, target_entity)
        else
            is_connected = are_fluidboxes_connected(source_entity, target_entity)
        end
    end

    game.print("Connection status: " .. tostring(is_connected))


    return {
        entities = serialized_entities,
        connected = is_connected, 
        number_of_entities = counter_state.place_counter
    }
end

global.utils.normalise_path = function(original_path, start_position, end_position)
    local path = {}
    local seen = {}  -- To track seen positions

    if math.ceil(start_position.x) == start_position.x or math.ceil(start_position.y) == start_position.y then
        start_position.x = start_position.x + 0.5
        start_position.y = start_position.y + 0.5
    end

    if math.ceil(end_position.x) == end_position.x or math.ceil(end_position.y) == end_position.y then
        end_position.x = end_position.x + 0.5
        end_position.y = end_position.y + 0.5
    end

    for i = 1, #original_path do
        game.print(serpent.line(original_path[i]))
    end

    if math.ceil(original_path[1].position.x) == original_path[1].position.x or math.ceil(original_path[1].position.y) == original_path[1].position.y then
        original_path[1].position.x = original_path[1].position.x + 0.5
        original_path[1].position.y = original_path[1].position.y + 0.5
    end

    -- Helper function to add unique positions
    local function add_unique(pos, prev_pos)
        local key = pos.x .. "," .. pos.y
        if not seen[key] then
            if is_placeable(pos) then
                table.insert(path, {position = pos})
                seen[key] = true
                return pos
            else
                local alt_pos = find_placeable_neighbor(pos, prev_pos)
                if alt_pos then
                    local alt_key = alt_pos.x .. "," .. alt_pos.y
                    if not seen[alt_key] then
                        table.insert(path, {position = alt_pos})
                        seen[alt_key] = true
                        return alt_pos
                    end
                end
            end
        end
        return nil
    end

    -- Add start position first
    local previous_pos = add_unique(start_position, nil) or start_position

    -- Process each segment of the path
    local current_pos = previous_pos
    for i = 1, #original_path do
        local target_pos = original_path[i].position
        local interpolated = interpolate_manhattan(current_pos, target_pos)

        -- Add interpolated positions
        for _, point in ipairs(interpolated) do
            local new_pos = add_unique(point.position, current_pos)
            if new_pos then
                current_pos = new_pos
            end
        end

        -- Add the target position
        local new_pos = add_unique(target_pos, current_pos)
        if new_pos then
            current_pos = new_pos
        end
    end

    -- Finally interpolate to end position if it's different from the last position
    if current_pos.x ~= end_position.x or current_pos.y ~= end_position.y then
        local interpolated = interpolate_manhattan(current_pos, end_position)
        for _, point in ipairs(interpolated) do
            local new_pos = add_unique(point.position, current_pos)
            if new_pos then
                current_pos = new_pos
            end
        end
        add_unique(end_position, current_pos)
    end

    return path
end

-- Using the new shortest_path function.
global.actions.connect_entities = function(player_index, source_x, source_y, target_x, target_y, path_handle, connection_type, dry_run, number_of_connection_entities)
    --First do a dry run
    game.print("haha")
    local result = connect_entities(player_index, source_x, source_y, target_x, target_y, path_handle, connection_type, true)
    -- then do an actual run if dry run is false
    if not dry_run then
        -- Check if the player has enough entities in their inventory
        local required_count = result.number_of_entities
        game.print("Required count: " .. required_count)
        game.print("Available count: " .. number_of_connection_entities)
        if number_of_connection_entities < required_count then
            error("\"Player does not have enough " .. connection_type .. " in their inventory to complete this connection. Required number: " .. required_count .. ", Available in inventory: " .. number_of_connection_entities.."\"")
        end
        result = connect_entities(player_index, source_x, source_y, target_x, target_y, path_handle, connection_type, false)
    end
    
    return result
end
