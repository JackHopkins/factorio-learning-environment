-- Function to get inventory fullness information
local function get_inventory_info(entity)
    if entity.get_inventory then
        -- Try common inventory types
        local inv = entity.get_inventory(defines.inventory.chest) or          -- For chests
                   entity.get_inventory(defines.inventory.furnace_source) or  -- For furnaces
                   entity.get_inventory(defines.inventory.assembling_machine_input) -- For assemblers

        if inv then
            -- Get actual item count and inventory capacity
            local item_count = 0
            for i = 1, #inv do
                local stack = inv[i]
                if stack and stack.valid_for_read then
                    item_count = item_count + stack.count
                end
            end

            -- Calculate total capacity (slots * stack size)
            local capacity = #inv * game.item_prototypes[inv[1].name or "iron-plate"].stack_size

            return string.format("(%d/%d items)", item_count, capacity)
        end
    end
    return ""
end

global.actions.insert_item = function(player_index, insert_item, count, x, y, target_name)
    local player = global.agent_characters[player_index]
    local position = {x=x, y=y}
    local surface = player.surface

    -- Check if player has enough items
    local item_count = player.get_item_count(insert_item)
    if item_count == 0 then
        error('\"No '..insert_item..' to insert from your inventory\"')
    end

    local closest_distance = math.huge
    local closest_entity = nil
    local area = {{position.x - 1, position.y - 1}, {position.x + 1, position.y + 1}}
    local buildings = nil

    if target_name then
        buildings = surface.find_entities_filtered{area = area, name=target_name}
    else
        buildings = surface.find_entities_filtered{area = area}
    end

    -- Function to get inventory fullness information
    --local function get_inventory_info(entity)
    --    if entity.get_inventory then
    --        local inv = entity.get_inventory(defines.inventory.chest)
    --        if inv then
    --            return string.format("(%d/%d)", #inv, #inv.get_bar())
    --        end
    --    end
    --    return ""
    --end

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
                    error("\"furnace already contains " .. existing_item.." so cannot insert " .. item_name .."\"")
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
        error("\"Could not find a nearby entity that can accept " .. insert_item.."\"")
    end

    -- Throw an error if the entity is too far away from the player
    if closest_distance > 10 then
        error("\"Entity at ("..closest_entity.position.x..", "..closest_entity.position.y..") is too far away from your position of ("..player.position.x..", "..player.position.y.."), move closer.\"")
    end

    -- Function to insert items onto a transport belt - one at a time
    local function insert_on_belt(belt, item_name)
        local line1 = belt.get_transport_line(1)
        local line2 = belt.get_transport_line(2)

        -- Try first line
        if line1.can_insert_at_back() then
            if line1.insert_at_back({name = item_name, count = 1}) then
                return 1
            end
        end

        -- If first line failed, try second line
        if line2.can_insert_at_back() then
            if line2.insert_at_back({name = item_name, count = 1}) then
                return 1
            end
        end

        return 0  -- Could not insert on either line
    end

    -- Determine how many items can be inserted
    local insertable_count = math.min(count, item_count)

   -- Attempt to insert items
    local inserted = 0
    if closest_entity.type == "transport-belt" then
        -- For transport belts, we need to use a different method
        -- game.print("Inserting ".. insertable_count.. " items onto transport belt...")
        inserted = insert_on_belt(closest_entity, insert_item)
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

    -- game.print("Inserted " .. inserted .. " items.")
    if inserted > 0 then
        -- Only remove successfully inserted items from player
        player.remove_item{name=insert_item, count=inserted}
        -- game.print("Successfully inserted " .. inserted .. " items.")
        return global.utils.serialize_entity(closest_entity)
    else
        local inventory_info = get_inventory_info(closest_entity)
        local error_msg = string.format(
            "\"Failed to insert %s into %s (type %s) at position %s. " ..
            "Attempted to insert %d items. %s %s\"",
            insert_item,
            closest_entity.name,
            closest_entity.type,
            serpent.line(closest_entity.position),
            insertable_count,
            inventory_info ~= "" and "Inventory is full " .. inventory_info or "Entity might not accept this item or has no available space.",
            inventory_info
        )
        error(error_msg)
    end
end