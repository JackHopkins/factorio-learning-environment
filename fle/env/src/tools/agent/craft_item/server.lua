global.actions.craft_item = function(player_index, entity, count)
    local player = global.agent_characters[player_index]

    local function calculate_crafting_ticks(recipe, crafts_count)
        -- energy_required is in seconds, multiply by 60 to get ticks
        local ticks_per_craft = (recipe.energy or 0.5) * 60
        return math.ceil(ticks_per_craft * crafts_count)
    end

    local function check_inventory_space(player, item_name, count)
        -- Get the prototype of the item
        local item_prototype = game.item_prototypes[item_name]
        if not item_prototype then
            return false, "Invalid item prototype"
        end

        -- Calculate how many slots this would need
        local stack_size = item_prototype.stack_size
        local slots_needed = math.ceil(count / stack_size)

        -- Check if player has enough free inventory slots
        local inventory = player.get_main_inventory()
        if not inventory then
            return false, "Cannot access player inventory"
        end

        -- Count free slots and partially filled slots of the same item
        local available_slots = 0
        for i = 1, #inventory do
            local stack = inventory[i]
            if not stack.valid_for_read then
                -- Empty slot
                available_slots = available_slots + 1
            elseif stack.name == item_name and stack.count < stack_size then
                -- Partially filled slot of the same item
                available_slots = available_slots + 1
            end
        end

        if available_slots < slots_needed then
            return false, "Inventory is full - requires " .. slots_needed .. " slots but only " .. available_slots .. " available"
        end

        return true
    end


    local function get_missing_ingredients(player, recipe, count)
        local missing_ingredients = {}
        local crafts_needed = math.ceil(count / recipe.products[1].amount)
        for _, ingredient in pairs(recipe.ingredients) do
            local count_that_player_has = player.get_item_count(ingredient.name)
            local needed = ingredient.amount * crafts_needed
            if count_that_player_has < needed then
                local difference = needed - count_that_player_has
                missing_ingredients[ingredient.name] = difference
            end
        end
        return missing_ingredients
    end

    local function get_required_technology(recipe_name, force)
        for _, tech in pairs(force.technologies) do
            if tech.effects then
                for _, effect in pairs(tech.effects) do
                    if effect.type == "unlock-recipe" and effect.recipe == recipe_name then
                        return tech.name
                    end
                end
            end
        end
        return nil
    end

    local function can_craft_recipe(player, recipe_name)
        local recipe = player.force.recipes[recipe_name]
        if not recipe then
            return false, "recipe for " .. recipe_name .. " doesn't exist, it is a raw resource that must be gathered first"
        end
        if not recipe.enabled then
            local required_tech = get_required_technology(recipe_name, player.force)
            local tech_message = required_tech and string.format(" (requires %s technology)", required_tech) or ""
            return false, "recipe for " .. recipe_name .. " is not unlocked yet" .. tech_message .. ". You need to research the technology first"
        end
        if recipe.category ~= "crafting" then
            return false, "Item " .. recipe_name .. " cannot be crafted. Recipe requires a crafting machine or smelting in a furnace"
        end
        return true, recipe
    end

    local function update_production_stats(force, recipe, crafts_count)
        local stats = force.item_production_statistics
        local craft_stats = {crafted_count = crafts_count, inputs = {}, outputs = {}}
        for _, ingredient in pairs(recipe.ingredients) do
            craft_stats.inputs[ingredient.name] = ingredient.amount * crafts_count
            stats.on_flow(ingredient.name, -ingredient.amount * crafts_count)
        end
        for _, product in pairs(recipe.products) do
            if product.type == "item" then
                stats.on_flow(product.name, product.amount * crafts_count)
                craft_stats.outputs[product.name] = product.amount * crafts_count
            end
        end
        table.insert(global.crafted_items, craft_stats)
    end

    -- Single recursive crafting function that handles both fast and slow modes
    local function attempt_craft(player, entity_name, count, attempted_recipes)
        attempted_recipes = attempted_recipes or {}

        -- Prevent infinite recursion
        if attempted_recipes[entity_name] then
            return 0, "recursive crafting loop detected"
        end
        attempted_recipes[entity_name] = true

        local can_craft, recipe_or_error = can_craft_recipe(player, entity_name)
        if not can_craft then
            return 0, recipe_or_error
        end

        local recipe = recipe_or_error
        local crafts_needed = math.ceil(count / recipe.products[1].amount)
        local actual_craft_count = crafts_needed * recipe.products[1].amount

        -- Check for missing ingredients
        local missing_ingredients = get_missing_ingredients(player, recipe, actual_craft_count)
        if next(missing_ingredients) then
            -- Try to craft each missing ingredient
            for ingredient_name, needed_amount in pairs(missing_ingredients) do
                local crafted_amount, error_msg = attempt_craft(player, ingredient_name, needed_amount, attempted_recipes)
                if crafted_amount == 0 then
                    return 0, "couldn't craft a required sub-ingredient for ".. entity_name .. " - " .. ingredient_name .. " - " .. error_msg .. ". Required " ..ingredient_name.. " amount for " .. entity_name .. " - " .. needed_amount .. ")"
                end
            end
        end

        -- Calculate total ticks needed for this craft
        local crafting_ticks = calculate_crafting_ticks(recipe, crafts_needed)


        -- After potentially crafting intermediates, check if we can now craft the original item
        if global.fast then
            -- Only add ticks in fast mode since in slow mode they are added naturally
            global.elapsed_ticks = global.elapsed_ticks + crafting_ticks

            -- Add inventory space check here
            local can_insert, error_msg = check_inventory_space(player, entity_name, actual_craft_count)
            if not can_insert then
                return 0, error_msg
            end

            -- Fast crafting implementation
            local missing = get_missing_ingredients(player, recipe, actual_craft_count)
            if next(missing) then
                local missing_str = ""
                for name, amount in pairs(missing) do
                    missing_str = missing_str .. name .. " x" .. amount .. ", "
                end
                return 0, "still missing ingredients - " .. missing_str:sub(1, -3)
            end

            for _, ingredient in pairs(recipe.ingredients) do
                player.remove_item({name = ingredient.name, count = ingredient.amount * crafts_needed})
            end

            local crafted = player.insert({name = entity_name, count = actual_craft_count})
            if crafted < actual_craft_count then
                player.surface.spill_item_stack(player.position, {name = entity_name, count = actual_craft_count - crafted})
            end

            update_production_stats(player.force, recipe, crafted)
            return crafted, nil
        else
            -- Slow crafting implementation
            local crafted = player.begin_crafting{count=count, recipe=entity_name}
            if crafted == 0 then
                return 0, "unable to begin crafting - check prerequisites and inventory space"
            end
            update_production_stats(player.force, recipe, crafted)
            return crafted, nil
        end
    end

    -- Main crafting logic
    local total_crafted = 0
    local final_error = nil

    while total_crafted < count do
        local remaining = count - total_crafted
        local crafted_amount, error_msg = attempt_craft(player, entity, remaining, {})

        if crafted_amount > 0 then
            total_crafted = total_crafted + crafted_amount
            if not global.fast then
                break
            end
        else
            final_error = error_msg
            break
        end
    end

    if total_crafted >= count or (not global.fast and total_crafted > 0) then
        return count
    elseif total_crafted > 0 then
        error(string.format("\"Successfully crafted %dx but failed to craft %dx %s because %s\"",
            total_crafted, count - total_crafted, entity, final_error))
    else
        error(string.format("\"Failed to craft %dx %s because %s\"",
            count, entity, final_error))
    end
end
