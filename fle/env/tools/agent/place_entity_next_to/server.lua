local function is_large_entity(entity)
    if not entity then return false end
    
    -- Check by size (3x3 or larger)
    local prototype = prototypes.entity[entity.name]
    if prototype then
        local collision_box = prototype.collision_box
        local width = math.abs(collision_box.right_bottom.x - collision_box.left_top.x)
        local height = math.abs(collision_box.right_bottom.y - collision_box.left_top.y)
        return width >= 2.6 and height >= 2.6  -- 3x3 entities have collision box ~2.8x2.8
    end
    
    return false
end

local function get_reserved_positions_around_entity(entity)
    if not is_large_entity(entity) then
        return {}
    end
    
    local pos = entity.position
    local reserved = {}
    
    -- For 3x3 entities, we need positions outside the collision box
    -- The collision box extends ±1.5 from center, so we need at least ±2 to be clear
    local middle_adjacent = {
        {x = pos.x, y = pos.y - 2, side = "north"},      -- North (middle)
        {x = pos.x + 2, y = pos.y, side = "east"},       -- East (middle)
        {x = pos.x, y = pos.y + 2, side = "south"},      -- South (middle)
        {x = pos.x - 2, y = pos.y, side = "west"}        -- West (middle)
    }
    
    for _, reserved_pos in pairs(middle_adjacent) do
        table.insert(reserved, reserved_pos)
    end
    
    return reserved
end


local function find_alternative_position_smart(ref_position, ref_entity, entity_to_place, original_direction, gap)
    local alternatives = {}
    
    -- If placing an inserter near a large entity, try the reserved middle positions first
    if ref_entity and is_large_entity(ref_entity) and (entity_to_place == "inserter" or entity_to_place:find("inserter")) then
        local reserved_positions = get_reserved_positions_around_entity(ref_entity)
        
        for _, reserved_pos in pairs(reserved_positions) do
            -- Calculate what direction this would be from the reference entity
            local dx = reserved_pos.x - ref_entity.position.x
            local dy = reserved_pos.y - ref_entity.position.y
            
            local alt_direction
            if math.abs(dx) > math.abs(dy) then
                alt_direction = dx > 0 and 1 or 3  -- East or West
            else
                alt_direction = dy > 0 and 2 or 0  -- South or North
            end
            
            table.insert(alternatives, {
                position = reserved_pos,
                direction = alt_direction,
                score = 75,  -- High priority for reserved positions
                reason = "Reserved position for large entity"
            })
        end
    end
    
    -- Try directions in order of preference
    local direction_priority = {original_direction}  -- Start with requested direction
    
    -- Add other directions
    for dir = 0, 3 do
        if dir ~= original_direction then
            table.insert(direction_priority, dir)
        end
    end
    
    -- Add standard adjacent positions with different directions
    for _, direction in pairs(direction_priority) do
        for distance = 1, 3 do  -- Try increasing distances
            local offset_x, offset_y = 0, 0
            
            if direction == 0 then     -- North
                offset_y = -distance
            elseif direction == 1 then -- East
                offset_x = distance
            elseif direction == 2 then -- South
                offset_y = distance
            else                       -- West
                offset_x = -distance
            end
            
            local alt_pos = {
                x = ref_position.x + offset_x,
                y = ref_position.y + offset_y
            }
            
            local score = 30 - (distance * 5)  -- Prefer closer positions
            
            table.insert(alternatives, {
                position = alt_pos,
                direction = direction,
                score = score,
                reason = "Alternative position at distance " .. distance
            })
        end
    end
    
    -- Sort by score (highest first)
    table.sort(alternatives, function(a, b) return a.score > b.score end)
    
    return alternatives
end

local function validate_mining_drill_placement(surface, position, entity_name)
    -- Check if the entity is a mining drill
    local prototype = prototypes.entity[entity_name]
    if prototype.type ~= "mining-drill" then
        return true
    end

    -- Get the mining area
    local mining_area = prototype.collision_box
    local area = {
        {position.x + mining_area.left_top.x, position.y + mining_area.left_top.y},
        {position.x + mining_area.right_bottom.x, position.y + mining_area.right_bottom.y}
    }

    -- Check for resources in the mining area
    local resources = surface.find_entities_filtered({
        area = area,
        type = "resource"
    })

    -- For mining drills, we need at least one valid resource
    return #resources > 0
end


storage.actions.place_entity_next_to = function(player_index, entity, ref_x, ref_y, direction, gap)
    -- Ensure we have a valid character, recreating if necessary
    local player = storage.utils.ensure_valid_character(player_index)
    local ref_position = {x = ref_x, y = ref_y}

    local function table_contains(tbl, element)
        for _, value in ipairs(tbl) do
            if value == element then
                return true
            end
        end
        return false
    end

    local valid_directions = {0, 1, 2, 3}  -- 0: North, 1: East, 2: South, 3: West

    if not table_contains(valid_directions, direction) then
        error("Invalid direction " .. direction .. " provided. Please use 0 (north), 1 (east), 2 (south), or 3 (west).")
    end

    local ref_entities = player.surface.find_entities_filtered({
        area = {{ref_x - 0.5, ref_y - 0.5}, {ref_x + 0.5, ref_y + 0.5}},
        type = {"character", "resource"}, -- Find players
        invert = true
    })
    local ref_entity = #ref_entities > 0 and ref_entities[1] or nil

    local function is_transport_belt(entity_name)
        return entity_name == "transport-belt" or
               entity_name == "fast-transport-belt" or
               entity_name == "express-transport-belt"
    end


    local function calculate_position(direction, ref_pos, ref_entity, gap, is_belt, entity_to_place)
        local new_pos = {x = ref_pos.x, y = ref_pos.y}
        local effective_gap = gap or 0

        -- Get reference entity's width/height based on its rotation
        local ref_width, ref_height
        if ref_entity then
            if ref_entity.type == "inserter" then
                ref_width, ref_height = 1, 1
            else
                local ref_orientation = ref_entity.direction
                if ref_orientation == 2 or ref_orientation == 6 then  -- East or West
                    ref_width = ref_entity.prototype.tile_height
                    ref_height = ref_entity.prototype.tile_width
                else  -- North or South
                    ref_width = ref_entity.prototype.tile_width
                    ref_height = ref_entity.prototype.tile_height
                end
            end
        else
            ref_width = 1
            ref_height = 1
        end

        -- Check if the entity to place is an inserter
        local entity_prototype = prototypes.entity[entity_to_place]
        -- Original spacing calculation for non-inserters
        local entity_width, entity_height
        if direction == 1 or direction == 3 then  -- East or West
            entity_width = entity_prototype.tile_height
            entity_height = entity_prototype.tile_width
        else  -- North or South
            entity_width = entity_prototype.tile_width
            entity_height = entity_prototype.tile_height
        end

        if direction == 0 then     -- North
            new_pos.y = new_pos.y - (math.ceil(ref_height + entity_height)/2 + effective_gap)
        elseif direction == 1 then -- East
            new_pos.x = new_pos.x + (math.ceil(ref_width + entity_width)/2 + effective_gap)
        elseif direction == 2 then -- South
            new_pos.y = new_pos.y + (math.ceil(ref_height + entity_height)/2 + effective_gap)
        else  -- West
            new_pos.x = new_pos.x - (math.ceil(ref_width + entity_width)/2 + effective_gap)
        end

        -- Round the position to the nearest 0.5 to align with Factorio's grid
        new_pos.x = math.ceil(new_pos.x * 2) / 2
        new_pos.y = math.ceil(new_pos.y * 2) / 2

        return new_pos
    end

    local function calculate_position_old(direction, ref_pos, ref_entity, gap, is_belt, entity_to_place)
        local new_pos = {x = ref_pos.x, y = ref_pos.y}
        local effective_gap = gap or 0

        -- Get reference entity's width/height based on its rotation
        local ref_width, ref_height
        if ref_entity then
            local ref_orientation = ref_entity.direction  -- Factorio 2.0: 0,4,8,12 = N,E,S,W
            if ref_orientation == defines.direction.east or ref_orientation == defines.direction.west then  -- East or West
                ref_width = ref_entity.prototype.tile_height
                ref_height = ref_entity.prototype.tile_width
            else  -- North or South
                ref_width = ref_entity.prototype.tile_width
                ref_height = ref_entity.prototype.tile_height
            end
        else
            ref_width = 1
            ref_height = 1
        end

        -- Get entity to place width/height based on desired direction
        local entity_prototype = prototypes.entity[entity_to_place]
        local entity_width, entity_height
        if direction == 1 or direction == 3 then  -- East or West
            entity_width = entity_prototype.tile_height
            entity_height = entity_prototype.tile_width
        else  -- North or South
            entity_width = entity_prototype.tile_width
            entity_height = entity_prototype.tile_height
        end

        -- Calculate spacing based on the relevant dimensions
        if direction == 0 then     -- North
            new_pos.y = new_pos.y - (math.ceil(ref_height + entity_height)/2 + effective_gap)
        elseif direction == 1 then -- East
            new_pos.x = new_pos.x + (math.ceil(ref_width + entity_width)/2 + effective_gap)
        elseif direction == 2 then -- South
            new_pos.y = new_pos.y + (math.ceil(ref_height + entity_height)/2 + effective_gap)
        else  -- West
            new_pos.x = new_pos.x - (math.ceil(ref_width + entity_width)/2 + effective_gap)
        end

        -- Round the position to the nearest 0.5 to align with Factorio's grid
        new_pos.x = math.ceil(new_pos.x * 2) / 2
        new_pos.y = math.ceil(new_pos.y * 2) / 2

        return new_pos
    end

    local is_belt = is_transport_belt(entity)

    local new_position = calculate_position(direction, ref_position, ref_entity, gap, is_belt, entity)
    
    -- Helper function to clear item-on-ground entities at a position
    local function clear_items_on_ground(position, radius)
        local items = player.surface.find_entities_filtered{
            position = position,
            radius = radius or 0.5,
            name = "item-on-ground"
        }
        for _, item in ipairs(items) do
            item.destroy()
        end
    end
    
    -- Clear any item-on-ground entities at the target position before collision check
    clear_items_on_ground(new_position)

    local function player_collision(player, target_area)
        local character_box = {
            left_top = {x = -0.2, y = -0.2},
            right_bottom = {x = 0.2, y = 0.2}
        }
        local character_area = {
            {player.position.x + character_box.left_top.x, player.position.y + character_box.left_top.y},
            {player.position.x + character_box.right_bottom.x, player.position.y + character_box.right_bottom.y}
        }
        return (character_area[1][1] < target_area[2][1] and character_area[2][1] > target_area[1][1]) and
               (character_area[1][2] < target_area[2][2] and character_area[2][2] > target_area[1][2])
    end

    local nearby_entities = player.surface.find_entities_filtered({
        position = new_position,
        radius = 0.5,
        force = player.force
    })

    -- Smart collision resolution with alternative positioning
    if #nearby_entities > 0 then
        local colliding_entity_names = {}
        local has_pole_collision = false
        
        for _, nearby_entity in pairs(nearby_entities) do
            if nearby_entity.name ~= 'laser-beam' and nearby_entity.name ~= "character" then
                table.insert(colliding_entity_names, nearby_entity.name)
                if nearby_entity.type == "electric-pole" then
                    has_pole_collision = true
                end
            end
        end
        
        if #colliding_entity_names > 0 then
            -- Try to find alternative positions, especially for inserters and common factory entities
            local should_try_alternatives = (
                entity == "inserter" or entity:find("inserter") or
                entity == "wooden-chest" or entity == "iron-chest" or entity == "steel-chest" or
                is_transport_belt(entity) or
                has_pole_collision  -- Always try alternatives when blocked by poles
            )
            
            if should_try_alternatives then
                local alternatives = find_alternative_position_smart(ref_position, ref_entity, entity, direction, gap)
                
                for i, alternative in pairs(alternatives) do
                    local alt_pos = alternative.position
                    -- Round to grid
                    alt_pos.x = math.ceil(alt_pos.x * 2) / 2
                    alt_pos.y = math.ceil(alt_pos.y * 2) / 2
                    
                    -- Clear items at alternative position before checking if it's clear
                    clear_items_on_ground(alt_pos)
                    
                    -- Use proper collision detection instead of radius search
                    local alt_clear = player.surface.can_place_entity({
                        name = entity,
                        position = alt_pos,
                        direction = storage.utils.get_entity_direction(entity, alternative.direction),
                        force = player.force
                    })
                    
                    if alt_clear then
                        -- Found a good alternative position!
                        new_position = alt_pos
                        direction = alternative.direction
                        
                        -- Update orientation for the new direction
                        orientation = storage.utils.get_entity_direction(entity, direction)
                        
                        
                        goto alternative_found
                    end
                end
            end
            
            -- If no alternatives worked, give the original error with suggestions
            local colliding_entity_name
            if #colliding_entity_names == 1 then
                colliding_entity_name = colliding_entity_names[1]
            elseif #colliding_entity_names == 2 then
                colliding_entity_name = table.concat(colliding_entity_names, " and ")
            else
                colliding_entity_name = table.concat(colliding_entity_names, ", ", 1, #colliding_entity_names - 1) .. ", and " .. colliding_entity_names[#colliding_entity_names]
            end
            
            local suggestions = ""
            if ref_entity and is_large_entity(ref_entity) then
                suggestions = " For large entities like " .. ref_entity.type .. ", consider using the middle sides (N/S/E/W) for inserters and chests, and corners for poles."
            elseif has_pole_collision then
                suggestions = " Consider using connect_entities to place poles in better positions, or manually place the pole elsewhere first."
            end
            
            error("\"A " .. colliding_entity_name .. " already exists at the new position " .. serpent.line(new_position) .. ". Consider increasing the spacing (".. gap.."), changing the direction or changing the reference position (" .. serpent.line(ref_position) .. ")." .. suggestions .. "\"")
        end
    end
    
    ::alternative_found::

    orientation = storage.utils.get_entity_direction(entity, direction)

    if ref_entity then
        local prototype = prototypes.entity[ref_entity.name]
        local collision_box = prototype.collision_box
        local width = math.abs(collision_box.right_bottom.x - collision_box.left_top.x)
        local height = math.abs(collision_box.right_bottom.y - collision_box.left_top.y)

        local target_area = {
            {new_position.x - width / 2, new_position.y - height / 2},
            {new_position.x + width / 2, new_position.y + height / 2}
        }
        while player_collision(player, target_area) do
            player.teleport({player.position.x + width + 1, player.position.y})
        end
    end

    -- Check for player collision and move player if necessary
    local entity_prototype = prototypes.entity[entity]
    local entity_box = entity_prototype.collision_box
    local entity_width = 1
    local entity_height = 1
    if orientation == defines.direction.north or orientation == defines.direction.south then
        entity_width = math.abs(entity_box.right_bottom.x - entity_box.left_top.x)
        entity_height = math.abs(entity_box.right_bottom.y - entity_box.left_top.y)
    else
        entity_height = math.abs(entity_box.right_bottom.x - entity_box.left_top.x)
        entity_width = math.abs(entity_box.right_bottom.y - entity_box.left_top.y)
    end


    local target_area = {
        {new_position.x - entity_width / 2, new_position.y - entity_height / 2},
        {new_position.x + entity_width / 2, new_position.y + entity_height / 2}
    }

    if player_collision(player, target_area) then
        local move_distance = math.max(entity_width, entity_height) + 1
        local move_direction = {x = 0, y = 0}

        if direction == 0 or direction == 2 then -- North or South
            move_direction.x = 1 -- Move East
        else -- East or West
            move_direction.y = 1 -- Move South
        end

        local new_player_position = {
            x = player.position.x + move_direction.x * move_distance,
            y = player.position.y + move_direction.y * move_distance
        }
        player.teleport(new_player_position)
    end

    local area = {{new_position.x - entity_width / 2, new_position.y - entity_height / 2}, {new_position.x + entity_width / 2, new_position.y + entity_height / 2}}

    -- Show bounding box for debugging
    rendering.draw_rectangle({
        only_in_alt_mode=true,
        color = {r = 0, g = 1, b = 0},
        filled = false,
        left_top = area[1],
        right_bottom = area[2],
        surface = player.surface,
        time_to_live = 60000
    })
    rendering.draw_circle({
        only_in_alt_mode=true,
        color = {r = 1, g = 0, b = 0},
        radius = 0.2,
        filled = true,
        target = new_position,
        surface = player.surface,
        time_to_live = 60000
    })
    rendering.draw_circle({
        only_in_alt_mode=true,
        color = {r = 0, g = 0, b = 1},
        radius = 0.2,
        filled = true,
        target = ref_position,
        surface = player.surface,
        time_to_live = 60000
    })

    storage.utils.avoid_entity(player_index, entity, new_position, direction)

    local can_build = player.surface.can_place_entity({
        name = entity,
        position = new_position,
        direction = orientation,
        force = player.force
    })
    if can_build then
        can_build = validate_mining_drill_placement(player.surface, new_position, entity)
        if not can_build then
            error("Cannot place mining drill - no resources found in mining area")
        end
    else
        local entities = player.surface.find_entities_filtered{area = area, type = {"beam", "resource", "player", "character"}, invert=true}
        local blocker_names = {}
        for _, e in ipairs(entities) do
            table.insert(blocker_names, e.type.."("..serpent.line(e.position)..")")
        end
        -- game.print(serpent.line(blocker_names))

        local tree = player.surface.find_entities_filtered{area = area, type = {"tree"}}
        for _, e in ipairs(tree) do
            table.insert(blocker_names, e.name.."("..serpent.line(e.position)..")")
        end
        
        local tiles = player.surface.find_tiles_filtered{area = area, name={"water", "deepwater", "water-green", "deepwater-green", "water-shallow", "water-mud"}}
        if #tiles > 0 then
            for _, e in ipairs(tiles) do
                -- if e.name is not in blocker_names, we should add item
                if not table_contains(blocker_names, e.name.."("..serpent.line(e.position)..")") then
                    table.insert(blocker_names, e.name.."("..serpent.line(e.position)..")")
                end
            end
        end
        -- game.print(serpent.line(blocker_names))

        error("\'Cannot place entity at the position " .. serpent.line(new_position) .. " with the current direction" ..
              ". Attempting to place next to - "..ref_entity.name..". There might be a collision with existing entities or this area cannot be placed on (water). Nearby entities that might be blocking the placement - " .. serpent.line(blocker_names) ..
                ". Consider increasing the spacing (".. gap.."), changing the direction or changing the reference position (" .. serpent.line(ref_position) .. ")\'")

    end

    local new_entity = player.surface.create_entity({
        name = entity,
        position = new_position,
        force = player.force,
        direction = orientation,
        move_stuck_players = true,
    })

    if not new_entity then
        error("Failed to create entity " .. entity .. " at position " .. serpent.line(new_position))
    end

    local placement_info = storage.utils.serialize_entity(new_entity)
    
    local item_stack = {name = entity, count = 1}
    if player.get_main_inventory().can_insert(item_stack) then
        player.get_main_inventory().remove(item_stack)
        return placement_info
    else
        error("Not enough items in inventory.")
    end
end
