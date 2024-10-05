global.actions.insert_item = function(player_index, insert_item, count, x, y)
    local player = game.get_player(player_index)

    local position = {x=x, y=y}
    local surface = player.surface


    -- If the player has enough items
    local item_count = player.get_item_count(insert_item)

    if item_count == 0 then
        error('No '..insert_item..' to place')
    end

    local closest_distance = math.huge
    local closest_entity = nil
    local area = {{position.x - 10, position.y - 10}, {position.x + 10, position.y + 10}}
    local buildings = surface.find_entities_filtered{area = area}

    -- Find the closest building
    for _, building in ipairs(buildings) do
        if building.name ~= 'character' then
            if building.get_inventory(defines.inventory.chest) ~= nil or
                    building.get_inventory(defines.inventory.furnace_source) ~= nil then
                local distance = ((position.x - building.position.x) ^ 2 + (position.y - building.position.y) ^ 2) ^ 0.5
                if distance < closest_distance then
                    closest_distance = distance
                    closest_entity = building
                end
            end
        end
    end

    if closest_entity == nil then
        error("Could not find a nearby entity to insert into.")
    else

        -- Check if the entity can accept the item
        local closest_entity_count = closest_entity.get_item_count(insert_item)

        if closest_entity_count == nil then
            error('No possible entity to fuel')
        end

        -- Throw an error if the entity is too far away from the player
        if closest_distance > 10 then
            error('Entity too far away. Move closer.')
        end

        -- Make transaction
        local number_removed = player.remove_item{name=insert_item, count=count}

        local number_inserted = closest_entity.insert{name=insert_item, count=number_removed}

        if number_inserted ~= number_removed then
            closest_entity.remove_item{name=insert_item, count=number_inserted}
            player.insert{name=insert_item, count=number_removed}
            error('Transaction not executed')
        else
            game.print("Inserted "..number_removed)
            return global.utils.serialize_entity(closest_entity)
        end

    end

end