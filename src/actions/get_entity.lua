global.actions.get_entity = function(player_index, entity, x, y)
    local player = game.get_player(player_index)
    local position = {x=x, y=y}

    if game.entity_prototypes[entity] == nil then
        local name = entity:gsub(" ", "_"):gsub("-", "_")
        error(name .. " isnt something that exists. Did you make a typo? ")
    end

    local prototype = game.entity_prototypes[entity]
    --local collision_box = prototype.collision_box
    local width = 0.5--math.abs(collision_box.right_bottom.x - collision_box.left_top.x)
    local height = 0.5--math.abs(collision_box.right_bottom.y - collision_box.left_top.y)

    game.print("Width: " .. width)
    game.print("Height: " .. height)

    local target_area = {
        {position.x - width , position.y - height },
        {position.x + width , position.y + height }
    }
    --local entities = player.surface.find_entities_filtered{area = target_area} --, name = entity}
    local entities = player.surface.find_entities_filtered{area = target_area, name = entity}
    game.print("Number of entities found: " .. #entities)

    if #entities > 0 then
        local entity = entities[1]  -- get the first entity of the specified type in the area
        local serialized = global.utils.serialize_entity(entity)
        --local entity_json = game.table_to_json(serialized)-- game.table_to_json(entity
        return serialized
    else
        error("\"No entity of type " .. entity .. " found at the specified position.\"")
    end
end
