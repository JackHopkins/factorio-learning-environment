global.actions.get_entity = function(player_index, entity, x, y)
    local player = global.agent_characters[player_index]
    local position = {x=x, y=y}

    if game.entity_prototypes[entity] == nil then
        local name = entity:gsub(" ", "_"):gsub("-", "_")
        error(name .. " isnt something that exists. Did you make a typo? ")
    end

    local prototype = game.entity_prototypes[entity]
    --local collision_box = prototype.collision_box
    local width = 1--math.abs(collision_box.right_bottom.x - collision_box.left_top.x)
    local height = 1--math.abs(collision_box.right_bottom.y - collision_box.left_top.y)

    -- game.print("Width: " .. width)
    -- game.print("Height: " .. height)

    local target_area = {
        {position.x - width , position.y - height },
        {position.x + width , position.y + height }
    }
    --local entities = player.surface.find_entities_filtered{area = target_area} --, name = entity}
    local entities = player.surface.find_entities_filtered{area = target_area, name = entity}
    -- game.print("Number of entities found: " .. #entities)

    local closest_distance = math.huge
    local closest_entity = nil

    for _, building in ipairs(entities) do
        if building.name ~= 'character' then
            local distance = ((position.x - building.position.x) ^ 2 +
                            (position.y - building.position.y) ^ 2) ^ 0.5
            if distance < closest_distance then
                closest_distance = distance
                closest_entity = building
            end
        end
    end

    if closest_entity ~= nil then
        local entity = closest_entity  -- get the first entity of the specified type in the area
        local serialized = global.utils.serialize_entity(entity)
        --local entity_json = game.table_to_json(serialized)-- game.table_to_json(entity
        return serialized
    else
        error("\"No entity of type " .. entity .. " found at the specified position.\"")
    end
end
