global.actions.extract_item = function(player_index, extract_item, count, x, y)
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
        error("Could not find a nearby entity to extract from.")
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

    return 1
end