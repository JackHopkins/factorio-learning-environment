global.actions.place_entity = function(player_index, entity, direction, x, y, exact)
    local player = game.players[player_index]
    local position = {x = x, y = y}

    -- If character exists on the map, use its reach distance
    local max_distance
    if player.character == nil then
        max_distance = player.build_distance
    else
        max_distance = player.character.reach_distance  -- Using character's reach distance
    end

    local dx = player.position.x - x
    local dy = player.position.y - y
    if dy == nil then
        dy = 0
    end
    local distance = math.sqrt(dx * dx + dy * dy)

    if distance > max_distance then
        error("The target position is too far away to place the entity. Move closer.")
    end

    local function get_entity_direction(entity, direction)
        local prototype = game.entity_prototypes[entity]
        local cardinals = {
            defines.direction.north,
            defines.direction.east,
            defines.direction.south,
            defines.direction.west
        }

        if prototype and prototype.name == "offshore-pump" then
            if direction == 1 then
                return defines.direction.north
            elseif direction == 4 then
                return defines.direction.east
            elseif direction == 3 then
                return defines.direction.south
            else
                return defines.direction.west
            end
        end

        if prototype and prototype.type == "inserter" then
            --return cardinals[(direction % 4)]
            if direction == 0 then
                return defines.direction.south
            elseif direction == 1 then
                return defines.direction.west
            elseif direction == 2 then
                return defines.direction.north
            else
                return defines.direction.east
            end
        elseif prototype.type == "mining-drill" then
            if direction == 1 then
                return cardinals[2]
            elseif direction == 2 then
                return cardinals[3]
            elseif direction == 3 then
                return cardinals[4]
            else
                return cardinals[1]
            end
        else
            return cardinals[direction]
        end
    end

    if game.entity_prototypes[entity] == nil then
        local name = entity:gsub(" ", "_"):gsub("-", "_")
        error(name .. " isn't something that exists. Did you make a typo?")
    end

    local count = player.get_item_count(entity)

    if count == 0 then
        local name = entity:gsub(" ", "_"):gsub("-", "_")
        error("No " .. name .. " in inventory.")
    end

    local prototype = game.entity_prototypes[entity]
    local collision_box = prototype.collision_box
    local width = math.abs(collision_box.right_bottom.x - collision_box.left_top.x)
    local height = math.abs(collision_box.right_bottom.y - collision_box.left_top.y)

    local function player_collision(player, target_area)
        local character_box = player.character.prototype.collision_box
        local character_area = {
            {player.position.x + character_box.left_top.x, player.position.y + character_box.left_top.y},
            {player.position.x + character_box.right_bottom.x, player.position.y + character_box.right_bottom.y}
        }
        return (character_area[1][1] < target_area[2][1] and character_area[2][1] > target_area[1][1]) and
               (character_area[1][2] < target_area[2][2] and character_area[2][2] > target_area[1][2])
    end

    local target_area = {
        {position.x - width / 2, position.y - height / 2},
        {position.x + width / 2, position.y + height / 2}
    }

    while player_collision(player, target_area) do
        player.teleport({player.position.x + width + 1, player.position.y}, player.surface)
    end

    -- **Modified Code Starts Here**
    -- Check for pre-existing entities and pick them up first
    --local existing_entities = player.surface.find_entities_filtered{radius = 0.5, position = position}
    --for _, existing_entity in pairs(existing_entities) do
    --    if existing_entity ~= player.character and existing_entity.valid then
    --        if existing_entity.prototype.selectable_in_game then
    --            local can_reach = player.can_reach_entity(existing_entity)
    --            if not can_reach then
    --                error("Cannot reach existing entity " .. existing_entity.name .. " at position (" .. existing_entity.position.x .. ", " .. existing_entity.position.y .. ").")
    --            end
    --            --local success = player.mine_entity(existing_entity)
    --            if not existing_entity.minable then
    --                local success = global.actions.pickup_entity(player.index, existing_entity.position.x, existing_entity.position.y, existing_entity.name)
    --                if not success then
    --                    error("Cannot pick up existing entity " .. existing_entity.name .. " at position (" .. existing_entity.position.x .. ", " .. existing_entity.position.y .. ").")
    --                else
    --                    game.print("Picked up existing entity " .. existing_entity.name .. " at position (" .. existing_entity.position.x .. ", " .. existing_entity.position.y .. ").")
    --                end
    --            end
    --        else
    --            error("Cannot pick up existing entity " .. existing_entity.name .. " at position (" .. existing_entity.position.x .. ", " .. existing_entity.position.y .. "). It is not minable.")
    --        end
    --    end
    --end
    -- **Modified Code Ends Here**

    local can_build = player.can_place_entity{
        name = entity,
        force = player.force,
        position = position,
        direction = get_entity_direction(entity, direction)
    }

    if not can_build then
        if not exact then
            local radius = 1
            local max_radius = 10
            local found_position = false
            local new_position

            while not found_position and radius <= max_radius do
                for dx = -radius, radius do
                    for dy = -radius, radius do
                        if dx == -radius or dx == radius or dy == -radius or dy == radius then
                            new_position = {x = position.x + dx, y = position.y + dy}
                            can_build = player.can_place_entity{
                                name = entity,
                                force = player.force,
                                position = new_position,
                                direction = get_entity_direction(entity, direction)
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

            if found_position then
                local have_built = player.surface.create_entity{
                    name = entity,
                    force = "player",
                    position = new_position,
                    direction = get_entity_direction(entity, direction),
                    player = player
                }
                if have_built then
                    player.remove_item{name = entity, count = 1}
                    --local placed_entity = player.surface.find_entity(entity, new_position)
                    --game.print("Placed " .. entity .. " at " .. placed_entity.position.x .. ", " .. placed_entity.position.y)
                    --local serialized = global.utils.serialize_entity(placed_entity)
                    --return serialized
                    return global.actions.get_entity(player_index, entity, new_position.x, new_position.y)
                end
            else
                error("Could not find a suitable position to place " .. entity .. " near the target location.")
            end
        else
            --local existing_entity = global.actions.get_entity(player_index, entity, position.x, position.y)
            local area = {{position.x - 0.25, position.y - 0.25}, {position.x + 0.25, position.y + 0.25}}
            local entities = player.surface.find_entities_filtered{area = area, force = "player"}
            for _, existing_entity in pairs(entities) do
                --if existing_entity.name == entity then
                --local success = global.actions.pickup_entity(player_index, existing_entity.position.x, existing_entity.position.y, existing_entity.name)
                if existing_entity.can_be_destroyed() then
                    game.print("Picked up "..existing_entity.name)
                    pcall(existing_entity.destroy{raise_destroy=false, do_cliff_correction=false})
                end

                --end
            end
           -- local success = global.actions.pickup_entity(player.index, position.x, position.y, entity)
           -- if not success then
             --   error("Cannot place " .. entity .. " at the exact position due to obstacles.")
            --end
        --    error("Cannot place " .. entity .. " at the exact position due to obstacles.")
        end
        can_build = player.can_place_entity{
            name = entity,
            force = player.force,
            position = position,
            direction = get_entity_direction(entity, direction)
        }
        if not can_build then
            error("Cannot place " .. entity .. " at the target location.")
        end
        local have_built = player.surface.create_entity{
            name = entity,
            force = "player",
            position = position,
            direction = get_entity_direction(entity, direction),
            player = player
        }
        if have_built then
            --game.print("Placed " .. entity .. " at " .. position.x .. ", " .. position.y)
            player.remove_item{name = entity, count = 1}
            return global.actions.get_entity(player_index, entity, position.x, position.y)
            --local placed_entity = player.surface.find_entity(entity, position)
            --game.print("Placed " .. entity .. " at " .. placed_entity.position.x .. ", " .. placed_entity.position.y)
            --local serialized = global.utils.serialize_entity(placed_entity)
            --return serialized
        end
    else

        local have_built = player.surface.create_entity{
            name = entity,
            force = "player",
            position = position,
            direction = get_entity_direction(entity, direction),
            player = player
        }
        if have_built then
            game.print("Placed " .. entity .. " at " .. position.x .. ", " .. position.y)
            player.remove_item{name = entity, count = 1}
            local width = 0.5
            local height = 0.5
             local target_area = {
                {position.x - width , position.y - height },
                {position.x + width , position.y + height }
            }
            --local entities = player.surface.find_entities_filtered{area = target_area} --, name = entity}
            local entities = player.surface.find_entities_filtered{area = target_area, name = entity}
            game.print("Number of entities found: " .. #entities)

             if #entities > 0 then
                local entity = entities[1]  -- get the first entity of the specified type in the area
                local serialized = global.utils.serialize_entity(entity)
                local entity_json = game.table_to_json(serialized)-- game.table_to_json(entity
                return serialized
             end

            error("Could not find entity")
            -- local placed_entity = player.surface.find_entity(entity, position)
            -- game.print("Placed " .. entity .. " at " .. placed_entity.position.x .. ", " .. placed_entity.position.y)
            -- local serialized = global.utils.serialize_entity(placed_entity)
            -- return serialized
            --return global.actions.get_entity(player_index, entity, position.x, position.y)
            --return global.actions.get_entity(player_index, entity, position.x, position.y)
        end
    end
end