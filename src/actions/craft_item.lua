global.actions.craft_item = function(player_index, entity, count)
    local player = game.get_player(player_index)

    -- Helper functions remain the same
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

    local function can_craft_recipe(player, recipe_name)
        local recipe = player.force.recipes[recipe_name]
        if not recipe then
            return false, "recipe doesn't exist"
        end
        if not recipe.enabled then
            return false, "recipe not unlocked"
        end
        if recipe.category ~= "crafting" then
            return false, "recipe requires specific crafting machine"
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
                    return 0, "couldn't craft intermediate " .. ingredient_name .. ": " .. error_msg
                end
            end
        end

        -- After potentially crafting intermediates, check if we can now craft the original item
        if global.fast then
            -- Fast crafting implementation
            local missing = get_missing_ingredients(player, recipe, actual_craft_count)
            if next(missing) then
                local missing_str = ""
                for name, amount in pairs(missing) do
                    missing_str = missing_str .. name .. " x" .. amount .. ", "
                end
                return 0, "still missing ingredients: " .. missing_str:sub(1, -3)
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

global.actions.craft_item2 = function(player_index, entity, count)
    local player = game.get_player(player_index)

    -- Helper function to check missing ingredients
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

    -- Helper function to check if recipe can be crafted (has prerequisites and is hand-craftable)
    local function can_craft_recipe(player, recipe_name)
        local recipe = player.force.recipes[recipe_name]
        if not recipe then
            return false, "recipe doesn't exist"
        end
        if not recipe.enabled then
            return false, "recipe not unlocked"
        end
        -- Check if recipe is hand-craftable (not machine-only)
        if recipe.category ~= "crafting" then
            return false, "recipe requires specific crafting machine"
        end
        return true, recipe
    end

    -- Helper function to update production statistics
    local function update_production_stats(force, recipe, crafts_count)
        local stats = force.item_production_statistics
        -- Record consumed ingredients
        for _, ingredient in pairs(recipe.ingredients) do
            stats.on_flow(ingredient.name, -ingredient.amount * crafts_count)
        end
        -- Record produced items
        for _, product in pairs(recipe.products) do
            if product.type == "item" then
                stats.on_flow(product.name, product.amount * crafts_count)
            end
        end
    end

    -- Slow crafting implementation
    local function slow_craft(player, entity_name, count)
        local can_craft, recipe_or_error = can_craft_recipe(player, entity_name)
        if not can_craft then
            return recipe_or_error
        end
        local recipe = recipe_or_error

        -- Check for missing ingredients
        local missing_ingredients = get_missing_ingredients(player, recipe, count)
        if next(missing_ingredients) then
            local missing_str = ""
            for name, amount in pairs(missing_ingredients) do
                missing_str = missing_str .. name .. " x" .. amount .. ", "
            end
            return "missing ingredients: " .. missing_str:sub(1, -3)
        end

        -- Attempt to queue crafting
        local crafted = player.begin_crafting{count=count, recipe=entity_name}
        if crafted == 0 then
            return "unable to begin crafting - check prerequisites and inventory space"
        end

        -- Update production statistics for successful craft
        update_production_stats(player.force, recipe, crafted)

        return crafted
    end

    -- Fast crafting implementation with proper restrictions
    local function fast_craft(player, entity_name, count)
        local can_craft, recipe_or_error = can_craft_recipe(player, entity_name)
        if not can_craft then
            return recipe_or_error
        end
        local recipe = recipe_or_error

        local crafts_needed = math.ceil(count / recipe.products[1].amount)
        local actual_craft_count = crafts_needed * recipe.products[1].amount

        -- Check for missing ingredients but don't try to craft them
        local missing_ingredients = get_missing_ingredients(player, recipe, actual_craft_count)
        if next(missing_ingredients) then
            local missing_str = ""
            for name, amount in pairs(missing_ingredients) do
                missing_str = missing_str .. name .. " x" .. amount .. ", "
            end
            return "missing ingredients: " .. missing_str:sub(1, -3)
        end

        -- Remove ingredients and create items
        for _, ingredient in pairs(recipe.ingredients) do
            player.remove_item({name = ingredient.name, count = ingredient.amount * crafts_needed})
        end

        local crafted = player.insert({name = entity_name, count = actual_craft_count})
        if crafted < actual_craft_count then
            player.surface.spill_item_stack(player.position, {name = entity_name, count = actual_craft_count - crafted})
        end

        -- Update production statistics for successful craft
        update_production_stats(player.force, recipe, crafted)

        return actual_craft_count
    end

    -- Main crafting logic
    local total_crafted = 0
    local reason = ''

    -- Choose crafting method based on global.fast setting
    local craft_function = global.fast and fast_craft or slow_craft

    while total_crafted < count do
        local remaining = count - total_crafted
        local did_craft = craft_function(player, entity, remaining)
        if type(did_craft) == "number" then
            total_crafted = total_crafted + did_craft
            if not global.fast then
                -- For slow crafting, we queue everything at once and return
                break
            end
        else
            reason = did_craft
            break
        end
    end

    if total_crafted >= count or (not global.fast and total_crafted > 0) then
        return count
    elseif total_crafted > 0 then
        error("\"Successfully crafted " .. total_crafted .."x but failed to craft "
                .. (count-total_crafted) .. "x " .. entity.." because ".. reason.."\"")
    else
        error("\"Failed to craft " .. count .. "x " .. entity.." because "..reason.."\"")
    end
end

global.actions.craft_item3 = function(player_index, entity, count)
    local player = game.get_player(player_index)

    -- Helper function to check missing ingredients
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

    -- Helper function to check if recipe can be crafted (has prerequisites)
    local function can_craft_recipe(player, recipe_name)
        local recipe = player.force.recipes[recipe_name]
        if not recipe then
            return false, "recipe doesn't exist"
        end
        if not recipe.enabled then
            return false, "recipe not unlocked"
        end
        -- Check if recipe is hand-craftable (not machine-only)
        if recipe.category ~= "crafting" then
            return false, "recipe requires specific crafting machine"
        end
        return true, recipe
    end

    -- Helper function to update production statistics
    local function update_production_stats(force, recipe, crafts_count)
        local stats = force.item_production_statistics
        -- Record consumed ingredients
        for _, ingredient in pairs(recipe.ingredients) do
            stats.on_flow(ingredient.name, -ingredient.amount * crafts_count)
        end
        -- Record produced items
        for _, product in pairs(recipe.products) do
            if product.type == "item" then
                stats.on_flow(product.name, product.amount * crafts_count)
            end
        end
    end


    -- Slow crafting implementation
    local function slow_craft(player, entity_name, count)
        local can_craft, recipe_or_error = can_craft_recipe(player, entity_name)
        if not can_craft then
            return recipe_or_error
        end
        local recipe = recipe_or_error

        -- Check for missing ingredients
        local missing_ingredients = get_missing_ingredients(player, recipe, count)
        if next(missing_ingredients) then
            local missing_str = ""
            for name, amount in pairs(missing_ingredients) do
                missing_str = missing_str .. name .. " x" .. amount .. ", "
            end
            return "missing ingredients: " .. missing_str:sub(1, -3)
        end

        -- Attempt to queue crafting
        local crafted = player.begin_crafting{count=count, recipe=entity_name}
        if crafted == 0 then
            return "unable to begin crafting - check prerequisites and inventory space"
        end

        -- Update production statistics for successful craft
        update_production_stats(player.force, recipe, crafted)

        return crafted
    end

    -- Fast crafting implementation (existing logic)
    local function fast_craft(player, entity_name, count)
         local can_craft, recipe_or_error = can_craft_recipe(player, entity_name)
        if not can_craft then
            return recipe_or_error
        end
        local recipe = recipe_or_error

        local crafts_needed = math.ceil(count / recipe.products[1].amount)
        local actual_craft_count = crafts_needed * recipe.products[1].amount

        local missing_ingredients = get_missing_ingredients(player, recipe, actual_craft_count)

        -- Try to craft missing ingredients
        for ingredient_name, ingredient_count in pairs(missing_ingredients) do
            local ingredient_recipe = player.force.recipes[ingredient_name]
            if ingredient_recipe or can_craft_recipe(player, ingredient_name) then
                local crafted = fast_craft(player, ingredient_name, ingredient_count)
                if type(crafted) ~= "number" or crafted < ingredient_count then
                    return "failed to craft intermediate ingredient: " .. ingredient_name
                end
            else
                return "missing ingredients that can't be crafted: " .. ingredient_name
            end
        end

        -- Check again for missing ingredients after crafting intermediates
        missing_ingredients = get_missing_ingredients(player, recipe, actual_craft_count)
        if next(missing_ingredients) ~= nil then
            local missing_ingredients_string = ""
            for ingredient_name, ingredient_count in pairs(missing_ingredients) do
                missing_ingredients_string = missing_ingredients_string .. ingredient_name .. " x" .. ingredient_count .. ", "
            end
            return "still missing ingredients after crafting intermediates: " .. missing_ingredients_string:sub(1, -3)
        end

        -- Remove ingredients and create items
        for _, ingredient in pairs(recipe.ingredients) do
            player.remove_item({name = ingredient.name, count = ingredient.amount * crafts_needed})
        end

        local crafted = player.insert({name = entity_name, count = actual_craft_count})
        if crafted < actual_craft_count then
            player.surface.spill_item_stack(player.position, {name = entity_name, count = actual_craft_count - crafted})
        end

        -- Update production statistics for successful craft
        update_production_stats(player.force, recipe, crafted)

        return actual_craft_count
    end

    -- Main crafting logic
    local total_crafted = 0
    local reason = ''

    -- Choose crafting method based on global.fast setting
    local craft_function = global.fast and fast_craft or slow_craft

    while total_crafted < count do
        local remaining = count - total_crafted
        local did_craft = craft_function(player, entity, remaining)
        if type(did_craft) == "number" then
            total_crafted = total_crafted + did_craft
            if not global.fast then
                -- For slow crafting, we queue everything at once and return
                break
            end
        else
            reason = did_craft
            break
        end
    end

    if total_crafted >= count or (not global.fast and total_crafted > 0) then
        return count
    elseif total_crafted > 0 then
        error("\"Successfully crafted " .. total_crafted .."x but failed to craft "
                .. (count-total_crafted) .. "x " .. entity.." because ".. reason.."\"")
    else
        error("\"Failed to craft " .. count .. "x " .. entity.." because "..reason.."\"")
    end
end

global.actions.craft_item2 = function(player_index, entity, count)
    local player = game.get_player(player_index)

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

    local function craft_entity(player, entity_name, count)
        local recipe = player.force.recipes[entity_name]
        if not recipe then
            return "recipe doesn't exist"
        end

        local crafts_needed = math.ceil(count / recipe.products[1].amount)
        local actual_craft_count = crafts_needed * recipe.products[1].amount

        local missing_ingredients = get_missing_ingredients(player, recipe, actual_craft_count)

        -- Try to craft missing ingredients
        for ingredient_name, ingredient_count in pairs(missing_ingredients) do
            local ingredient_recipe = player.force.recipes[ingredient_name]
            if ingredient_recipe then
                local crafted = craft_entity(player, ingredient_name, ingredient_count)
                if type(crafted) ~= "number" or crafted < ingredient_count then
                    return "failed to craft intermediate ingredient: " .. ingredient_name
                end
            else
                return "missing ingredients that can't be crafted: " .. ingredient_name
            end
        end

        -- Check again for missing ingredients after crafting intermediates
        missing_ingredients = get_missing_ingredients(player, recipe, actual_craft_count)
        if next(missing_ingredients) ~= nil then
            local missing_ingredients_string = ""
            for ingredient_name, ingredient_count in pairs(missing_ingredients) do
                missing_ingredients_string = missing_ingredients_string .. ingredient_name .. " x" .. ingredient_count .. ", "
            end
            return "still missing ingredients after crafting intermediates: " .. missing_ingredients_string:sub(1, -3)
        end

        for _, ingredient in pairs(recipe.ingredients) do
            player.remove_item({name = ingredient.name, count = ingredient.amount * crafts_needed})
        end

        local crafted = player.insert({name = entity_name, count = actual_craft_count})
        if crafted < actual_craft_count then
            player.surface.spill_item_stack(player.position, {name = entity_name, count = actual_craft_count - crafted})
        end

        return actual_craft_count
    end

    local total_crafted = 0
    local reason = ''

    while total_crafted < count do
        local remaining = count - total_crafted
        local did_craft = craft_entity(player, entity, remaining)
        if type(did_craft) == "number" then
            total_crafted = total_crafted + did_craft
        else
            reason = did_craft
            break
        end
    end

    if total_crafted >= count then
        game.print("Crafted x"..count.." "..entity)
        return count
    elseif total_crafted > 0 then
        error("\"Successfully crafted " .. total_crafted .."x but failed to craft "
                .. (count-total_crafted) .. "x " .. entity.." because ".. reason.."\"")
    else
        error("\"Failed to craft " .. count .. "x_" .. entity.." because "..reason.."\"")
    end
end