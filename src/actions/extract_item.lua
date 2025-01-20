global.actions.extract_item = function(player_index, extract_item, count, x, y)
    local player = game.get_player(player_index)
    local position = {x=x, y=y}
    local surface = player.surface

    -- First validate the request
    if count <= 0 then
        error("\"Invalid count: must be greater than 0\"")
    end

    -- Find all entities with inventories in range
    local search_radius = 10
    local area = {{position.x - search_radius, position.y - search_radius},
                  {position.x + search_radius, position.y + search_radius}}

    local buildings = surface.find_entities_filtered{
        area = area,
        force=player.force
    }

    -- Find the closest building with the item we want
    local closest_distance = math.huge
    local closest_entity = nil
    local found_any_items = false

    for _, building in ipairs(buildings) do
        if building.name ~= 'character' then
            -- Check if entity has an inventory
            local inventory = building.get_inventory(defines.inventory.chest)
            if inventory then
                local item_count = building.get_item_count(extract_item)
                if item_count > 0 then
                    found_any_items = true
                    local distance = ((position.x - building.position.x) ^ 2 +
                                    (position.y - building.position.y) ^ 2) ^ 0.5
                    if distance < closest_distance then
                        closest_distance = distance
                        closest_entity = building
                    end
                end
            end
        end
    end

    -- Error handling in priority order
    if #buildings == 0 then
        error("\"Could not find any entities with inventories in range\"")
    end

    if closest_distance > player.reach_distance then
        error("\"Entity "..closest_entity.name.." is too far away. Move closer.\"")
    end

    if not found_any_items then
        error("\"No " .. extract_item .. " found in any nearby containers\"")
    end

    if not closest_entity then
        error("\"Could not find a valid container with " .. extract_item .. "\"")
    end

    -- Calculate how many items we can actually extract
    local available_count = closest_entity.get_item_count(extract_item)
    local extract_count = math.min(count, available_count)

    -- Create the stack for extraction
    local stack = {name=extract_item, count=extract_count}

    -- Attempt the extraction
    local number_extracted = closest_entity.remove_item(stack)

    if number_extracted > 0 then
        -- Insert items into player inventory
        local inserted = player.insert(stack)

        -- If we couldn't insert all items, put them back in the container
        if inserted < number_extracted then
            stack.count = number_extracted - inserted
            closest_entity.insert(stack)
            number_extracted = inserted
        end

        game.print("Extracted " .. number_extracted .. " " .. extract_item)
        return number_extracted
    else
        -- This should rarely happen given our prior checks
        error("\"Failed to extract " .. extract_item .. "\"")
    end
end

global.actions.extract_item2 = function(player_index, extract_item, count, x, y)
    local player = game.get_player(player_index)
    local position = {x=x, y=y}
    local surface = player.surface

    local stack = {name=extract_item, count=count}

    local closest_distance = math.huge
    local closest_entity = nil
    local area = {{position.x - 10, position.y - 10}, {position.x + 10, position.y + 10}}
    local buildings = surface.find_entities_filtered{area = area}

    -- Find the closest building
    for _, building in ipairs(buildings) do
        if building.get_inventory(defines.inventory.chest) ~= nil and building.name ~= 'character' then
            local distance = ((position.x - building.position.x) ^ 2 + (position.y - building.position.y) ^ 2) ^ 0.5
            if distance < closest_distance then
                closest_distance = distance
                closest_entity = building
            end
        end
    end

    if closest_entity == nil then
        error("\"Could not find a nearby entity to extract from.\"")
    end

    -- If we can find an entity to extract from near the player's x, y position
    local closest_entity_count = closest_entity.get_item_count(extract_item)

    if closest_entity_count == 0 then
        error('No item to extract')
    end

    -- Throw an error if the entity is too far away from the player
    if closest_distance > 10 then
        error('Entity too far away. Move closer.')
    end

    -- Extract items
    local number_extracted = closest_entity.remove_item(stack)

    -- If nothing was extracted
    if number_extracted == 0 then
        error('No item extracted')
    end

    stack.count = number_extracted

    game.print("Extracted "..number_extracted)
    -- Insert the extracted items directly into the player's inventory
    player.insert(stack)

    return number_extracted
end