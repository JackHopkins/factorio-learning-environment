local function player_collision(player, target_area)
        local character_box = player.character.prototype.collision_box
        local character_area = {
            {player.position.x + character_box.left_top.x, player.position.y + character_box.left_top.y},
            {player.position.x + character_box.right_bottom.x, player.position.y + character_box.right_bottom.y}
        }
        return (character_area[1][1] < target_area[2][1] and character_area[2][1] > target_area[1][1]) and
               (character_area[1][2] < target_area[2][2] and character_area[2][2] > target_area[1][2])
    end

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

    local factorio_direction = direction * 2  -- Convert to Factorio's 0-7 system

    local entity_prototype = game.entity_prototypes[entity]
    local ref_entities = player.surface.find_entities_filtered({
        area = {{ref_x - 0.5, ref_y - 0.5}, {ref_x + 0.5, ref_y + 0.5}}
    })
    local ref_entity = #ref_entities > 0 and ref_entities[1] or nil

    local function is_transport_belt(entity_name)
        return entity_name == "transport-belt" or
               entity_name == "fast-transport-belt" or
               entity_name == "express-transport-belt"
    end

    local function calculate_position(direction, ref_pos, ref_entity, gap, is_belt, entity_to_place)
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
        game.print("ref_size: " .. serpent.line(ref_size))
        game.print("entity_size: " .. serpent.line(entity_size))
        game.print("effective_gap: " .. effective_gap)
        game.print("direction: " .. direction)

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

    local function calculate_position2(direction, ref_pos, ref_entity, gap, is_belt, entity_to_place)
        local new_pos = {x = ref_pos.x, y = ref_pos.y}
        local effective_gap = gap

        local ref_size = {x = 1, y = 1}
        if ref_entity then
            local ref_bounding_box = ref_entity.prototype.collision_box
            ref_size = {
                x = ref_bounding_box.right_bottom.x - ref_bounding_box.left_top.x,
                y = ref_bounding_box.right_bottom.y - ref_bounding_box.left_top.y
            }
        end

        local entity_size = {x = 1, y = 1}
        local entity_prototype = game.entity_prototypes[entity_to_place]
        if entity_prototype then
            local entity_bounding_box = entity_prototype.collision_box
            entity_size = {
                x = entity_bounding_box.right_bottom.x - entity_bounding_box.left_top.x,
                y = entity_bounding_box.right_bottom.y - entity_bounding_box.left_top.y
            }
        end

        if direction == 0 then     -- North
            new_pos.y = new_pos.y - ref_size.y / 2 - entity_size.y / 2 - effective_gap - 0.5
        elseif direction == 1 then -- East
            new_pos.x = new_pos.x + ref_size.x / 2 + entity_size.x / 2 + effective_gap
        elseif direction == 2 then -- South
            new_pos.y = new_pos.y + ref_size.y / 2 + entity_size.y / 2 + effective_gap
        else                       -- West
            new_pos.x = new_pos.x - ref_size.x / 2 - entity_size.x / 2 - effective_gap - 0.5
        end

        -- Round the position to the nearest 0.5 to align with Factorio's grid
        new_pos.x = math.floor(new_pos.x * 2 + 0.5) / 2
        new_pos.y = math.floor(new_pos.y * 2 + 0.5) / 2

        return new_pos
    end

    local is_belt = is_transport_belt(entity)

    local new_position = calculate_position(direction, ref_position, ref_entity, gap, is_belt, entity)
    game.print("new_position: " .. serpent.line(new_position))
    create_beam_point_with_direction(player, direction, new_position)

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
            error("A " .. colliding_entity_name .. " already exists at the new position " .. serpent.line(new_position) .. ".")
        end
    end
    --
    --local orientation = factorio_direction
    --if entity == "fast-inserter" or entity == "burner-inserter" or entity == "inserter" or entity == "long-handed-inserter" then
    --    -- Adjust orientation for inserters if necessary
    --    local inserter_direction_map = {defines.direction.south, defines.direction.west, defines.direction.north, defines.direction.east}
    --    orientation = inserter_direction_map[direction + 1 % 4]
    --end
    local orientation = global.utils.get_entity_direction(entity, direction)
    game.print("orientation: " .. orientation)

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
        local entities = player.surface.find_entities_filtered{area = area, type = {"beam", "resource"}, invert=true}
        local entity_names = {}
        for _, e in ipairs(entities) do
            game.print(e.type)
            table.insert(entity_names, e.name)
        end
       -- error("Cannot place entity at the position " .. serpent.line(new_position) .. " with direction " ..
        --      serpent.line(orientation) .. ". Nearby entities: " .. serpent.line(entity_names))
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

global.actions.place_entity_next_to_9 = function(player_index, entity, ref_x, ref_y, direction, gap)
    --- Places an entity next to a reference entity:
    --- Find the reference entity at (ref_x, ref_y)
    --- If there is a reference entity, find the edge of the entity in the `direction`, take a step of size `gap` before placing the entity.
    --- If there is not a reference entity, take a step of size `gap` from the (ref_x, ref_y) position.
    --- Before placing the entity, check to see if an entity exists at this new position (If so, raise an `error`)
    --- If there is no error, place the entity and remove the item from the inventory.
    --- Return the resultant ent    ity by calling the `global.utils.serialize_entity(new_entity)` method.
    ---
    --- @param player_index number
    --- @param entity string
    --- @param ref_x number
    --- @param ref_y number
    --- @param direction defines.direction
    --- @param gap number
    --- @return boolean
    ---
    local player = game.get_player(player_index)
    local ref_position = {x = ref_x, y = ref_y}
    --game.print("Direction " .. direction)
    --local direction_map = {defines.direction.north, defines.direction.south, defines.direction.west, defines.direction.east}

    local function table_contains(tbl, element)
        for _, value in ipairs(tbl) do
            if value == element then
                return true
            end
        end
        return false
    end


    ---
    --- North - 0
    --- Northeast - 1
    --- East - 2
    --- Southeast - 3
    --- South - 4
    --- Southwest - 5
    --- West - 6
    --- Northwest - 7

    ---local direction_map = {defines.direction.south, defines.direction.north, defines.direction.east, defines.direction.west}
    --local direction_map = {defines.direction.north, defines.direction.east, defines.direction.south, defines.direction.west}

    -- Inserters have upside down directions, weirdly
    --local inserter_direction_map = {defines.direction.south, defines.direction.west, defines.direction.north, defines.direction.east}
    --- For inserters
    ---    Place entity DOWN - 0 => UP
    ---   Place entity LEFT - 2
    ---    Place entity RIGHT - 4 => LEFT
    ---    Place entity UP - 6 => LEFT
    ---

    --local valid_directions = {0, 2, 4, 6}
    local valid_directions = {0, 1, 2, 3}  -- Factorio uses 0-7, but we're using 0-3 from Python

    if not table_contains(valid_directions, direction) then
        error("\"Invalid direction "..(direction).." provided. Please use 0 (north), 2 (east), 4 (south), or 6 (west).\"")
    end

    local entity_prototype = game.entity_prototypes[entity]
    -- local ref_entity = player.surface.find_entity(entity, ref_position)
    -- Find the reference entity at (ref_x, ref_y) with a bounding box of size (1, 1)
    local ref_entities = player.surface.find_entities_filtered({
        area = {
            {ref_x - 0.5, ref_y - 0.5},
            {ref_x + 0.5, ref_y + 0.5}
        }
    })
    local ref_entity = nil
    if #ref_entities > 0 then
        ref_entity = ref_entities[1]
    end

    --game.print("ref_entity: " .. serpent.line(ref_entity))
    --game.print("ref_position: " .. serpent.line(ref_position))
    local new_position = {y = ref_y, x = ref_x}
    local entity_size = {
        x = entity_prototype.tile_width,
        y = entity_prototype.tile_height
    }

    local function player_collision(player, target_area)
        local character_box = player.character.prototype.collision_box
        local character_area = {
            {player.position.x + character_box.left_top.x, player.position.y + character_box.left_top.y},
            {player.position.x + character_box.right_bottom.x, player.position.y + character_box.right_bottom.y}
        }
        return (character_area[1][1] < target_area[2][1] and character_area[2][1] > target_area[1][1]) and
                (character_area[1][2] < target_area[2][2] and character_area[2][2] > target_area[1][2])
    end

    if ref_entity then
        local ref_bounding_box = ref_entity.prototype.collision_box
        local ref_size = {
            x = ref_bounding_box.right_bottom.x - ref_bounding_box.left_top.x,
            y = ref_bounding_box.right_bottom.y - ref_bounding_box.left_top.y
        }
        --    UP = NORTH = 0
        --    RIGHT = EAST = 1
        --    LEFT = WEST = 3
        --    DOWN = BELOW = BOTTOM = 2

        if direction == 0 then
            new_position.y = new_position.y - ref_size.y - ( gap) -- entity_size.y
        elseif direction == 2 then
            new_position.y = new_position.y + ref_size.y + ( gap)
        elseif direction == 1 then
            new_position.x = new_position.x + ref_size.x + ( gap)
        else
            new_position.x = new_position.x - ref_size.x - ( gap)
        end
    else
        if direction == 0 then
            new_position.y = new_position.y - (1 + gap) -- entity_size.y
        elseif direction == 2 then
            new_position.y = new_position.y + (1 + gap)
        elseif direction == 1 then
            new_position.x = new_position.x + (1 + gap)-- + entity_size.x
        else -- direction == defines.direction.west
            new_position.x = new_position.x - (1 + gap)-- - entity_size.x
        end
    end

    -- Check if there's an entity at the new position
    --if player.surface.find_entity(entity, new_position) then
    --    error("An entity already exists at the new position " .. serpent.line(new_position) .. ".")
    --end
    local nearby_entities = player.surface.find_entities_filtered({position=new_position,
        --radius=0.707, -- sqrt(0.5^2 + 0.5^2)
                                                                   radius=0.5,
                                                                   force = player.force})
    if #nearby_entities > 0 then
        colliding_entity_names  = {}
        for _, nearby_entity in pairs(nearby_entities) do
            if nearby_entity.name ~= "character" and nearby_entity.name ~= 'laser-beam' then
                table.insert(colliding_entity_names, nearby_entity.name)
            end
        end
        if #colliding_entity_names > 0 then
            local colliding_entity_name = nil
            if #colliding_entity_names == 1 then
                colliding_entity_name = colliding_entity_names[1]
            elseif #colliding_entity_names == 2 then
                colliding_entity_name = table.concat(colliding_entity_names, " and ")
            else
                -- commas separate all but the last two items, which are separated by "and"
                colliding_entity_name = table.concat(colliding_entity_names, ", ", 1, #colliding_entity_names - 1) .. ", and " .. colliding_entity_names[#colliding_entity_names]
            end
            error("A "..colliding_entity_name.." already exists at the new position " .. serpent.line(new_position) .. ".")
        end
    end

    -- if entity is an inserter, get the direction from the inserter_direction_map
    local orientation
    game.print("entity: " .. entity)
    if entity == "fast-inserter" or entity == "burner-inserter" or entity == "inserter" or entity == "long-handed-inserter" then
        --orientation = inserter_direction_map[direction+1] -- 1 based index
        orientation = inserter_direction_map[direction+1 % 4]
        game.print("orientation: " .. orientation .. " direction: " .. direction)

    elseif entity == 'stone-furnace' or entity == 'steel-furnace' or entity == 'electric-furnace' then
        orientation = direction_map[direction+1 % 4] -- 1 based index
    else
        orientation = direction_map[direction+1 % 4] -- 1 based index
    end
--    orientation = inserter_direction_map[direction+1] -- 1 based index

    if ref_entity then
        local prototype = game.entity_prototypes[ref_entity.name]
        local collision_box = prototype.collision_box
        local width = math.abs(collision_box.right_bottom.x - collision_box.left_top.x)
        local height = math.abs(collision_box.right_bottom.y - collision_box.left_top.y)

        local target_area = {
            {new_position.x - width, new_position.y - height},
            {new_position.x + width, new_position.y + height}
        }
        game.print("target_area: " .. serpent.line(target_area))
        while player_collision(player, target_area) do
            game.print("Player is colliding with the target area. Moving player.")
            player.teleport({player.position.x + width + 1, player.position.y}, player.surface)
        end
    end

    -- Check to see if can create the entity at the new position
    local can_build = player.surface.can_place_entity({
        name = entity,
        position = new_position,
        direction = orientation,
        force = player.force
    })
    -- create laser direction beam
    --create_beam_point_with_direction(player, orientation, ref_position)
    game.print("ref_position: " .. serpent.line(ref_position) .. " new_position: " .. serpent.line(new_position) .. " direction: " .. serpent.line(orientation))
    can_build = true
    if not can_build then
        error("Cannot place entity at the position " .. serpent.line(new_position) .. " with direction " .. serpent.line(direction) .. "." )
    end



    -- Place the entity and remove the item from the inventory
    local new_entity = player.surface.create_entity({
        name = entity,
        position = new_position,
        force = player.force,
        direction = orientation,
        move_stuck_players = true,
    })

    -- if entity is an inserter, create a beam pointing to the inserter drop position
    if entity == "fast-inserter" or entity == "burner-inserter" or entity == "inserter" or entity == "long-handed-inserter" then
        --create_beam_point_with_direction(player, orientation, new_entity.drop_position)
    end

    -- Remove the item from the player's inventory
    local item_stack = {name = entity, count = 1}
    if player.get_main_inventory().can_insert(item_stack) then
        player.get_main_inventory().remove(item_stack)
        -- Return the resultant entity
        return global.utils.serialize_entity(new_entity)
    else
        error("Not enough items in inventory.")
    end
end


global.actions.place_entity_next_to_8 = function(player_index, entity, ref_x, ref_y, direction, gap)
    --- Places an entity next to a reference entity.
    --- @param player_index number
    --- @param entity string
    --- @param ref_x number
    --- @param ref_y number
    --- @param direction defines.direction
    --- @param gap number
    --- @return boolean
    ---
    local player = game.get_player(player_index)
    local ref_position = {x = ref_x, y = ref_y}
    local cardinals = {defines.direction.north, defines.direction.south, defines.direction.east, defines.direction.west}
    local entity_prototype = game.entity_prototypes[entity]

    local function clear_items(surface, area)
        local items = surface.find_entities_filtered{area = area, type = "item-entity"}
        for _, item in pairs(items) do
            item.destroy()
        end
    end

    local surface = player.surface
    local ref_entities = player.surface.find_entities_filtered{area = {{ref_position.x - 0.5, ref_position.y - 0.5}, {ref_position.x + 0.5, ref_position.y + 0.5}}}
    -- local ref_entities = player.surface.find_entities_filtered{name=entity, position=ref_position, radius=2}
    local ref_entity = ref_entities[1]
    local target_position

    if ref_entity then
        local ref_bb = ref_entity.prototype.selection_box
        local entity_bb = entity_prototype.selection_box
        local dx, dy
        local ref_height = ref_bb.right_bottom.y - ref_bb.left_top.y
        local ref_width = ref_bb.right_bottom.x - ref_bb.left_top.x
        game.print("ref_height: " .. ref_height)
        game.print("ref_width: " .. ref_width)
        game.print("ref_tile_width: " .. ref_entity.prototype.tile_width)
        game.print("ref_tile_height: " .. ref_entity.prototype.tile_height)

        --- THIS HAS A BUG IN IT
        if direction == 1 then -- North
            dx = 0
            dy = -(ref_bb.right_bottom.y - ref_bb.left_top.y + entity_bb.right_bottom.y - entity_bb.left_top.y - ref_entity.prototype.tile_height/2 + gap)
        elseif direction == 2 then -- South
            dx = 0
            dy = (ref_bb.right_bottom.y - ref_bb.left_top.y + entity_bb.right_bottom.y - entity_bb.left_top.y - ref_entity.prototype.tile_height/2 + gap + (1-ref_height))
        elseif direction == 3 then -- East
            dx = (ref_bb.right_bottom.x - ref_bb.left_top.x + entity_bb.right_bottom.x - entity_bb.left_top.x -  ref_entity.prototype.tile_width/2 + gap + (1-ref_width))
            dy = 0
        else -- West
            dx = -(ref_bb.right_bottom.x - ref_bb.left_top.x + entity_bb.right_bottom.x - entity_bb.left_top.x - ref_entity.prototype.tile_width/2 + gap)
            dy = 0
        end
        ---

    if direction == 1 then -- North
        dx = 0
        dy = -(ref_height / 2 + entity_bb.right_bottom.y - entity_bb.left_top.y / 2 + gap)
    elseif direction == 2 then -- South
        dx = 0
        dy = ref_height / 2 + entity_bb.right_bottom.y - entity_bb.left_top.y / 2 + gap
    elseif direction == 3 then -- East
        dx = ref_width / 2 + entity_bb.right_bottom.x - entity_bb.left_top.x / 2 + gap
        dy = 0
    else -- West
        dx = -(ref_width / 2 + entity_bb.right_bottom.x - entity_bb.left_top.x / 2 + gap)
        dy = 0
    end


        target_position = {x = ref_x + dx, y = ref_y + dy}

        game.print("dx: " .. dx)
        game.print("dy: " .. dy)
        game.print("ref_x: " .. ref_x)
        game.print("ref_y: " .. ref_y)
        game.print("target_position.x: " .. target_position.x)
        game.print("target_position.y: " .. target_position.y)
    else

        local direction_vector = {
            [1] = {x = 0, y = -gap - entity_prototype.selection_box.right_bottom.y},
            [2] = {x = 0, y = gap + entity_prototype.selection_box.right_bottom.y},
            [3] = {x = gap + entity_prototype.selection_box.right_bottom.x, y = 0},
            [4] = {x = -gap - entity_prototype.selection_box.right_bottom.x, y = 0},
        }

        target_position = {x = ref_x + direction_vector[direction].x, y = ref_y + direction_vector[direction].y}
    end

    local target_area = {
        left_top = {x = target_position.x + entity_prototype.selection_box.left_top.x, y = target_position.y + entity_prototype.selection_box.left_top.y},
        right_bottom = {x = target_position.x + entity_prototype.selection_box.right_bottom.x, y = target_position.y + entity_prototype.selection_box.right_bottom.y}
    }

    clear_items(surface, target_area)

    if surface.count_entities_filtered{area = target_area, name = entity} > 0 then
        error("There is an existing entity in the target position.")
    end
    local can_build = player.surface.can_place_entity{name=entity, force=player.force, position=target_position, direction = direction}
    if can_build then
        local new_entity = surface.create_entity{name = entity, position = target_position, direction = direction, force = player.force}
        player.remove_item{name=entity, count=1}
        local serialized = global.utils.serialize_entity(new_entity)
        local entity_json = game.table_to_json(serialized)-- game.table_to_json(entity)
        game.print(dump(entity_json))
        return serialized
    else
        error("There is an existing entity in the target position.")
    end
end


global.actions.place_entity_next_to_6 = function(player_index, entity, ref_x, ref_y, direction, gap)
    local function clear_items_inside_area(surface, area)
        local items = surface.find_entities_filtered{area = area, type = "item-entity"}
        for _, item in ipairs(items) do
            item.destroy()
        end
    end

    local player = game.get_player(player_index)
    local ref_position = {x = ref_x, y = ref_y}
    local cardinals = {defines.direction.north, defines.direction.south, defines.direction.east, defines.direction.west}
    local entity_prototype = game.entity_prototypes[entity]
    local collision_box = entity_prototype.collision_box
    local width = math.abs(collision_box.right_bottom.x - collision_box.left_top.x)
    local height = math.abs(collision_box.right_bottom.y - collision_box.left_top.y)

    local existing_entities = player.surface.find_entities_filtered{area = {{ref_position.x - 0.25, ref_position.y - 0.25}, {ref_position.x + 0.25, ref_position.y + 0.25}}}
    local existing_entity = existing_entities[1]
    local existing_height = 0
    local existing_width = 0
    local tile_height = 0
    local tile_width = 0
    if existing_entity then
        local existing_collision_box = existing_entity.prototype.collision_box
        existing_width = math.abs(existing_collision_box.right_bottom.x - existing_collision_box.left_top.x)
        existing_height = math.abs(existing_collision_box.right_bottom.y - existing_collision_box.left_top.y)
        --width = width + existing_width
        --height = height + existing_height
        tile_height = existing_entity.prototype.tile_height
        tile_width = existing_entity.prototype.tile_width

        -- Correct reference position to be the centroid of the existing entity
        ref_position.x = existing_entity.position.x + tile_width-- math.floor(width/2)
        ref_position.y = existing_entity.position.y + tile_height--math.floor(height/2)


    end

    local target_position = {x = ref_position.x, y = ref_position.y}


    if direction == 1 then
        target_position.y = target_position.y - (gap  + (2-tile_height))-- +1
    elseif direction == 2 then
        target_position.y = target_position.y + (gap )
    elseif direction == 3 then
        target_position.x = target_position.x + (gap)
    else
        target_position.x = target_position.x - (gap + (2-tile_width))-- +1
    end

    local orientation = cardinals[direction]

    local area = {{target_position.x - width / 2, target_position.y - height / 2}, {target_position.x + width / 2, target_position.y + height / 2}}
    clear_items_inside_area(player.surface, area)

    local can_build = player.surface.can_place_entity{name=entity, force=player.force, position=target_position, direction=orientation}
    if can_build then
        local placed_entity = player.surface.create_entity{name=entity, force=player.force, position=target_position, direction=orientation}
        if placed_entity then
            player.remove_item{name=entity, count=1}
            return {x=target_position.x, y=target_position.y}
        else
            error("\"Cannot place here, although I thought I could. Please check your entity or position.\"")
        end
    else
        local colliding_entities = player.surface.find_entities_filtered{area = {{target_position.x - width / 2, target_position.y - height / 2}, {target_position.x + width / 2, target_position.y + height / 2}}}
        local collision_info = ""

        for _, colliding_entity in ipairs(colliding_entities) do
            collision_info = collision_info .. "\nEntity: " .. colliding_entity.name .. ", Position: x=" .. colliding_entity.position.x .. ", y=" .. colliding_entity.position.y
        end

        if collision_info == "" then
            error("\"Cannot place here. Entity: " .. entity .. " at target position: x=" .. target_position.x .. ", y=" .. target_position.y.."\"")
        else
            error("\"Cannot place here due to collision with the following entities:" .. collision_info.."\"")
        end
    end
    error("Something went wrong")
end

global.actions.place_entity_next_to_7 = function(player_index, entity, ref_x, ref_y, direction, gap)
    local player = game.players[player_index]
    local ref_position = {x = ref_x, y = ref_y}
    local cardinals = {defines.direction.north, defines.direction.south, defines.direction.east, defines.direction.west}
    local entity_prototype = game.entity_prototypes[entity]
    local collision_box = entity_prototype.collision_box
    local width = math.abs(collision_box.right_bottom.x - collision_box.left_top.x)
    local height = math.abs(collision_box.right_bottom.y - collision_box.left_top.y)

    local existing_entities = player.surface.find_entities_filtered{area = {{ref_position.x - 0.1, ref_position.y - 0.1}, {ref_position.x + 0.1, ref_position.y + 0.1}}}
    local existing_entity = existing_entities[1]

    if existing_entity then
        local existing_collision_box = existing_entity.prototype.collision_box
        local existing_width = math.abs(existing_collision_box.right_bottom.x - existing_collision_box.left_top.x)
        local existing_height = math.abs(existing_collision_box.right_bottom.y - existing_collision_box.left_top.y)
        width = width + existing_width
        height = height + existing_height

        -- Correct reference position to be the centroid of the existing entity
        ref_position.x = existing_entity.position.x + existing_width / 2
        ref_position.y = existing_entity.position.y + existing_height / 2
    end

    local target_position = {x = ref_position.x, y = ref_position.y}
    if direction == 0 then
        target_position.y = target_position.y - gap - height / 2
    elseif direction == 1 then
        target_position.y = target_position.y + gap + height / 2
    elseif direction == 2 then
        target_position.x = target_position.x + gap + width / 2
    else
        target_position.x = target_position.x - gap - width / 2
    end

    if ref_position.y > target_position.y then
        orientation = defines.direction.south
    elseif ref_position.y < target_position.y then
        orientation = defines.direction.north
    elseif ref_position.x < target_position.x then
        orientation = defines.direction.west
    else
        orientation = defines.direction.east
    end

    local can_build = player.surface.can_place_entity{name=entity, force=player.force, position=target_position, direction=orientation}
    if can_build then
        local placed_entity = player.surface.create_entity{name=entity, force=player.force, position=target_position, direction=orientation}
        if placed_entity then
            player.remove_item{name=entity, count=1}
            game.print(dump(entity))
            return {x=target_position.x, y=target_position.y}

        else
            error("\"Cannot place here, although I thought I could.\"")
        end
    else
        error("\"Cannot place here.\"")
    end
end
