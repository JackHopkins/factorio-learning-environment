global.actions.craft_item = function(player_index, entity, count)
    local player = game.get_player(player_index)

    local function get_missing_ingredients(player, recipe, count)
        local missing_ingredients = {}
        for _, ingredient in pairs(recipe.ingredients) do
            local count_that_player_has = player.get_item_count(ingredient.name)
            local needed = ingredient.amount * count
            if count_that_player_has < needed then
                local difference = needed - count_that_player_has
                missing_ingredients[ingredient.name] = difference
            end
        end
        return missing_ingredients
    end

    local function craft_entity(player, entity_name, count)
        --rcon.print(entity_name)
        local recipe = player.force.recipes[entity_name]

        if not recipe then
            return "recipe doesnt exist"
        end

        local missing_ingredients = get_missing_ingredients(player, recipe, count)
        --rcon.print(dump(missing_ingredients))
        local missing_ingredients_string = ""
        if next(missing_ingredients) ~= nil then
            for ingredient_name, ingredient_count in pairs(missing_ingredients) do
                --local ingredient_recipe = player.force.recipes[ingredient_name]
                --if ingredient_recipe then
                --    local attempted_craft = craft_entity(player, ingredient_name, ingredient_count)
                --    if attempted_craft ~= 1 then
                --        return attempted_craft
                --    end
                --else
                --    return "missing ingredient " .. ingredient_name:gsub("-", "_")
                --end
                missing_ingredients_string = missing_ingredients_string .. ingredient_name .. " x" .. ingredient_count .. ", "

            end
            return "missing ingredients: " .. missing_ingredients_string
        end

        for _, ingredient in pairs(recipe.ingredients) do
            player.remove_item({name = ingredient.name, count = ingredient.amount * count})
        end

        player.insert({name = entity_name, count = count})
        return 1
    end

    --local player = game.players[arg1]
    --local entity_name = arg2
    --local count = tonumber(arg3)
    local successfully_crafted = 0
    local reason = nil
    local k = 1
    for i = 1, count, 1 do
        local did_craft = craft_entity(player, entity, 1)
        if did_craft == 1 then
            successfully_crafted = successfully_crafted + 1
        else
            reason = did_craft
            k = i
            break
        end
    end

    if successfully_crafted == count then
        game.print("Crafted x"..count.." "..entity)
        return 1
    elseif successfully_crafted > 0 then
        error("Successfully crafted " .. successfully_crafted .."x but failed_to_craft_"
                .. (count-successfully_crafted) .. "x " .. entity.." because ".. reason)
    else
        error("Failed_to_craft_" .. (count-k)+1 .. "x_" .. entity.." because "..reason)-- .. tostring(did_craft))
    end

end