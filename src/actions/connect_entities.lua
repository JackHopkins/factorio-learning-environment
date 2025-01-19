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

    if manhattan_distance > 2 then
        local steps = math.max(math.abs(dx), math.abs(dy))
        local x_step = dx / steps
        local y_step = dy / steps

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
    elseif math.abs(dx) == 1 and math.abs(dy) == 1 then
        local mid_pos = {x = pos2.x, y = pos1.y}
        if is_placeable(mid_pos) then
            table.insert(interpolated, {position = mid_pos})
        else
            mid_pos = {x = pos1.x, y = pos2.y}
            if is_placeable(mid_pos) then
                table.insert(interpolated, {position = mid_pos})
            else
                mid_pos = find_placeable_neighbor(mid_pos, pos1)
                if mid_pos then
                    table.insert(interpolated, {position = mid_pos})
                end
            end
        end
    end

    return interpolated
end

local function get_direction(from_position, to_position)
    local dx = to_position.x - from_position.x
    local dy = to_position.y - from_position.y
    local adx = math.abs(dx)
    local ady = math.abs(dy)
    local diagonal_threshold = 0.5

    if adx > ady then
        if dx > 0 then
            return (ady / adx > diagonal_threshold) and (dy > 0 and 3 or 1) or 2
        else
            return (ady / adx > diagonal_threshold) and (dy > 0 and 5 or 7) or 6
        end
    else
        if dy > 0 then
            return (adx / ady > diagonal_threshold) and (dx > 0 and 3 or 5) or 4
        else
            return (adx / ady > diagonal_threshold) and (dx > 0 and 1 or 7) or 0
        end
    end
end

local function get_closest_entity(player, position)
    local closest_distance = math.huge
    local closest_entity = nil
    local entities = player.surface.find_entities_filtered{
        position = position,
        force = "player",
        radius = 3
    }

    for _, entity in ipairs(entities) do
        if entity.name ~= 'character' and entity.name ~= 'laser-beam' then
            local distance = ((position.x - entity.position.x) ^ 2 + (position.y - entity.position.y) ^ 2) ^ 0.5
            if distance < closest_distance then
                closest_distance = distance
                closest_entity = entity
            end
        end
    end

    return closest_entity
end

local function place_at_position(player, connection_type, current_position, dir, serialized_entities, dry_run, counter_state)
    counter_state.place_counter = counter_state.place_counter + 1
    if dry_run then return end
    game.print("Placing at position: "..current_position.x..", "..current_position.y)

    local is_electric_pole = wire_reach[connection_type] ~= nil
    local placement_position = current_position
    local existing_entity = nil

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
    game.print("can place?: "..serpent.line(can_place).." - "..current_position.x..", "..current_position.y)

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
        global.actions.avoid_entity(player.index, connection_type, placement_position)
        --if player.surface.can_place_entity{
        --    name = connection_type,
        --    position = placement_position,
        --    direction = dir,
        --    force = player.force
        --} then
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
        --end
    end
end

local function connect_entities(player_index, source_x, source_y, target_x, target_y, path_handle, connection_type, dry_run)
    local counter_state = {place_counter = 0}
    local player = game.get_player(player_index)

    local start_position = {x = math.floor(source_x*2)/2, y = math.floor(source_y*2)/2}
    local end_position = {x = target_x, y = target_y}

    local raw_path = global.paths[path_handle]
    if not raw_path or type(raw_path) ~= "table" or #raw_path == 0 then
        error("Invalid path: " .. serpent.line(path))
    end

    local path = global.actions.normalise_path(raw_path, start_position, end_position)
    local serialized_entities = {}

    -- Get source and target entities
    local source_entity = get_closest_entity(player, {x = source_x, y = source_y})
    local target_entity = get_closest_entity(player, {x = target_x, y = target_y})

    local is_electric_pole = wire_reach[connection_type] ~= nil

    if is_electric_pole then
        -- Place poles until we achieve connectivity
        local last_pole = source_entity
        local step_size = get_step_size(connection_type)

        for i = 1, #path-1, step_size do
            local current_pos = path[i].position
            local dir = get_direction(current_pos, path[math.min(i + step_size, #path)].position)
            local entity_dir = global.utils.get_entity_direction(connection_type, dir/2)

            -- Place the pole
            local placed_entity = place_at_position(player, connection_type, current_pos, entity_dir, serialized_entities, dry_run, counter_state)

            if not dry_run then
                -- Get the newly placed pole
                local current_pole = placed_entity or get_closest_entity(player, current_pos)

                -- Check if we've achieved connectivity to the target
                if are_poles_connected(current_pole, target_entity) then
                    break  -- Stop placing poles once we have connectivity
                end

                last_pole = current_pole
            end
        end

        -- If we haven't achieved connectivity yet, place one final pole at the target
        if not dry_run and last_pole and target_entity and not are_poles_connected(last_pole, target_entity) then
            local final_dir = get_direction(path[#path].position, end_position)
            place_at_position(player, connection_type, end_position,
                global.utils.get_entity_direction(connection_type, final_dir/2),
                serialized_entities, dry_run, counter_state)
        end
    else
        -- For pipes and belts
        local step_size = get_step_size(connection_type)

        if connection_type == 'pipe' then
            place_at_position(player, connection_type, start_position, 0, serialized_entities, dry_run, counter_state)
        end

        for i = 1, #path-1, step_size do
            local dir = get_direction(path[i].position, path[math.min(i + step_size, #path)].position)
            place_at_position(player, connection_type, path[i].position,
                global.utils.get_entity_direction(connection_type, dir/2),
                serialized_entities, dry_run, counter_state)
        end

        -- Handle final placement
        if connection_type == 'pipe' then
            local preemptive_target = {
                x = (target_x + path[#path].position.x)/2,
                y = (target_y + path[#path].position.y)/2
            }

            -- Place intermediate and final pipes
            place_at_position(player, connection_type, path[#path].position,
                get_direction(path[#path].position, preemptive_target),
                serialized_entities, dry_run, counter_state)

            place_at_position(player, connection_type, preemptive_target,
                get_direction(path[#path].position, preemptive_target),
                serialized_entities, dry_run, counter_state)

            place_at_position(player, connection_type, end_position,
                get_direction(preemptive_target, end_position),
                serialized_entities, dry_run, counter_state)
        else
            -- For belts, just place the final entity
            local final_dir = get_direction(path[#path].position, end_position)
            place_at_position(player, connection_type, end_position,
                global.utils.get_entity_direction(connection_type, final_dir/2),
                serialized_entities, dry_run, counter_state)
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

global.actions.normalise_path = function(original_path, start_position, end_position)
    --- This function interpolates the path to ensure that all positions are placeable and within 1 tile of each other

    local path = {}
    local seen = {}  -- To track seen positions

    -- Helper function to add unique positions
    local function add_unique(pos)
        local key = pos.x .. "," .. pos.y
        if not seen[key] then
            if is_placeable(pos) then
                table.insert(path, {position = pos})
                seen[key] = true
                return pos
            else
                local alt_pos = find_placeable_neighbor(pos, previous_pos)
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
    local previous_pos = nil
    previous_pos = add_unique(start_position) or start_position

    -- Interpolate the start to the second position in the original path.
    if #original_path > 2 then
        local interpolated = interpolate_manhattan(start_position, original_path[2].position)
        for _, point in ipairs(interpolated) do
            local new_pos = add_unique(point.position, previous_pos)
            if new_pos then previous_pos = new_pos end
        end
    end

    for i = 1, #original_path - 1 do
        local current_pos = add_unique(original_path[i].position, previous_pos)
        if current_pos then
            previous_pos = current_pos
            local interpolated = interpolate_manhattan(current_pos, original_path[i+1].position)
            for _, point in ipairs(interpolated) do
                local new_pos = add_unique(point.position, previous_pos)
                if new_pos then previous_pos = new_pos end
            end
        end
    end

    local interpolated = interpolate_manhattan(path[#path].position, end_position)
    for _, point in ipairs(interpolated) do
        add_unique(point.position)
    end

    add_unique(end_position)

    return path
end

-- Using the new shortest_path function.
global.actions.connect_entities = function(player_index, source_x, source_y, target_x, target_y, path_handle, connection_type, dry_run, number_of_connection_entities)
    --First do a dry run
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
