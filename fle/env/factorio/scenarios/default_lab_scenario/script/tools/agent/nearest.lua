global.actions.nearest = function(player_index, resource)
    local player = global.agent_characters[player_index]

    local function normalize_resource_name(resource)
        if resource == "copper" then
            return "copper-ore"
        elseif resource == "iron" then
            return "iron-ore"
        elseif resource == "uranium" then
            return "uranium-ore"
        else
            return resource
        end
    end

    local normalized_resource = normalize_resource_name(resource)

    local function find_nearest(player, resource)
        local surface = player.surface
        local position = player.position
        local closest_distance = math.huge
        local closest = nil
        local entities

        if resource == "wood" then
            entities = surface.find_entities_filtered{
                area = {{position.x - 500, position.y - 500}, {position.x + 500, position.y + 500}},
                type = "tree"
            }
        elseif resource == "water" then
            local water_positions = surface.find_tiles_filtered{
                area = {{position.x - 500, position.y - 500}, {position.x + 500, position.y + 500}},
                name = "water"
            }
            for _, water_tile in ipairs(water_positions) do
                local distance = ((position.x - water_tile.position.x) ^ 2 + (position.y - water_tile.position.y) ^ 2) ^ 0.5
                if distance < closest_distance then
                    closest_distance = distance
                    closest = water_tile.position
                end
            end
            if closest == nil then
                error("\"Could not find an entity called "..resource.."\"")
            end
            --return { x = position.x - closest.x, y = position.y - closest.y }
            return {x = closest.x, y = closest.y}
        else
            entities = surface.find_entities_filtered{
                area = {{position.x - 500, position.y - 500}, {position.x + 500, position.y + 500}},
                name = resource
            }
        end

        for _, entity in ipairs(entities) do
            local distance = ((position.x - entity.position.x) ^ 2 + (position.y - entity.position.y) ^ 2) ^ 0.5
            if distance < closest_distance then
                closest_distance = distance
                closest = entity.position
            end
        end

        if closest == nil then
            error("\"Could not find an entity called "..resource.."\"")
        end
        -- game.print("Distance to "..resource.." is "..closest_distance)
        return {x= closest.x, y = closest.y}
        --return { x = position.x - closest.x, y = position.y - closest.y }
    end

    return find_nearest(player, normalized_resource)
end
