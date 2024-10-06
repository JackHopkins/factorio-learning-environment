global.actions.place_entity = function(player_index, entity, direction, x, y, exact)
    local player = game.get_player(player_index)
    local position = {x = x, y = y}

    -- If character exists on the map, use its reach distance
    local max_distance
    if player['character'] then
        max_distance = player.reach_distance -- Using character's reach distance
    else
        max_distance = player.build_distance
    end

    local dx = player.position.x - x
    local dy = player.position.y - y
    if dy == nil then
        dy = 0
    end
    local distance = math.sqrt(dx * dx + dy * dy)

    if distance > max_distance then
        error("The target position is too far away to place the entity. The player position is " .. player.position.x .. ", " .. player.position.y .. " and the target position is " .. x .. ", " .. y .. ". The distance is " .. distance .. " and the max distance is " .. max_distance .. ". Move closer.")
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

    global.actions.avoid_entity(player_index, entity, position)

    -- **Modified Code Ends Here**
    game.print(direction)
    local can_build = player.can_place_entity{
        name = entity,
        force = player.force,
        position = position,
        direction = global.utils.get_entity_direction(entity, direction)
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
                                direction = global.utils.get_entity_direction(entity, direction)
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
                    direction = global.utils.get_entity_direction(entity, direction),
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
            direction = global.utils.get_entity_direction(entity, direction)
        }
        if not can_build then
            error("Cannot place " .. entity .. " at the target location.")
        end
        local have_built = player.surface.create_entity{
            name = entity,
            force = "player",
            position = position,
            direction = global.utils.get_entity_direction(entity, direction),
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
            direction = global.utils.get_entity_direction(entity, direction),
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
                --local entity_json = game.table_to_json(serialized)-- game.table_to_json(entity
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