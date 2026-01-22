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


-- Helper to check if a tile is water
local function is_water_tile(tile_name)
    return tile_name == "water" or
           tile_name == "deepwater" or
           tile_name == "water-green" or
           tile_name == "deepwater-green" or
           tile_name == "water-shallow" or
           tile_name == "water-mud"
end

local function find_offshore_pump_position(player, center_pos)
    local max_radius = 20
    local search_positions = {
        {dx = 0, dy = 1, dir = defines.direction.north},
        {dx = 1, dy = 0, dir = defines.direction.west}, 
        {dx = 0, dy = -1, dir = defines.direction.south},
        {dx = -1, dy = 0, dir = defines.direction.east}
    }

    for radius = 1, max_radius do
        for y = -radius, radius do
            for x = -radius, radius do
                if math.abs(x) == radius or math.abs(y) == radius then
                    local check_pos = {
                        x = center_pos.x + x,
                        y = center_pos.y + y
                    }

                    -- Check if position is already occupied
                    -- Factorio 2.0: collision_mask expects a collision layer name string
                    local entities = player.surface.find_entities_filtered{
                        position = check_pos,
                        collision_mask = "player",
                        invert = false
                    }

                    if #entities == 0 then
                        local current_tile = player.surface.get_tile(check_pos.x, check_pos.y)

                        if not is_water_tile(current_tile.name) then
                            for _, search in ipairs(search_positions) do
                                local water_pos = {
                                    x = check_pos.x + search.dx,
                                    y = check_pos.y + search.dy
                                }

                                -- Check for entities at water position
                                -- Factorio 2.0: collision_mask expects a collision layer name string
                                local water_entities = player.surface.find_entities_filtered{
                                    position = water_pos,
                                    collision_mask = "water_tile",
                                    invert = true
                                }

                                if #water_entities == 0 then
                                    local adjacent_tile = player.surface.get_tile(water_pos.x, water_pos.y)

                                    if is_water_tile(adjacent_tile.name) then
                                        local entity_dir = surface_to_entity_direction(search.dir)
                                        local placement = {
                                            name = "offshore-pump",
                                            position = check_pos,
                                            direction = entity_dir,
                                            force = "player"
                                        }

                                        if player.surface.can_place_entity(placement) then
                                            -- Final collision check for the exact pump dimensions
                                            -- Factorio 2.0: collision_mask expects a collision layer name string
                                            local final_check = player.surface.find_entities_filtered{
                                                area = {{check_pos.x - 0.5, check_pos.y - 0.5},
                                                       {check_pos.x + 0.5, check_pos.y + 0.5}},
                                                collision_mask = "player"
                                            }

                                            if #final_check == 0 then
                                                return {
                                                    position = check_pos,
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
            end
        end
    end

    return nil
end

storage.actions.place_entity = function(player_index, entity, direction, x, y, exact)
    -- Ensure we have a valid character, recreating if necessary
    local player = storage.utils.ensure_valid_character(player_index)
    local position = {x = x, y = y}

    if not direction then
        direction = 0
    end

    local entity_direction = storage.utils.get_entity_direction(entity, direction)

    -- Common validation functions
    local function validate_distance()
        local max_distance = player.reach_distance or player.build_distance
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
        if prototypes.entity[entity] == nil then
            local name = entity:gsub(" ", "_"):gsub("-", "_")
            error("\""..name .. " isn't something that exists. Did you make a typo?\"")
        end
    end

    local function validate_inventory()
        local count = player.get_item_count(entity)
        if count == 0 then
            local name = entity:gsub(" ", "_"):gsub("-", "_")
            local inv_contents = storage.utils.format_inventory_for_error(player)
            error("\"No " .. name .. " in inventory. Current inventory: " .. inv_contents .. "\"")
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
            storage.utils.avoid_entity(player_index, entity, position)

            -- Perform the actual placement
            local placed_entity = player.surface.create_entity{
                name = entity,
                force = "player",
                position = position,
                direction = entity_direction,
            }

            if placed_entity then
                player.remove_item{name = entity, count = 1}
                player.cursor_ghost = nil  -- Clear the ghost
                return storage.utils.serialize_entity(placed_entity)
            else
                error("\"Failed to place entity after delay\"")
            end
        end)

        return { pending = true }
    end

    -- Fast placement implementation (existing logic)
    local function fast_place()
        local entity_prototype = prototypes.entity[entity]

        if entity == 'offshore-pump' then
            exact = false
        end

        -- Check for existing entity
        if exact then
            local existing_entity = player.surface.find_entity(entity, position)
            if existing_entity then
                error("\"entity already exists at the target position " .. serpent.line(existing_entity.position) .. " - remove this before continuing.\"" )
            end

            -- Get entity prototype's collision box
            local collision_box = entity_prototype.collision_box
            -- Calculate the area to check for water
            local check_area = {
                {position.x - collision_box.left_top.x/2, position.y - collision_box.left_top.y/2},
                {position.x + collision_box.right_bottom.x/2, position.y + collision_box.right_bottom.y/2}
            }
            rendering.draw_circle{only_in_alt_mode=true, width = 1, color = {r = 0, g = 1, b = 0}, surface = player.surface, radius = 0.5, filled = false, target = {x=position.x, y=position.y}, time_to_live = 12000}

            -- Check each tile in the entity's footprint for water
            for x = math.floor(check_area[1][1]), math.ceil(check_area[2][1]) do
                for y = math.floor(check_area[1][2]), math.ceil(check_area[2][2]) do
                    local tile = player.surface.get_tile(x, y)
                    if is_water_tile(tile.name) then
                        error("\"Cannot place " .. entity .. " at " .. position.x .. ", " .. position.y ..
                              " as entity footprint overlaps water. Please try a different location\"")
                    end
                end
            end
        end
        storage.utils.avoid_entity(player_index, entity, position, direction)
        -- Use surface based validation equivalent to LuaPlayer.can_place_entity
        local can_build = storage.utils.can_place_entity(player, entity, position, entity_direction)

        if not can_build then
            if not exact then
                local new_position
                local new_position = nil
                local found_position = false
                -- special logic for orienting offshore pumps correctly.
                if entity == 'offshore-pump' then
                    local pos_dir = find_offshore_pump_position(player, position)
                    -- Factorio 2.0: direction is already in 16-direction format, no division needed
                    entity_direction = storage.utils.get_entity_direction(entity, pos_dir['direction'])
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
                                    storage.utils.avoid_entity(player_index, entity, position, direction)
                                    can_build = storage.utils.can_place_entity(player, entity, new_position, entity_direction)
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
                    }
                    if have_built then
                        player.remove_item{name = entity, count = 1}
                        -- game.print("Placed " .. entity .. " at " .. new_position.x .. ", " .. new_position.y)
                        return storage.actions.get_entity(player_index, entity, new_position.x, new_position.y)
                    end
                else
                    error("\"Could not find a suitable position to place " .. entity .. " near the target location.\"")
                end
            else
                -- Clear existing entities if exact placement is required
                local area = {{position.x - 0.25, position.y - 0.25}, {position.x + 0.25, position.y + 0.25}}
                local entities = player.surface.find_entities_filtered{area = area, force = "player"}
                if #entities ~= 0 then
                    -- Build a list of blocking entity names and positions
                    local blocking_info = {}
                    for _, blocking_entity in ipairs(entities) do
                        table.insert(blocking_info, blocking_entity.name .. " at x=" .. blocking_entity.position.x .. " y=" .. blocking_entity.position.y)
                    end
                    local blocking_str = table.concat(blocking_info, ", ")
                    if #entities == 1 then
                        error("\"Could not find a suitable position to place " .. entity .. " at the target location x=" .. position.x .. " y=" .. position.y .. ", as there is an existing object in the way: " .. blocking_str .. "\"")
                    else
                        error("\"Could not find a suitable position to place " .. entity .. " at the target location x=" .. position.x .. " y=" .. position.y .. ", as there are existing objects in the way: " .. blocking_str .. "\"")
                    end
                end
            end

            storage.utils.avoid_entity(player_index, entity, position, direction)

            can_build = storage.utils.can_place_entity(player, entity, position, entity_direction)

            if not can_build then
                local entity_prototype = prototypes.entity[entity]
                local entity_box = entity_prototype.collision_box
                local entity_width = 1
                local entity_height = 1
                if direction == defines.direction.north or direction == defines.direction.south then
                    entity_width = math.abs(entity_box.right_bottom.x - entity_box.left_top.x)
                    entity_height = math.abs(entity_box.right_bottom.y - entity_box.left_top.y)
                else
                    entity_height = math.abs(entity_box.right_bottom.x - entity_box.left_top.x)
                    entity_width = math.abs(entity_box.right_bottom.y - entity_box.left_top.y)
                end

                rendering.draw_rectangle{
                    only_in_alt_mode=true,
                    surface = player.surface,
                    left_top = {position.x - entity_width / 2, position.y - entity_height / 2},
                    right_bottom = {position.x + entity_width / 2, position.y + entity_height / 2},
                    filled = false,
                    color = {r=1, g=0, b=0, a=0.5},
                    time_to_live = 60000
                }

                -- Find what's blocking placement for a better error message
                local blocking_area = {
                    {position.x - entity_width / 2, position.y - entity_height / 2},
                    {position.x + entity_width / 2, position.y + entity_height / 2}
                }
                local blocking_entities = player.surface.find_entities_filtered{area = blocking_area}
                local blocking_info = {}
                for _, blocking_entity in ipairs(blocking_entities) do
                    if blocking_entity.name ~= "character" then
                        table.insert(blocking_info, blocking_entity.name .. " at x=" .. blocking_entity.position.x .. " y=" .. blocking_entity.position.y)
                    end
                end

                -- Check for water tiles
                local has_water = false
                for check_x = math.floor(blocking_area[1][1]), math.ceil(blocking_area[2][1]) do
                    for check_y = math.floor(blocking_area[1][2]), math.ceil(blocking_area[2][2]) do
                        local tile = player.surface.get_tile(check_x, check_y)
                        if tile.name == "water" or tile.name == "deepwater" or tile.name == "water-green" or tile.name == "deepwater-green" or tile.name == "water-shallow" or tile.name == "water-mud" then
                            has_water = true
                            break
                        end
                    end
                    if has_water then break end
                end

                local error_msg = "\"Cannot place " .. entity .. " at x=" .. position.x .. " y=" .. position.y
                if #blocking_info > 0 then
                    error_msg = error_msg .. " - blocked by: " .. table.concat(blocking_info, ", ")
                end
                if has_water then
                    error_msg = error_msg .. " - terrain includes water"
                end
                if #blocking_info == 0 and not has_water then
                    error_msg = error_msg .. " - something is in the way or terrain is unplaceable"
                end
                error_msg = error_msg .. "\""
                error(error_msg)
            end
        end

        local have_built = player.surface.create_entity{
            name = entity,
            force = player.force,
            position = position,
            direction = entity_direction,
        }

        if have_built then
            player.remove_item{name = entity, count = 1}
            -- game.print("Placed " .. entity .. " at " .. position.x .. ", " .. position.y)

            -- Find and return the placed entity
            local width = 0.5
            local height = 0.5
            local target_area = {
                {position.x - width, position.y - height},
                {position.x + width, position.y + height}
            }
            local entities = player.surface.find_entities_filtered{area = target_area, name = entity}

            if #entities > 0 then
                return storage.utils.serialize_entity(entities[1])
            end
            error("\"Could not find placed entity\"")
        else
            -- create_entity returned nil - collect diagnostic information
            local diag = {}
            diag.entity_name = entity
            diag.position = {x = position.x, y = position.y}
            diag.direction = entity_direction
            diag.can_place = player.surface.can_place_entity{name = entity, position = position, force = player.force, direction = entity_direction}

            -- Check for blocking entities
            local prototype = prototypes.entity[entity]
            local width = 1
            local height = 1
            if prototype and prototype.tile_width then
                width = prototype.tile_width / 2 + 0.5
                height = prototype.tile_height / 2 + 0.5
            end
            local area = {{position.x - width, position.y - height}, {position.x + width, position.y + height}}
            local blocking = player.surface.find_entities_filtered{area = area}
            local blocking_names = {}
            for _, b in ipairs(blocking) do
                if b.name ~= "character" then
                    table.insert(blocking_names, b.name .. " at (" .. b.position.x .. "," .. b.position.y .. ")")
                end
            end
            diag.blocking_entities = blocking_names

            -- Check terrain
            local tile = player.surface.get_tile(position.x, position.y)
            diag.tile_name = tile.name

            local error_msg = string.format(
                "\"create_entity returned nil for %s at (%s, %s). Diagnostics: can_place=%s, tile=%s, blocking=%s\"",
                entity,
                position.x,
                position.y,
                tostring(diag.can_place),
                diag.tile_name,
                #blocking_names > 0 and table.concat(blocking_names, ", ") or "none"
            )
            error(error_msg)
        end
    end

    -- Main execution flow
    validate_distance()
    validate_entity()
    validate_inventory()
    storage.utils.avoid_entity(player_index, entity, position)

    -- Choose placement method based on storage.fast setting
    if storage.fast then
        return fast_place()
    else
        local result = slow_place()
        return result
    end
end