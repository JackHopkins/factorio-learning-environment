-- connect_entities.lua

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

local function has_valid_fluidbox(entity)
    return entity.fluidbox and #entity.fluidbox > 0 and entity.fluidbox[1] and entity.fluidbox[1].get_fluid_system_id
end

local function are_fluidboxes_connected(entity1, entity2)
    if has_valid_fluidbox(entity1) and has_valid_fluidbox(entity2) then
        return entity1.fluidbox[1].get_fluid_system_id() == entity2.fluidbox[1].get_fluid_system_id()
    end
    return false
end

local function interpolate_manhattan(pos1, pos2)
    local interpolated = {}
    local dx = pos2.x - pos1.x
    local dy = pos2.y - pos1.y

    -- Move horizontally first, then vertically
    if math.abs(dx) > 0 then
        table.insert(interpolated, {position = {x = pos2.x, y = pos1.y}})
    end

    return interpolated
end

global.actions.normalise_path = function(original_path, start_position)
    local path = {}
    local seen = {}  -- To track seen positions

    -- Helper function to add unique positions
    local function add_unique(pos)
        local key = pos.x .. "," .. pos.y
        if not seen[key] then
            table.insert(path, {position = pos})
            seen[key] = true
        end
    end


    -- Add start position first
    add_unique(start_position)

    for i = 1, #original_path - 1 do
        add_unique(original_path[i].position)
        local interpolated = interpolate_manhattan(original_path[i].position, original_path[i+1].position)
        for _, point in ipairs(interpolated) do
            add_unique(point.position)
        end
    end
    --table.insert(path, original_path[#original_path])
    add_unique(original_path[#original_path].position)

    return path
end

global.utils.reverse_path = function(path)
    local reversed = {}
    for i = #path, 1, -1 do
        table.insert(reversed, path[i])
    end
    return reversed
end

local function get_direction(from_position, to_position)
    local dx = to_position.x - from_position.x
    local dy = to_position.y - from_position.y
    local adx = math.abs(dx)
    local ady = math.abs(dy)

    -- Threshold for considering movement as diagonal
    local diagonal_threshold = 0.5

    if adx > ady then
        if dx > 0 then
            if ady / adx > diagonal_threshold then
                return dy > 0 and 3 or 1  -- Southeast or Northeast
            else
                return 2  -- East
            end
        else
            if ady / adx > diagonal_threshold then
                return dy > 0 and 5 or 7  -- Southwest or Northwest
            else
                return 6  -- West
            end
        end
    else
        if dy > 0 then
            if adx / ady > diagonal_threshold then
                return dx > 0 and 3 or 5  -- Southeast or Southwest
            else
                return 4  -- South
            end
        else
            if adx / ady > diagonal_threshold then
                return dx > 0 and 1 or 7  -- Northeast or Northwest
            else
                return 0  -- North
            end
        end
    end
end

local function place_at_position(player, connection_type, current_position, dir, serialized_entities)
    local entities = game.surfaces[1].find_entities_filtered{
        position = current_position,
        force = "player"
    }

    local existing_entity = nil
    for _, entity in pairs(entities) do
        if entity.name == connection_type then
            existing_entity = entity
            break
        elseif entity.name ~= 'laser-beam' and entity.name ~= 'character' then
            error("Cannot place entity at position (" .. current_position.x .. ", " .. current_position.y .. ") due to overlapping " .. entity.name .. ".")
        end
    end

    if existing_entity then
        if existing_entity.direction ~= dir then
            existing_entity.direction = dir
            -- Find and update the existing entity in serialized_entities
            for i, serialized in ipairs(serialized_entities) do
                if serialized.position.x == current_position.x and serialized.position.y == current_position.y then
                    serialized_entities[i] = global.utils.serialize_entity(existing_entity)
                    return  -- Exit the function as we've updated the existing entity
                end
            end
            -- If not found in serialized_entities, add it
            table.insert(serialized_entities, global.utils.serialize_entity(existing_entity))
        end
        return  -- Exit the function as we've handled the existing entity
    end

    -- Check if the player has the entity in their inventory
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

    -- Check if the entity can be placed at the given position
    if not game.surfaces[1].can_place_entity{
        name = connection_type,
        position = current_position,
        direction = dir,
        force = player.force
    } then
        global.actions.avoid_entity(player.index, connection_type, current_position)
    end

    local placed_entity = game.surfaces[1].create_entity({
        name = connection_type,
        position = current_position,
        direction = dir,
        force = player.force
    })

    if placed_entity ~= nil then
        local serialized = global.utils.serialize_entity(placed_entity)
        player.remove_item({name = connection_type, count = 1})
        table.insert(serialized_entities, serialized)
    end
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
        if entity.name ~= 'character' and entity.name ~= 'laser-beam' then
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


     if source_x == target_x and source_y == target_y then
        error("Source and target positions are the same.")
    end

    local start_position = {x = math.floor(source_x*2)/2, y = math.floor(source_y*2)/2}
    local end_position = {x = math.floor(target_x*2)/2, y = math.floor(target_y*2)/2}

    create_beam_point_with_direction(player, 0, start_position)
    create_beam_point_with_direction(player, 2, end_position)

    local raw_path = global.paths[path_handle]

    -- Check if path is valid
    if not raw_path or type(raw_path) ~= "table" or #raw_path == 0 then
        error("Invalid path: " .. serpent.line(path))
    end


    local path = global.actions.normalise_path(raw_path, start_position) --{x = source_x, y = source_y})
    -- For each position in the path, place a laser
    -- surface.create_entity{name='laser-beam', position=player.position, source_position=top_left, target_position=top_right, duration=beam_duration, direction=direction, force='player', player=player}

    for i = 1, #path - 1 do
        --get_direction(path[i].position, path[i + 1].position)
        --local dir = global.utils.get_entity_direction(connection_type, get_direction(path[i].position, path[i + 1].position))
        --create_beam_point_with_direction(player, dir, start_position)
        --game.surfaces[1].create_entity{name='laser-beam', position=path[i].position, source_position=path[i].position, target_position=path[i + 1].position, duration=6000, direction=dir, force='player', player=player}
        create_arrow_with_direction(player, get_direction(path[i].position, path[i + 1].position), path[i].position)
    end

    local serialized_entities = {}
    local xdiff = math.abs(source_x-target_x)
    local ydiff = math.abs(source_y-target_y)

    local source_entity = get_closest_entity(player, {x = source_x, y = source_y})
    local target_entity = get_closest_entity(player, {x = target_x, y = target_y})

    if xdiff + ydiff <= 1 then
        local dir = get_direction(start_position, end_position)
        game.print(dir)
        local entity_dir = global.utils.get_entity_direction(connection_type, dir/2)
        --game.print("Placing entity at position " .. start_position.x .. ", " .. start_position.y .. " with direction " .. entity_dir)
        place_at_position(player, connection_type, start_position, entity_dir, serialized_entities)
        return {entities = serialized_entities, connected = true}
    end

    local step_size = get_step_size(connection_type)
    local dir

    for i = 1, #path-1, step_size do
        --local distance = ((path[i].position.x - path[i + 1].position.x) ^ 2 + (path[i].position.y - path[i + 1].position.y) ^ 2) ^ 0.5
        if connection_type == 'transport-belt' then
            original_dir = (path[i + step_size] and get_direction(path[i + step_size].position, path[i].position)) or 0
        else
            original_dir = (path[i + step_size] and get_direction(path[i].position, path[i + step_size].position)) or 0
        end
        --game.print("Placing entity at position " .. path[i].position.x .. ", " .. path[i].position.y .. " connection type: " .. connection_type .. " direction: " .. original_dir .. "ndir: ".. global.utils.get_entity_direction(connection_type, original_dir/2))
        dir = global.utils.get_entity_direction(connection_type, original_dir/2)

        place_at_position(player, connection_type, path[i].position, dir, serialized_entities)
    end
    place_at_position(player, connection_type, path[#path].position, dir, serialized_entities)


    --if connection_type ~= 'transport-belt' then
    --original_dir = path[1] and get_direction(end_position, path[1].position) or 0
    --else
    --    original_dir = path[1] and get_direction(path[1].position, end_position) or 0
    --end
    --dir = global.utils.get_entity_direction(connection_type, original_dir/2)

    place_at_position(player, connection_type, end_position, dir, serialized_entities)

    game.print("Source entity: " .. source_entity.name)
    game.print("Target entity: " .. target_entity.name)
    --game.print("Source entity: " .. source_entity.fluidbox[1].get_fluid_system_id())
    --game.print("Target entity: " .. target_entity.fluidbox[1].get_fluid_system_id())

    -- Check if entities are connected
    local is_connected = are_fluidboxes_connected(source_entity, target_entity)

    if not is_connected then
        is_connected = (#serialized_entities > 0)
    end

    game.print("Connection status: " .. tostring(is_connected))

    return {
        entities = serialized_entities,
        connected = is_connected
    }
end
