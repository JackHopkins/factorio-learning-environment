global.utils.remove_enemies = function ()
    game.forces["enemy"].kill_all_units()  -- Removes all biters
    game.map_settings.enemy_expansion.enabled = false  -- Stops biters from expanding
    game.map_settings.enemy_evolution.enabled = false  -- Stops biters from evolving
    local surface = game.surfaces[1]
    for _, entity in pairs(surface.find_entities_filtered({type="unit-spawner"})) do
        entity.destroy()
    end
end

local directions = {'north', 'northeast', 'east', 'southeast', 'south', 'southwest', 'west', 'northwest'}

global.utils.get_direction = function(from_position, to_position)
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

global.utils.get_direction_with_diagonals = function(from_pos, to_pos)
    local dx = to_pos.x - from_pos.x
    local dy = to_pos.y - from_pos.y

    if dx == 0 and dy == 0 then
        return nil
    end

    -- Check for cardinal directions first
    local cardinal_margin = 0.20 --0.25
    if math.abs(dx) < cardinal_margin then
        return dy > 0 and defines.direction.south or defines.direction.north
    elseif math.abs(dy) < cardinal_margin then
        return dx > 0 and defines.direction.east or defines.direction.west
    end

    -- Handle diagonal directions
    if dx > 0 then
        return dy > 0 and defines.direction.southeast or defines.direction.northeast
    else
        return dy > 0 and defines.direction.southwest or defines.direction.northwest
    end
end


global.utils.get_closest_entity = function(player, position)
    local closest_distance = math.huge
    local closest_entity = nil
    local entities = player.surface.find_entities_filtered{
        position = position,
        force = "player",
        radius = 5  -- Increased from 3 to 5 to better handle large entities like 3x3 drills
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

global.utils.calculate_movement_ticks = function(player, from_pos, to_pos)
    -- Calculate distance between points
    local dx = to_pos.x - from_pos.x
    local dy = to_pos.y - from_pos.y
    local distance = math.sqrt(dx * dx + dy * dy)

    -- Get player's walking speed (tiles per tick)
    -- Character base speed is 0.15 tiles/tick
    local walking_speed = player.character_running_speed
    if not walking_speed or walking_speed == 0 then
        walking_speed = 0.15  -- Default walking speed
    end

    -- Calculate ticks needed for movement
    return math.ceil(distance / walking_speed)
end

-- Wrapper around LuaSurface.can_place_entity that replicates all checks LuaPlayer.can_place_entity performs.
-- This allows our code to validate placement without relying on an actual LuaPlayer instance.
-- extra_params can be provided by callers to pass additional flags (e.g. fast_replace) if needed.
global.utils.can_place_entity = function(player, entity_name, position, direction, extra_params)
    local params = extra_params or {}
    params.name = entity_name
    params.position = position
    params.direction = direction
    params.force = player.force
    -- Use the manual build-check path so the engine applies the same rules as when a human player builds.
    params.build_check_type = defines.build_check_type.manual
    return player.surface.can_place_entity(params)
end

global.utils.avoid_entity = function(player_index, entity, position, direction)
    local player = global.agent_characters[player_index]
    local player_position = player.position
    for i=0, 10 do
        local can_place = player.surface.can_place_entity{
            name = entity,
            force = "player",
            position = position,
            direction = global.utils.get_entity_direction(entity, direction)
        }
        if can_place then
            return true
        end
        player.teleport({player_position.x + i, player_position.y + i})
    end
    player.teleport(player_position)
    return false
end

global.crafting_queue = {}

script.on_event(defines.events.on_tick, function(event)
  -- Iterate over the crafting queue and update the remaining ticks
  for i, task in ipairs(global.crafting_queue) do
    task.remaining_ticks = task.remaining_ticks - 1

    -- If the crafting is finished, consume the ingredients, insert the crafted entity, and remove the task from the queue
    if task.remaining_ticks <= 0 then
      for _, ingredient in pairs(task.recipe.ingredients) do
        task.player.remove_item({name = ingredient.name, count = ingredient.amount * task.count})
      end
      task.player.insert({name = task.entity_name, count = task.count})
      table.remove(global.crafting_queue, i)
    end
  end
end)

function dump(o)
   if type(o) == 'table' then
      local s = '{ '
      for k,v in pairs(o) do
         if type(k) ~= 'number' then k = '"'..k..'"' end
         s = s .. '['..k..'] = ' .. dump(v) .. ','
      end
      return s .. '} '
   else
      return tostring(o)
   end
end

function global.utils.inspect(player, radius, position)
    local surface = player.surface
    local bounding_box = {
        left_top = {x = position.x - radius, y = position.y - radius},
        right_bottom = {x = position.x + radius, y = position.y + radius}
    }

    local entities = surface.find_entities_filtered({bounding_box, force = "player"})
    local entity_data = {}

    for _, entity in ipairs(entities) do
        if entity.name ~= 'character' then
            local data = {
                name = entity.name:gsub("-", "_"),
                position = entity.position,
                direction = entity.direction,--directions[entity.direction+1],
                health = entity.health,
                force = entity.force.name,
                energy = entity.energy,
                status = entity.status,
                --crafted_items = entity.crafted_items or nil
            }

            -- Get entity contents if it has an inventory
            if entity.get_inventory(defines.inventory.chest) then
                local inventory = entity.get_inventory(defines.inventory.chest).get_contents()
                data.contents = inventory
            end

            data.warnings = global.utils.get_issues(entity)

            -- Get entity orientation if it has an orientation attribute
            if entity.type == "train-stop" or entity.type == "car" or entity.type == "locomotive" then
                data.orientation = entity.orientation
            end

            -- Get connected entities for pipes and transport belts
            if entity.type == "pipe" or entity.type == "transport-belt" then
                local path_ends = find_path_ends(entity)
                data.path_ends = {}
                for _, path_end in pairs(path_ends) do
                    local path_position = {x=path_end.position.x - player.position.x, y=path_end.position.y - player.position.y}
                    table.insert(data.path_ends, {name = path_end.name:gsub("-", "_"), position = path_position, unit_number = path_end.unit_number})
                end
            end

            table.insert(entity_data, data)
        else
            local data = {
                name = "player_character",
                position = entity.position,
                direction = directions[entity.direction+1],
            }
            table.insert(entity_data, data)
        end
    end

    -- Sort entities with path_ends by the length of path_ends in descending order
    table.sort(entity_data, function(a, b)
        if a.path_ends and b.path_ends then
            return #a.path_ends > #b.path_ends
        elseif a.path_ends then
            return true
        else
            return false
        end
    end)

    -- Remove entities that exist in the path_ends of other entities
    local visited_paths = {}
    local filtered_entity_data = {}
    for _, data in ipairs(entity_data) do
        if data.path_ends then
            local should_add = true
            for _, path_end in ipairs(data.path_ends) do
                if visited_paths[path_end.unit_number] then
                    should_add = false
                    break
                end
            end
            if should_add then
                for _, path_end in ipairs(data.path_ends) do
                    visited_paths[path_end.unit_number] = true
                end
                table.insert(filtered_entity_data, data)
            else
                data.path_ends = nil
                --table.insert(filtered_entity_data, data)
            end
        else
            table.insert(filtered_entity_data, data)
        end
    end
    entity_data = filtered_entity_data

    return entity_data
end