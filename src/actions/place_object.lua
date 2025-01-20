-- Helper to check if a tile is water
local function is_water_tile(tile_name)
    return tile_name == "water" or
           tile_name == "deepwater" or
           tile_name == "water-green" or
           tile_name == "deepwater-green" or
           tile_name == "water-shallow" or
           tile_name == "water-mud"
end

-- Helper to convert surface direction to entity direction
local function surface_to_entity_direction(surface_dir)
    -- In Factorio, offshore pumps face opposite to placement direction
    local direction_map = {
        [defines.direction.north] = defines.direction.north,  -- 0 -> 4
        [defines.direction.east] = defines.direction.east,    -- 2 -> 6
        [defines.direction.south] = defines.direction.south,  -- 4 -> 0
        [defines.direction.west] = defines.direction.west     -- 6 -> 2
    }
    return direction_map[surface_dir]
end

-- Apply position offset based on direction
local function apply_position_offset(position, direction)
    local pos = {x = position.x, y = position.y}

    -- Apply offsets based on pump direction
    if direction == defines.direction.north then  -- Pump faces south
        pos.y = pos.y + 1  -- Move one tile down when placing at top of water
    elseif direction == defines.direction.west then  -- Pump faces east
        pos.x = pos.x + 1  -- Move one tile right when placing at left of water
    end

    return pos
end

local function find_offshore_pump_position(surface, center_pos)
    -- Search in an expanding spiral pattern for better coverage
    local max_radius = 20
    local search_positions = {
        {dx = 0, dy = 1, dir = defines.direction.north},   -- Check south of water
        {dx = 1, dy = 0, dir = defines.direction.west},    -- Check east of water
        {dx = 0, dy = -1, dir = defines.direction.south},  -- Check north of water
        {dx = -1, dy = 0, dir = defines.direction.east}    -- Check west of water
    }
    game.print("Searching")

    for radius = 1, max_radius do
        -- Search in a spiral pattern from center_pos
        for y = -radius, radius do
            for x = -radius, radius do
                -- Only process points on the edge of the current square
                if math.abs(x) == radius or math.abs(y) == radius then
                    local check_pos = {
                        x = center_pos.x + x,
                        y = center_pos.y + y
                    }

                    -- Check tile at current position
                    local current_tile = surface.get_tile(check_pos.x, check_pos.y)

                    -- Skip if current position is water
                    if not is_water_tile(current_tile.name) then
                        -- Check all adjacent positions for water
                        for _, search in ipairs(search_positions) do
                            local water_pos = {
                                x = check_pos.x + search.dx,
                                y = check_pos.y + search.dy
                            }

                            local adjacent_tile = surface.get_tile(water_pos.x, water_pos.y)

                            if is_water_tile(adjacent_tile.name) then
                                -- Create placement prototype
                                local entity_dir = surface_to_entity_direction(search.dir)
                                -- Apply position offset based on direction
                                local adjusted_pos = check_pos --apply_position_offset(check_pos, search.dir)

                                local placement = {
                                    name = "offshore-pump",
                                    position = adjusted_pos,
                                    direction = entity_dir,
                                    force = "player"
                                }
                                game.print("test")

                                -- Verify placement is valid
                                if surface.can_place_entity(placement) then
                                    return {
                                        position = adjusted_pos,
                                        direction = entity_dir
                                    }
                                end
                            end
                        end
                    end
                end
            end
        end
    end

    return nil
end


--global.actions.place_entity2 = function(player_index, entity, direction, x, y, exact)
--    local player = game.get_player(player_index)
--    local position = {x = x, y = y}
--    local entity_direction = global.utils.get_entity_direction(entity, direction)
--
--    -- Common validation functions
--    local function validate_distance()
--        local max_distance = player['character'] and player.reach_distance or player.build_distance
--        local dx = player.position.x - x
--        local dy = player.position.y - y or 0
--        local distance = math.sqrt(dx * dx + dy * dy)
--
--        if distance > max_distance then
--            error("\"The target position is too far away to place the entity. The player position is " ..
--                  player.position.x .. ", " .. player.position.y ..
--                  " and the target position is " .. x .. ", " .. y ..
--                  ". The distance is " .. string.format("%.2f", distance) ..
--                  " and the max distance is " .. max_distance .. ". Move closer.\"")
--        end
--    end
--
--    local function validate_entity()
--        if game.entity_prototypes[entity] == nil then
--            local name = entity:gsub(" ", "_"):gsub("-", "_")
--            error(name .. " isn't something that exists. Did you make a typo?")
--        end
--    end
--
--    local function validate_inventory()
--        local count = player.get_item_count(entity)
--        if count == 0 then
--            local name = entity:gsub(" ", "_"):gsub("-", "_")
--            error("No " .. name .. " in inventory.")
--        end
--    end
--
--    -- Slow placement implementation
--    local function slow_place()
--        -- Set cursor ghost
--        player.cursor_ghost = entity
--
--        -- Select the target position
--        player.update_selected_entity(position)
--
--        -- Schedule the actual placement after delay
--        script.on_nth_tick(60, function(event)  -- 30 ticks = 0.5 seconds
--            script.on_nth_tick(60, nil)  -- Clear the scheduled event
--
--            -- Verify conditions are still valid
--            validate_distance()
--            validate_inventory()
--
--            -- Avoid entity at target position
--            global.utils.avoid_entity(player_index, entity, position, direction)
--
--            -- Perform the actual placement
--            local placed_entity = player.surface.create_entity{
--                name = entity,
--                force = "player",
--                position = position,
--                direction = entity_direction,
--                player = player
--            }
--
--            if placed_entity then
--                player.remove_item{name = entity, count = 1}
--                game.print("Placed " .. entity .. " at " .. position.x .. ", " .. position.y)
--                player.cursor_ghost = nil  -- Clear the ghost
--                return global.utils.serialize_entity(placed_entity)
--            else
--                error("Failed to place entity after delay")
--            end
--        end)
--
--        return { pending = true }
--    end
--
--    -- Fast placement implementation (existing logic)
--    local function fast_place()
--        local entity_prototype = game.entity_prototypes[entity]
--
--        -- Check for existing entity
--        local existing_entity = player.surface.find_entity(entity, position)
--        if existing_entity then
--            if existing_entity.name == entity then
--                existing_entity.direction = entity_direction
--                game.print("Updated direction of existing " .. entity .. " at " .. x .. ", " .. y)
--                return global.utils.serialize_entity(existing_entity)
--            else
--                existing_entity.destroy({raise_destroy=true})
--            end
--        end
--
--        if entity == 'offshore-pump' then
--            exact = false
--        end
--
--        local can_build = global.utils.avoid_entity(player_index, entity, position, entity_direction)
--        game.print("Can build: " .. tostring(can_build))
--        if not can_build then
--            if not exact then
--                local new_position = nil
--                -- special logic for orienting offshore pumps correctly.
--                if entity == 'offshore-pump' then
--                    if new_position then
--                        local pos_dir = find_offshore_pump_position(player.surface, position)
--                        game.print(serpent.line(pos_dir))
--                        entity_direction = global.utils.get_entity_direction(entity, pos_dir['direction']/2)
--                        new_position = pos_dir['position']
--                    end
--                else
--                    new_position = player.surface.find_non_colliding_position(entity, position, 15, 0.5, false)
--                end
--
--                if new_position ~= nil then
--                    local have_built = player.surface.create_entity{
--                        name = entity,
--                        force = player.force,
--                        position = new_position,
--                        direction = entity_direction,
--                        player = player,
--                        move_stuck_players = true
--                    }
--                    if have_built then
--                        player.remove_item{name = entity, count = 1}
--                        game.print("Placed " .. entity .. " at " .. new_position.x .. ", " .. new_position.y)
--                        return global.actions.get_entity(player_index, entity, new_position.x, new_position.y)
--                    end
--                else
--                    error("\"Could not find a suitable position to place " .. entity .. " near the target location.\"")
--                end
--            else
--                -- Clear existing entities if exact placement is required
--                local area = {{position.x - 0.25, position.y - 0.25}, {position.x + 0.25, position.y + 0.25}}
--                local entities = player.surface.find_entities_filtered{area = area, force = "player"}
--                for _, existing_entity in pairs(entities) do
--                    if existing_entity.can_be_destroyed() and existing_entity ~= player.character then
--                        pcall(existing_entity.destroy{raise_destroy=false, do_cliff_correction=false})
--                    end
--                end
--            end
--
--            --local entity_direction = global.utils.get_entity_direction(entity, direction)
--            global.utils.avoid_entity(player_index, entity, position, entity_direction)
--
--            can_build = player.can_place_entity{
--                name = entity,
--                force = player.force,
--                position = position,
--                direction = entity_direction
--            }
--            local issue_num = #global.utils.get_placement_issues(player, entity, position, entity_direction)
--            if not can_build and issue_num > 0 then
--                local description = global.utils.describe_placement_issues(player, entity, position, entity_direction)
--                error(description)
--            end
--            --can_build = true -- We are forcing this to be true if there are no discernable issues in placement
--        end
--
--        local have_built = player.surface.create_entity{
--            name = entity,
--            force = player.force,
--            position = position,
--            direction = entity_direction,
--            player = player,
--            move_stuck_players = true,
--            fast_replace = true
--        }
--
--        if have_built then
--
--            player.remove_item{name = entity, count = 1}
--            game.print("Placed " .. entity .. " at " .. position.x .. ", " .. position.y)
--
--
--            -- Find and return the placed entity
--            local width = 1
--            local height = 1
--            local target_area = {
--                {position.x - width, position.y - height},
--                {position.x + width, position.y + height}
--            }
--            local entities = player.surface.find_entities_filtered{area = target_area, name = entity}
--
--            local closest = nil
--            local closest_distance = 100000
--
--            if #entities == 0 then
--                error("\"Could not find placed entity\"")
--            end
--            -- Order entities by distance to the position
--            for _, _entity in ipairs(entities) do
--                local distance = ((position.x - (_entity.position.x-0.5)) ^ 2 + (position.y - (_entity.position.y-0.5)) ^ 2) ^ 0.5
--                if distance < closest_distance then
--                    closest_distance = distance
--                    closest = _entity
--                end
--            end
--            game.print(serpent.line(closest.position)..","..serpent.line(position))
--            return global.utils.serialize_entity(closest)
--        end
--    end
--
--    -- Main execution flow
--    validate_distance()
--    validate_entity()
--    validate_inventory()
--    global.utils.avoid_entity(player_index, entity, position, entity_direction)
--
--    -- Choose placement method based on global.fast setting
--    if global.fast then
--        return fast_place()
--    else
--        local result = slow_place()
--        return result
--    end
--end


global.actions.place_entity = function(player_index, entity, direction, x, y, exact)
    local player = game.get_player(player_index)
    local position = {x = x, y = y}

    if not direction then
        direction = 0
    end

    local entity_direction = global.utils.get_entity_direction(entity, direction)

    -- Common validation functions
    local function validate_distance()
        local max_distance = player['character'] and player.reach_distance or player.build_distance
        local dx = player.position.x - x
        local dy = player.position.y - y or 0
        local distance = math.sqrt(dx * dx + dy * dy)

        if distance > max_distance then
            error("\"The target position is too far away to place the entity. The player position is " ..
                  player.position.x .. ", " .. player.position.y ..
                  " and the target position is " .. x .. ", " .. y ..
                  ". The distance is " .. string.format("%.2f", distance) ..
                  " and the max distance is " .. max_distance .. ". Move closer.\"")
        end
    end

    local function validate_entity()
        if game.entity_prototypes[entity] == nil then
            local name = entity:gsub(" ", "_"):gsub("-", "_")
            error(name .. " isn't something that exists. Did you make a typo?")
        end
    end

    local function validate_inventory()
        local count = player.get_item_count(entity)
        if count == 0 then
            local name = entity:gsub(" ", "_"):gsub("-", "_")
            error("No " .. name .. " in inventory.")
        end
    end

    -- Slow placement implementation
    local function slow_place()
        -- Set cursor ghost
        player.cursor_ghost = entity

        -- Select the target position
        player.update_selected_entity(position)

        -- Schedule the actual placement after delay
        script.on_nth_tick(60, function(event)  -- 30 ticks = 0.5 seconds
            script.on_nth_tick(60, nil)  -- Clear the scheduled event

            -- Verify conditions are still valid
            validate_distance()
            validate_inventory()

            -- Avoid entity at target position
            global.utils.avoid_entity(player_index, entity, position)

            -- Perform the actual placement
            local placed_entity = player.surface.create_entity{
                name = entity,
                force = "player",
                position = position,
                direction = entity_direction,
                player = player
            }

            if placed_entity then
                player.remove_item{name = entity, count = 1}
                game.print("Placed " .. entity .. " at " .. position.x .. ", " .. position.y)
                player.cursor_ghost = nil  -- Clear the ghost
                return global.utils.serialize_entity(placed_entity)
            else
                error("Failed to place entity after delay")
            end
        end)

        return { pending = true }
    end

    -- Fast placement implementation (existing logic)
    local function fast_place()
        local entity_prototype = game.entity_prototypes[entity]

        -- Check for existing entity
        local existing_entity = player.surface.find_entity(entity, position)
        if existing_entity then
            if existing_entity.name == entity then
                existing_entity.direction = entity_direction
                game.print("Updated direction of existing " .. entity .. " at " .. x .. ", " .. y)
                return global.utils.serialize_entity(existing_entity)
            else
                existing_entity.destroy({raise_destroy=true})
            end
        end

        local can_build = player.can_place_entity{
            name = entity,
            force = player.force,
            position = position,
            direction = entity_direction
        }
        if entity == 'offshore-pump' then
            exact = false
        end

        if not can_build then
            if not exact then
                local new_position
                local new_position = nil
                local found_position = false
                -- special logic for orienting offshore pumps correctly.
                if entity == 'offshore-pump' then
                    local pos_dir = find_offshore_pump_position(player.surface, position)
                    game.print(serpent.line(pos_dir))
                    entity_direction = global.utils.get_entity_direction(entity, pos_dir['direction']/2)
                    new_position = pos_dir['position']
                    found_position = true
                else
                    -- Existing search logic for nearby valid position
                    local radius = 1
                    local max_radius = 10

                    while not found_position and radius <= max_radius do
                        for dx = -radius, radius do
                            for dy = -radius, radius do
                                if dx == -radius or dx == radius or dy == -radius or dy == radius then
                                    new_position = {x = position.x + dx, y = position.y + dy}
                                    can_build = player.can_place_entity{
                                        name = entity,
                                        force = player.force,
                                        position = new_position,
                                        direction = entity_direction
                                    }
                                    if can_build then
                                        found_position = true
                                        break
                                    end
                                end
                            end
                            if found_position then break end
                        end
                        radius = radius + 1
                    end
                end

                if found_position then
                    local have_built = player.surface.create_entity{
                        name = entity,
                        force = player.force,
                        position = new_position,
                        direction = entity_direction,
                        player = player
                    }
                    if have_built then
                        player.remove_item{name = entity, count = 1}
                        game.print("Placed " .. entity .. " at " .. new_position.x .. ", " .. new_position.y)
                        return global.actions.get_entity(player_index, entity, new_position.x, new_position.y)
                    end
                else
                    error("\"Could not find a suitable position to place " .. entity .. " near the target location.\"")
                end
            else
                -- Clear existing entities if exact placement is required
                local area = {{position.x - 0.25, position.y - 0.25}, {position.x + 0.25, position.y + 0.25}}
                local entities = player.surface.find_entities_filtered{area = area, force = "player"}
                for _, existing_entity in pairs(entities) do
                    if existing_entity.can_be_destroyed() then
                        game.print("Picked up "..existing_entity.name)
                        pcall(existing_entity.destroy{raise_destroy=false, do_cliff_correction=false})
                    end
                end
            end

            global.utils.avoid_entity(player_index, entity, position)

            can_build = player.can_place_entity{
                name = entity,
                force = player.force,
                position = position,
                direction = entity_direction
            }

            if not can_build then
                --error("Cannot place " .. entity .. " at the target location.")
            end
        end

        local have_built = player.surface.create_entity{
            name = entity,
            force = player.force,
            position = position,
            direction = entity_direction,
            player = player
        }

        if have_built then
            player.remove_item{name = entity, count = 1}
            game.print("Placed " .. entity .. " at " .. position.x .. ", " .. position.y)

            -- Find and return the placed entity
            local width = 0.5
            local height = 0.5
            local target_area = {
                {position.x - width, position.y - height},
                {position.x + width, position.y + height}
            }
            local entities = player.surface.find_entities_filtered{area = target_area, name = entity}

            if #entities > 0 then
                return global.utils.serialize_entity(entities[1])
            end
            error("\"Could not find placed entity\"")
        end
    end

    -- Main execution flow
    validate_distance()
    validate_entity()
    validate_inventory()
    global.utils.avoid_entity(player_index, entity, position)

    -- Choose placement method based on global.fast setting
    if global.fast then
        return fast_place()
    else
        local result = slow_place()
        return result
    end
end