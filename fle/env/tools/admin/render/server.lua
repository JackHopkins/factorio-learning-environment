global.actions.render = function(player_index, include_status, radius)
    local player = global.agent_characters[player_index]
    if not player then
        return nil, "Player not found"
    end
    
    local surface = player.surface
    local player_position = player.position
    
    -- Define search area around player
    local area = {
        left_top = {
            x = player_position.x - radius,
            y = player_position.y - radius
        },
        right_bottom = {
            x = player_position.x + radius,
            y = player_position.y + radius
        }
    }
    
    -- Find all entities in area
    local entities = surface.find_entities(area)
    local entity_data = {}
    
    for _, entity in pairs(entities) do
        if entity.valid then
            local data = {
                name = '\"'..entity.name..'\"',
                position = {
                    x = entity.position.x,
                    y = entity.position.y
                },
                direction = entity.direction or 0
            }

            if entity.type == 'underground-belt' then
                if entity.belt_to_ground_type then
                    data.type = '\"'..entity.belt_to_ground_type..'\"'
                end
            end
            
            -- Add status if requested and available
            if include_status and entity.status then
                data.status = entity.status
            end
            
            table.insert(entity_data, data)
        end
    end
    
    -- Get water tiles
    local water_tiles = {}
    for x = math.floor(area.left_top.x), math.ceil(area.right_bottom.x) do
        for y = math.floor(area.left_top.y), math.ceil(area.right_bottom.y) do
            local tile = surface.get_tile(x, y)
            if tile and tile.valid and tile.name and (tile.name:find("water") or tile.name == "deepwater" or tile.name == "water") then
                table.insert(water_tiles, {
                    x = tile.position.x,
                    y = tile.position.y,
                    name = '\"'..tile.name..'\"'
                })
            end
        end
    end
    
    -- Get resource patches
    local resource_types = {"iron-ore", "copper-ore", "coal", "stone", "uranium-ore", "crude-oil"}
    local resources = {}
    
    for _, resource_type in ipairs(resource_types) do
        local resource_entities = surface.find_entities_filtered{
            area = {{area.left_top.x, area.left_top.y}, {area.right_bottom.x, area.right_bottom.y}},
            name = resource_type
        }
        
        for _, entity in ipairs(resource_entities) do
            local resource_data = {
                name = '\"'..entity.name..'\"',
                position = {
                    x = entity.position.x,
                    y = entity.position.y
                },
                amount = entity.amount
            }
            
            table.insert(resources, resource_data)
        end
    end
    
    return {
        entities = entity_data,
        water_tiles = water_tiles,
        resources = resources
    }
end