global.actions.can_place_entity = function(player_index, entity, direction, x, y)
    local player = global.agent_characters[player_index]
    local position = {x = x, y = y}
    
    ---- Check player's reach distance
    local dx = player.position.x - x
    local dy = player.position.y - y
    local distance = math.sqrt(dx * dx + dy * dy)

    if distance > player.reach_distance then
        error("The distance to the target position is too far away to place the entity (" ..distance.."). Move closer.")
    end

    -- if not global.actions.can_reach_entity(player, x, y) then
    --    error("The target position is too far away to place the entity. The player position is " .. player.position.x .. ", " .. player.position.y .. " and the target position is " .. x .. ", " .. y .. ". Move closer.")
    -- end

    -- Check entity prototype exists
    if game.entity_prototypes[entity] == nil then
        local name = entity:gsub(" ", "_"):gsub("-", "_")
        error(name .. " isn't a valid entity prototype. Did you make a typo?")
    end

    -- Check inventory for the entity
    if player.get_item_count(entity) == 0 then
        local name = entity:gsub(" ", "_"):gsub("-", "_")
        error("No " .. name .. " in inventory.")
    end

    -- Get entity direction and collision box
    local direction_enum = get_entity_direction(entity, direction)
    local prototype = game.entity_prototypes[entity]
    local collision_box = prototype.collision_box
    local width = math.abs(collision_box.right_bottom.x - collision_box.left_top.x)
    local height = math.abs(collision_box.right_bottom.y - collision_box.left_top.y)

    -- Define the area where the entity will be placed
    local target_area = {
        {x = position.x - width / 2, y = position.y - height / 2},
        {x = position.x + width / 2, y = position.y + height / 2}
    }

    -- Check for collision with other entities
    local entities = player.surface.find_entities_filtered{area = target_area, force = player.force}

    -- iterate over entities and remove any with the player_character name
    for i = #entities, 1, -1 do
        if entities[i].name == "character" or entities[i].name == 'item-on-ground' then
            table.remove(entities, i)
        end
    end
    if #entities > 1 then
        error("Cannot place the entity at the specified location due to collision with other entities.")
    end

    -- Additional checks for specific entities like offshore-pump
    if entity == "offshore-pump" then
        local tile = player.surface.get_tile(x, y)
        if not tile.prototype.name:match("water") then
            error("Cannot place the entity at the specified position due to lack of water.")
        end
    end

    ---- Check if the entity can be placed
    ---  if placement fails, it tries 11 different positions (i=0 to 10) by moving the player diagonally
    local can_build = global.utils.avoid_entity(player_index, entity, position, direction)
    if not can_build then
        error("Cannot place the entity at the specified position: x="..position.x..", y="..position.y)
    end
    return true
end

function get_entity_direction(entity, direction)
    if direction == nil then
        return defines.direction.north
    end
    local prototype = game.entity_prototypes[entity]
    local cardinals = {defines.direction.north, defines.direction.east, defines.direction.south, defines.direction.west}
    if prototype and prototype.type == "inserter" then
        return cardinals[(direction % 4) + 1]
    else
        return cardinals[direction % 4]
    end
end