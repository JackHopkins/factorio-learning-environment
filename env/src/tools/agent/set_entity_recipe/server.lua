global.actions.set_entity_recipe = function(player_index, recipe_name, x, y)
    local player = global.agent_characters[player_index]
    local surface = player.surface
    --local position = player.position
    local closest_distance = math.huge
    local closest_building = nil

    -- Iterate through all crafting machines in the area
    local area = {{x - 1, y - 1}, {x + 1, y + 1}}
    local buildings = surface.find_entities_filtered{area = area, type = {"assembling-machine", "inserter"}}

    -- Find the closest building
    for _, building in ipairs(buildings) do
        local distance = ((x - building.position.x) ^ 2 + (y - building.position.y) ^ 2) ^ 0.5
        if distance < closest_distance then
            closest_distance = distance
            closest_building = building
        end
    end

    -- If a closest building is found, handle based on its type
    if closest_building then
        local serialized

        -- Handle different entity types
        if closest_building.type == "inserter" then
            -- For filter inserters, set the filter
            if closest_building.name == "filter-inserter" or closest_building.name == "stack-filter-inserter" then
                closest_building.set_filter(1, recipe_name)  -- Set first filter slot
                serialized = global.utils.serialize_entity(closest_building)
            end
        else
            -- Original assembling machine logic
            local recipe = player.force.recipes[recipe_name]
            if recipe and closest_building.get_recipe() ~= recipe then
                closest_building.set_recipe(recipe_name)
            end
            serialized = global.utils.serialize_entity(closest_building)
        end

        local entity_json = game.table_to_json(serialized)
        -- game.print(entity_json)
        return serialized
    else
        error("No building found that could have its recipe or filter set.")
    end
end

