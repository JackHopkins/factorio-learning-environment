global.actions.render = function(player_index, method, arg1, arg2, arg3, arg4)
    local player = global.agent_characters[player_index]
    local position, bounding_box, radius

    if method == "bounding_box" then
        -- If using bounding box method
        bounding_box = {
            left_top = {x = tonumber(arg1), y = tonumber(arg2)},
            right_bottom = {x = tonumber(arg3), y = tonumber(arg4)}
        }
    elseif method == "radius" then
        -- If using radius method
        local pos_x = tonumber(arg1)
        local pos_y = tonumber(arg2)
        radius = tonumber(arg3) or 40

        position = {x = pos_x, y = pos_y}
        bounding_box = {
            left_top = {x = position.x - radius, y = position.y - radius},
            right_bottom = {x = position.x + radius, y = position.y + radius}
        }
    else
        return "\"Error: Invalid method\""
    end

    -- Get all entities
    local area = {
        {bounding_box.left_top.x, bounding_box.left_top.y},
        {bounding_box.right_bottom.x, bounding_box.right_bottom.y}
    }

    -- Get water tiles
    local water_tiles = {}
    for x = math.floor(area[1][1]), math.ceil(area[2][1]) do
        for y = math.floor(area[1][2]), math.ceil(area[2][2]) do
            local tile = player.surface.get_tile(x, y)
            if tile and tile.valid and tile.name and (tile.name:find("water") or tile.name == "deepwater" or tile.name == "water") then
                table.insert(water_tiles, {
                    x = tile.position.x,
                    y = tile.position.y,
                    name = "\""..tile.name.."\""
                })
            end
        end
    end

    -- Get resource entities
    local resource_types = {"iron-ore", "copper-ore", "coal", "stone", "uranium-ore", "crude-oil"}
    local resources = {}

    for _, resource_type in ipairs(resource_types) do
        local resource_entities = player.surface.find_entities_filtered{
            area = area,
            name = resource_type
        }

        for _, entity in ipairs(resource_entities) do
            local resource_data = {
                name = "\""..entity.name.."\"",
                position = {
                    x = entity.position.x,
                    y = entity.position.y
                },
                amount = entity.amount
            }

            table.insert(resources, resource_data)
        end
    end

    -- Get trees
    local trees = {}
    local tree_entities = player.surface.find_entities_filtered{
        area = area,
        type = "tree"
    }

    for _, tree in ipairs(tree_entities) do
        local tree_data = {
            name = "\""..tree.name.."\"",
            position = {
                x = tree.position.x,
                y = tree.position.y
            }
        }

        -- Add tree size if available
        if tree.prototype and tree.prototype.tree_color_count then
            tree_data.size = tree.prototype.tree_color_count
        end

        table.insert(trees, tree_data)
    end

    -- Get rocks
    local rocks = {}
    local rock_entities = player.surface.find_entities_filtered{
        area = area,
        type = "simple-entity"
    }

    for _, rock in ipairs(rock_entities) do
        -- Check if it's actually a rock (naming convention for rocks typically includes "rock" or "stone")
        if rock.name and (rock.name:find("rock") or rock.name:find("stone")) then
            local rock_data = {
                name = "\""..rock.name.."\"",
                position = {
                    x = rock.position.x,
                    y = rock.position.y
                }
            }

            table.insert(rocks, rock_data)
        end
    end

    -- Get electricity network information
    local electricity_networks = {}
    local electric_poles = player.surface.find_entities_filtered{
        area = area,
        type = {"electric-pole", "power-switch"}
    }

    -- Process electric poles to get network information
    for _, pole in ipairs(electric_poles) do
        if pole.valid and pole.electric_network_id then
            local network_id = pole.electric_network_id
            local supply_area = pole.prototype.supply_area_distance or 0

            -- Get the area this pole covers
            local pole_data = {
                position = {
                    x = pole.position.x,
                    y = pole.position.y
                },
                network_id = network_id,
                supply_area = supply_area,
                name = "\""..pole.name.."\""
            }

            table.insert(electricity_networks, pole_data)
        end
    end

    -- Combine all data for response
    local render_data = {
        water_tiles = water_tiles,
        resources = resources,
        trees = trees,
        rocks = rocks,
        electricity_networks = electricity_networks,
        bounding_box = bounding_box,
        position = position
    }

    return dump(render_data)
end
