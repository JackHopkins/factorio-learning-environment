global.actions.get_entity = function(player_index, entity, x, y)
    local player = game.players[player_index]
    local position = {x=x, y=y}

    if game.entity_prototypes[entity] == nil then
        local name = entity:gsub(" ", "_"):gsub("-", "_")
        error(name .. " isnt something that exists. Did you make a typo? ")
    end

    local prototype = game.entity_prototypes[entity]
    local collision_box = prototype.collision_box
    local width = math.abs(collision_box.right_bottom.x - collision_box.left_top.x)
    local height = math.abs(collision_box.right_bottom.y - collision_box.left_top.y)

    local target_area = {
        {position.x - width / 2, position.y - height / 2},
        {position.x + width / 2, position.y + height / 2}
    }
    local entities = player.surface.find_entities_filtered{area = target_area, name = entity}
    if #entities > 0 then
        local entity = entities[1]  -- get the first entity of the specified type in the area
        local serialized = global.utils.serialize_entity(entity)
        local entity_json = game.table_to_json(serialized)-- game.table_to_json(entity
        return serialized
    else
        error("No entity of type " .. entity .. " found at the specified position.")
    end
end
