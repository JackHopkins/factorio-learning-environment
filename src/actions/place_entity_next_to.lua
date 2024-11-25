global.actions.place_entity_next_to = function(player_index, entity, ref_x, ref_y, direction, gap)
    local player = game.get_player(player_index)
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
            local ref_orientation = ref_entity.direction  -- 0,2,4,6 = N,E,S,W
            if ref_orientation == 2 or ref_orientation == 6 then  -- East or West
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
        local entity_prototype = game.entity_prototypes[entity_to_place]
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

    local function calculate_position2(direction, ref_pos, ref_entity, gap, is_belt, entity_to_place)
        local new_pos = {x = ref_pos.x, y = ref_pos.y}
        local effective_gap = gap

        local ref_size = {x = 1, y = 1}
        if ref_entity then
            local ref_orientation = ref_entity.direction  -- Convert to 0-7 system
            game.print("ref_orientation: " .. ref_orientation)
            local is_rotated = (ref_orientation == 2 or ref_orientation == 6)  -- East or West
            ref_size = {
                x = is_rotated and ref_entity.prototype.tile_height or ref_entity.prototype.tile_width,
                y = is_rotated and ref_entity.prototype.tile_width or ref_entity.prototype.tile_height
            }
        end

        local entity_size = {x = 1, y = 1}
        local entity_prototype = game.entity_prototypes[entity_to_place]
        if entity_prototype then
            local entity_bounding_box = entity_prototype.collision_box
            --entity_size = {
            --    x = entity_bounding_box.right_bottom.x - entity_bounding_box.left_top.x,
            --    y = entity_bounding_box.right_bottom.y - entity_bounding_box.left_top.y
            --}
            --entity_size = {
            --    x = entity_prototype.tile_width,
            --    y = entity_prototype.tile_height
            --}
            local is_rotated = (direction == 1 or direction == 3)  -- East or West
            entity_size = {
                x = is_rotated and entity_prototype.tile_height or entity_prototype.tile_width,
                y = is_rotated and entity_prototype.tile_width or entity_prototype.tile_height
            }
        end

        -- Ensure we have valid sizes
        ref_size.x = math.max(ref_size.x, 1)
        ref_size.y = math.max(ref_size.y, 1)
        entity_size.x = math.max(entity_size.x, 1)
        entity_size.y = math.max(entity_size.y, 1)

        if direction == 0 then     -- North
            new_pos.y = new_pos.y - ref_size.y / 2 - entity_size.y / 2 - effective_gap
            --new_pos.x = new_pos.x - 0.5
        elseif direction == 1 then -- East
            new_pos.x = new_pos.x + ref_size.x / 2 + entity_size.x / 2 + effective_gap
            --new_pos.y = new_pos.y - 0.5
        elseif direction == 2 then -- South
            new_pos.y = new_pos.y + ref_size.y / 2 + entity_size.y / 2 + effective_gap
            --new_pos.x = new_pos.x - 0.5
        else  -- West
            new_pos.x = new_pos.x - ref_size.x / 2 - entity_size.x / 2 - effective_gap
        end

        -- Round the position to the nearest 0.5 to align with Factorio's grid
        new_pos.x = math.ceil(new_pos.x * 2) / 2
        new_pos.y = math.ceil(new_pos.y * 2) / 2

        return new_pos
    end

    local is_belt = is_transport_belt(entity)

    local new_position = calculate_position(direction, ref_position, ref_entity, gap, is_belt, entity)
    --game.print("new_position: " .. serpent.line(new_position))
    --create_beam_point_with_direction(player, direction, new_position)

    local function player_collision(player, target_area)
        --local character_box = player.character.prototype.collision_box
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

    if #nearby_entities > 0 then
        local colliding_entity_names = {}
        for _, nearby_entity in pairs(nearby_entities) do
            if nearby_entity.name ~= 'laser-beam' and nearby_entity.name ~= "character" then
                table.insert(colliding_entity_names, nearby_entity.name)
            end
        end
        if #colliding_entity_names > 0 then
            local colliding_entity_name
            if #colliding_entity_names == 1 then
                colliding_entity_name = colliding_entity_names[1]
            elseif #colliding_entity_names == 2 then
                colliding_entity_name = table.concat(colliding_entity_names, " and ")
            else
                colliding_entity_name = table.concat(colliding_entity_names, ", ", 1, #colliding_entity_names - 1) .. ", and " .. colliding_entity_names[#colliding_entity_names]
            end
            error("\"A " .. colliding_entity_name .. " already exists at the new position " .. serpent.line(new_position) .. ".\"")
        end
    end

    local orientation = global.utils.get_entity_direction(entity, direction)

    if ref_entity then
        local prototype = game.entity_prototypes[ref_entity.name]
        local collision_box = prototype.collision_box
        local width = math.abs(collision_box.right_bottom.x - collision_box.left_top.x)
        local height = math.abs(collision_box.right_bottom.y - collision_box.left_top.y)

        local target_area = {
            {new_position.x - width / 2, new_position.y - height / 2},
            {new_position.x + width / 2, new_position.y + height / 2}
        }
        while player_collision(player, target_area) do
            player.teleport({player.position.x + width + 1, player.position.y}, player.surface)
        end
    end

    -- Check for player collision and move player if necessary
    local entity_prototype = game.entity_prototypes[entity]
    local entity_box = entity_prototype.collision_box
    local entity_width = math.abs(entity_box.right_bottom.x - entity_box.left_top.x)
    local entity_height = math.abs(entity_box.right_bottom.y - entity_box.left_top.y)

    local target_area = {
        {new_position.x - entity_width / 2, new_position.y - entity_height / 2},
        {new_position.x + entity_width / 2, new_position.y + entity_height / 2}
    }

    if player_collision(player, target_area) then
        game.print("Player is colliding with the target area. Moving player.")
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
        player.teleport(new_player_position, player.surface)
    end

    local can_build = player.surface.can_place_entity({
        name = entity,
        position = new_position,
        direction = orientation,
        force = player.force
    })

    -- Modify the error message in the can_build check
    if not can_build then
        local area = {{new_position.x - 1, new_position.y - 1}, {new_position.x + 1, new_position.y + 1}}
        local entities = player.surface.find_entities_filtered{area = area, type = {"beam", "resource", "player"}, invert=true}
        local entity_names = {}
        for _, e in ipairs(entities) do
            game.print(e.type)
            table.insert(entity_names, e.name)
        end
        error("\'Cannot place entity at the position " .. serpent.line(new_position) .. " with direction " ..
              serpent.line(orientation) .. ". Attempting to place next to: "..ref_entity.name..". Nearby entities: " .. serpent.line(entity_names).."\'")
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

    local item_stack = {name = entity, count = 1}
    if player.get_main_inventory().can_insert(item_stack) then
        player.get_main_inventory().remove(item_stack)
        return global.utils.serialize_entity(new_entity)
    else
        error("Not enough items in inventory.")
    end
end
