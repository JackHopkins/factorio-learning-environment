global.actions.set_entity_recipe = function(player_index, recipe_name, x, y)
    local player = game.get_player(player_index)
    local surface = player.surface
    --local position = player.position
    local closest_distance = math.huge
    local closest_building = nil

    -- Iterate through all crafting machines in the area
    local area = {{x - 2, y - 2}, {x + 2, y + 2}}
    local buildings = surface.find_entities_filtered{area = area, type = "assembling-machine"}

    -- Find the closest building
    for _, building in ipairs(buildings) do
        local distance = ((x - building.position.x) ^ 2 + (y - building.position.y) ^ 2) ^ 0.5
        if distance < closest_distance then
            closest_distance = distance
            closest_building = building
        end
    end

    -- If a closest building is found and it supports the given recipe, set the recipe
    if closest_building then
        local recipe = player.force.recipes[recipe_name]
        if recipe and closest_building.get_recipe() ~= recipe then
            closest_building.set_recipe(recipe_name)

            local serialized = global.utils.serialize_entity(closest_building)
            local entity_json = game.table_to_json(serialized)-- game.table_to_json(entity)
            game.print(entity_json)
            return serialized

        else
            error("Recipe already set.")
        end
    else
        error("No building found that could have its recipe set.")
    end
end

