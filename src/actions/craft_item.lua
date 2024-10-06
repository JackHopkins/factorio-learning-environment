global.actions.craft_item = function(player_index, entity, count)
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
        error("Successfully crafted " .. total_crafted .."x but failed to craft "
                .. (count-total_crafted) .. "x " .. entity.." because ".. reason)
    else
        error("Failed to craft " .. count .. "x_" .. entity.." because "..reason)
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
            return "recipe doesnt exist"
        end

        local crafts_needed = math.ceil(count / recipe.products[1].amount)
        local actual_craft_count = crafts_needed * recipe.products[1].amount

        local missing_ingredients = get_missing_ingredients(player, recipe, actual_craft_count)
        if next(missing_ingredients) ~= nil then
            local missing_ingredients_string = ""
            for ingredient_name, ingredient_count in pairs(missing_ingredients) do
                missing_ingredients_string = missing_ingredients_string .. ingredient_name .. " x" .. ingredient_count .. ", "
            end
            return "missing ingredients: " .. missing_ingredients_string:sub(1, -3)  -- Remove trailing ", "
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
        error("Successfully crafted " .. total_crafted .."x but failed to craft "
                .. (count-total_crafted) .. "x " .. entity.." because ".. reason)
    else
        error("Failed to craft " .. count .. "x_" .. entity.." because "..reason)
    end
end