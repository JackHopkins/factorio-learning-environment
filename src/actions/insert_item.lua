global.actions.insert_item = function(player_index, insert_item, count, x, y)
    local player = game.get_player(player_index)
    local position = {x=x, y=y}
    local surface = player.surface

    -- Check if player has enough items
    local item_count = player.get_item_count(insert_item)
    if item_count == 0 then
        error('No '..insert_item..' to place')
    end

    local closest_distance = math.huge
    local closest_entity = nil
    local area = {{position.x - 1, position.y - 1}, {position.x + 1, position.y + 1}}
    local buildings = surface.find_entities_filtered{area = area}

    -- Function to check if an item can be inserted into an entity
    local function can_insert_item(entity, item_name)
        if entity.type == "transport-belt" then
            -- All items that can be on ground can be on belts
            local item_prototype = game.item_prototypes[item_name]
            return item_prototype and not item_prototype.has_flag("only-in-cursor")

        elseif entity.type == "lab" then
            -- Check if the item is a science pack
            local item_prototype = game.item_prototypes[item_name]
            return item_prototype and item_prototype.type == "tool"

        elseif entity.type == "assembling-machine" then
            local recipe = entity.get_recipe()
            if recipe then
               -- Check if the item is an ingredient or the result of the recipe
                for _, ingredient in pairs(recipe.ingredients) do
                    if ingredient.name == item_name then
                        return true
                    end
                end
                -- Check if the item is the result of the recipe
                for _, product in pairs(recipe.products) do
                    if product.name == item_name then
                        return true
                    end
                end
                return false
            end
        elseif entity.type == "furnace" then
            -- Check if it's a fuel
            if game.item_prototypes[item_name].fuel_value > 0 then
                return true
            end
            -- Check furnace inventory for incompatible items
            local inventory = entity.get_inventory(defines.inventory.furnace_source)
            if inventory and not inventory.is_empty() then
                local existing_item = nil
                for i = 1, #inventory do
                    local stack = inventory[i]
                    if stack.valid_for_read then
                        existing_item = stack.name
                        break
                    end
                end
                if existing_item and existing_item ~= item_name then
                    error("Cannot insert " .. item_name .. " - furnace already contains " .. existing_item)
                end
            end
            -- Check if it's a valid ingredient for any furnace recipe
            for _, recipe in pairs(game.recipe_prototypes) do
                if recipe.category == "smelting" then
                    for _, ingredient in pairs(recipe.ingredients) do
                        if ingredient.name == item_name then
                            return true
                        end
                    end
                end
            end
            return false
            ---- Check if it's a fuel
            --if game.item_prototypes[item_name].fuel_value > 0 then
            --    return true
            --end
            ---- Check if it's a valid ingredient for any furnace recipe
            --for _, recipe in pairs(game.recipe_prototypes) do
            --    if recipe.category == "smelting" then
            --        for _, ingredient in pairs(recipe.ingredients) do
            --            if ingredient.name == item_name then
            --                return true
            --            end
            --        end
            --    end
            --end
            --return false
        elseif entity.burner then
            -- Check if it's a fuel
            return game.item_prototypes[item_name].fuel_value > 0
        elseif entity.type == "container" or entity.type == "logistic-container" then
            return true  -- Containers can accept any item
        end
        -- Add more entity types as needed
        return true
    end

    -- Find the closest suitable building
    for _, building in ipairs(buildings) do
        if building.name ~= 'character' and can_insert_item(building, insert_item) then
            local distance = ((position.x - building.position.x) ^ 2 + (position.y - building.position.y) ^ 2) ^ 0.5
            if distance < closest_distance then
                closest_distance = distance
                closest_entity = building
            end
        end
    end

    if closest_entity == nil then
        error("Could not find a nearby entity that can accept " .. insert_item)
    end

    -- Throw an error if the entity is too far away from the player
    if closest_distance > 10 then
        error('Entity too far away. Move closer.')
    end

    -- Function to insert items onto a transport belt
    local function insert_on_belt(belt, item_name, count)
        local inserted = 0
        local transport_line = belt.get_transport_line(1)

        local function try_insert()
            if transport_line.can_insert_at_back() then
                local inserted_on_belt = transport_line.insert_at_back({name = item_name, count = 1})
                if inserted_on_belt then
                    inserted = inserted + 1
                    player.remove_item{name=item_name, count=1}
                    return true
                end
            end
            return false
        end

        -- Initial insertion attempt
        try_insert()

        -- Schedule repeated insertion attempts
        for i = 2, count do
            local ticks_to_wait = 5
            script.on_nth_tick(ticks_to_wait, function(event)
                if try_insert() then
                    if inserted == count then
                        script.on_nth_tick(ticks_to_wait, nil)  -- Stop the scheduled insertions
                    end
                else
                    script.on_nth_tick(ticks_to_wait, nil)  -- Stop if insertion fails
                end
            end)
        end

        return inserted
    end

    -- Determine how many items can be inserted
    local insertable_count = math.min(count, item_count)

   -- Attempt to insert items
    local inserted = 0
    if closest_entity.type == "transport-belt" then
        -- For transport belts, we need to use a different method
        game.print("Inserting ".. insertable_count.. " items onto transport belt...")
        inserted = insert_on_belt(closest_entity, insert_item, insertable_count)
    elseif closest_entity.type == "assembling-machine" then
        local recipe = closest_entity.get_recipe()
        if recipe then
            local is_product = false
            for _, product in pairs(recipe.products) do
                if product.name == insert_item then
                    is_product = true
                    break
                end
            end

            if is_product then
                -- Insert into output inventory
                inserted = closest_entity.get_output_inventory().insert({name=insert_item, count=insertable_count})
            else
                -- Insert into input inventory
                inserted = closest_entity.get_inventory(defines.inventory.assembling_machine_input).insert({name=insert_item, count=insertable_count})
            end
        else
            error("No recipe set for the assembling machine.")
        end
    else
        -- For other entities, use the normal insert method
        inserted = closest_entity.insert{name=insert_item, count=insertable_count}
    end

    game.print("Inserted " .. inserted .. " items.")
    if inserted > 0 then
        -- Only remove successfully inserted items from player
        player.remove_item{name=insert_item, count=inserted}
        game.print("Successfully inserted " .. inserted .. " items.")
        return global.utils.serialize_entity(closest_entity)
    else
        error("Failed to insert any items into the target entity.")
    end
end