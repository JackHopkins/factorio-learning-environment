global.actions.place_object = function(player_index, entity, direction, x, y, exact)
    local player = game.players[player_index]
    local position = {x=x, y=y}

    -- If character exists on the map, use its reach distance
    local max_distance
    if player.character == nil then
        max_distance = player.build_distance
    else
        max_distance = player.character.reach_distance  -- Using character's reach distance
    end

    local dx = player.position.x - x
    local dy = player.position.y - y
    if dy == nil then
        dy = 0
    end
    local distance = math.sqrt(dx * dx + dy * dy)

    if distance > max_distance then
        error("The target position is too far away to place the entity. Move closer.")
    end

    local function get_entity_direction(entity, direction)
        local prototype = game.entity_prototypes[entity]
        --local cardinals = {defines.direction.north, defines.direction.south, defines.direction.east, defines.direction.west}
        local cardinals = {defines.direction.north, defines.direction.east, defines.direction.south, defines.direction.west}

        if prototype and prototype.name == "offshore-pump" then
            if direction == 1 then
                return defines.direction.north
            elseif direction == 4 then
                return defines.direction.east
            elseif direction == 3 then
                return defines.direction.south
            else
                return defines.direction.west
            end
        end
        local direction_map = {defines.direction.north, defines.direction.east, defines.direction.south, defines.direction.west}

        if prototype and prototype.type == "inserter" then
            -- For some reason there is weird directionality of inserters
            if direction == 1 then
                return cardinals[direction+1 % 4]
                --return defines.direction.north
            elseif direction == 2 then
                return cardinals[direction+1 % 4]
            elseif direction == 3 then
                return cardinals[direction+1 % 4]
            else
                return cardinals[direction+1 % 4]
            end
        elseif  prototype.type == "mining-drill" then
            game.print("Mining drill")

            ---    UP = NORTH = 0 => 1
            ---    RIGHT = EAST = 4 => 6
            ---    LEFT = WEST = 3 => 4
            ---    DOWN = BELOW = BOTTOM = 2 => 2

            if direction == 1 then
                game.print("Direction 1")
                return cardinals[2]
            elseif direction == 2 then
                game.print("Direction 2")
                return cardinals[3]
            elseif direction == 3 then
                game.print("Direction 3")
                return cardinals[4]
            else
                game.print("Direction "..direction)
                return cardinals[1]
            end
        else
            return cardinals[direction]
        end
    end

    if game.entity_prototypes[entity] == nil then
        local name = entity:gsub(" ", "_"):gsub("-", "_")
        error(name .. " isnt something that exists. Did you make a typo? ")
    end

    local count = player.get_item_count(entity)

    if count == 0 then
        local name = entity:gsub(" ", "_"):gsub("-", "_")
        error("No ".. name .." in inventory.")
    end

    local prototype = game.entity_prototypes[entity]
    local collision_box = prototype.collision_box
    local width = math.abs(collision_box.right_bottom.x - collision_box.left_top.x)
    local height = math.abs(collision_box.right_bottom.y - collision_box.left_top.y)

    local function player_collision(player, target_area)
        local character_box = player.character.prototype.collision_box
        local character_area = {
            {player.position.x + character_box.left_top.x, player.position.y + character_box.left_top.y},
            {player.position.x + character_box.right_bottom.x, player.position.y + character_box.right_bottom.y}
        }
        return (character_area[1][1] < target_area[2][1] and character_area[2][1] > target_area[1][1]) and
                (character_area[1][2] < target_area[2][2] and character_area[2][2] > target_area[1][2])
    end

    local target_area = {
        {position.x - width / 2, position.y - height / 2},
        {position.x + width / 2, position.y + height / 2}
    }

    while player_collision(player, target_area) do
        player.teleport({player.position.x + width + 1, player.position.y}, player.surface)
    end

    local can_build = player.can_place_entity{name=entity, force=player.force, position=position, direction=get_entity_direction(entity, direction)}

    if can_build == false or can_build == 0 then

        if not exact then
            local radius = 1
            local max_radius = 10
            local found_position = false
            local new_position

            while not found_position and radius <= max_radius do
                for dx = -radius, radius do
                    for dy = -radius, radius do
                        if dx == -radius or dx == radius or dy == -radius or dy == radius then

                            new_position = {x = position.x + dx, y = position.y + dy}
                            can_build = player.can_place_entity{name=entity, force=player.force, position=new_position, direction=get_entity_direction(entity, direction)}
                            if can_build then
                                found_position = true
                                break
                            end
                        end
                    end
                    if found_position then break end
                end
                radius = radius + 1
            end

            if found_position then
                local have_built = player.surface.create_entity{name=entity, force="player", position=new_position, direction=get_entity_direction(entity, direction), player=player}
                if have_built then
                    player.remove_item{name=entity, count=1}

                    local placed_entity = player.surface.find_entity(entity, new_position)

                    game.print("Placed "..entity.." at "..placed_entity.position.x..","..placed_entity.position.y)
                    --game.print(dump(entity))

                    local serialized = global.utils.serialize_entity(placed_entity)
                   -- local entity_json = game.table_to_json(serialized)-- game.table_to_json(entity)
                    --game.print(entity_json)
                    return serialized
                end
            else
                error("Could not find a suitable position to place " .. entity .. " near the target location.")
            end
        else
            local entities = player.surface.find_entities_filtered{area = target_area, type = "entity"}
            local blocking_entities = {}

            for _, blocking_entity in ipairs(entities) do
                local entity_box = blocking_entity.prototype.collision_box
                local entity_area = {
                    {blocking_entity.position.x + entity_box.left_top.x, blocking_entity.position.y + entity_box.left_top.y},
                    {blocking_entity.position.x + entity_box.right_bottom.x, blocking_entity.position.y + entity_box.right_bottom.y}
                }

                if (entity_area[1][1] < target_area[2][1] and entity_area[2][1] > target_area[1][1]) and
                        (entity_area[1][2] < target_area[2][2] and entity_area[2][2] > target_area[1][2]) then

                    local name = blocking_entity.name
                    local size = " with the size "..width
                    table.insert(blocking_entities, name..size)
                end
            end
            if #blocking_entities > 0 then
                error("Cant place there due to existing " .. table.concat(blocking_entities, "___") .. ", Need "..width.." space. Maybe inspect your surroundings.")
            else
                local resource_present, missing_resource = required_resource_present(entity, position, player.surface)

                local water_tile_present = false
                local tile = player.surface.get_tile(position)
                --for _, tile in ipairs(tiles) do
                if tile.prototype.collision_mask["ground-tile"] then
                    water_tile_present = true
                end

                if not resource_present then
                    error("Cannot place " .. entity .. " due to missing " .. missing_resource .. " on the tile.")
                elseif entity == "offshore-pump" and not water_tile_present then
                    error("Cannot place " .. entity .. " as a single water tile is required.")
                else
                    -- Check for overlapping entities
                    local overlapping_entities = player.surface.find_entities_filtered{area = target_area}
                    local blocking_entities = {}

                    for _, overlapping_entity in ipairs(overlapping_entities) do
                        if overlapping_entity.prototype.collision_box and not overlapping_entity.prototype.has_flag("not-on-map") then
                        --if overlapping_entity.prototype.collision_box and not overlapping_entity.prototype.has_flag("placeable_off_grid") then
                            local name = overlapping_entity.name:gsub(" ", "_"):gsub("-", "_")
                            table.insert(blocking_entities, name)
                        end
                    end

                    if #blocking_entities > 0 then
                        error("Cannot place " .. entity .. " due to existing " .. table.concat(blocking_entities, ", ") .. " at the target position.")
                    else
                        error("Maybe inspect your surroundings before placing")
                    end
                end

            end
        end
    else
        local have_built = player.surface.create_entity{name=entity, force="player", position=position, direction=get_entity_direction(entity, direction), player=player}
        if have_built then
            player.remove_item{name=entity, count=1}

            local entities = player.surface.find_entities_filtered{name=entity, area = {{position.x - 1, position.y - 1}, {position.x + 1, position.y + 1}}}
            local placed_entity = nil

            for _, ent in ipairs(entities) do
                game.print(ent.name)
                game.print(entity)
                if ent.name == entity then
                    placed_entity = ent
                    break
                end
            end
            game.print("Placed "..entity.." at "..placed_entity.position.x..","..placed_entity.position.y)
            -- game.print(dump(entity))

            local serialized = global.utils.serialize_entity(placed_entity)
            -- local entity_json = game.table_to_json(serialized)-- game.table_to_json(entity)
            -- game.print(entity_json)
            return serialized

        end
    end
end