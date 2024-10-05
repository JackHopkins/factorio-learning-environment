global.actions.get_resource_patch = function(player_index, resource, x, y, radius)
    local player = game.get_player(player_index)
    local position = {x = x, y = y}
    local surface = player.surface

    -- Function to expand bounding box
    local function expand_bounding_box(box, pos)
        box.left_top.x = math.min(box.left_top.x, pos.x)
        box.left_top.y = math.min(box.left_top.y, pos.y)
        box.right_bottom.x = math.max(box.right_bottom.x, pos.x + 1)
        box.right_bottom.y = math.max(box.right_bottom.y, pos.y + 1)
    end

    -- Initialize bounding box
    local bounding_box = {left_top = {x = x, y = y}, right_bottom = {x = x, y = y}}

    if resource == "water" then
        local water_tiles = surface.find_tiles_filtered{position = position, name = "water", radius = radius}
        if #water_tiles == 0 then
            error("No water at the specified location.")
        end

        local total_water_tiles = 0
        for _, tile in pairs(water_tiles) do
            expand_bounding_box(bounding_box, tile.position)
            total_water_tiles = total_water_tiles + 1
        end

        return {bounding_box = bounding_box, size = total_water_tiles}
    elseif resource == "wood" then
        local trees = surface.find_entities_filtered{
            position = position,
            type = "tree",
            radius = radius
        }
        if #trees == 0 then
            error("No trees at the specified location.")
        end
        local total_wood = 0
        for _, tree in pairs(trees) do
            expand_bounding_box(bounding_box, tree.position)
            -- Estimate wood amount based on tree prototype
            local tree_product = tree.prototype.mineable_properties.products[1]
            if tree_product and tree_product.name == "wood" then
                total_wood = total_wood + tree_product.amount
            else
                -- If wood amount is not specified, assume 1 wood per tree
                total_wood = total_wood + 1
            end
        end
        return {bounding_box = bounding_box, size = total_wood}
    else
        local resource_entities = surface.find_entities_filtered{position = position, name = resource, radius = radius}
        if #resource_entities == 0 then
            error("No resource of type " .. resource .. " at the specified location.")
        end

        -- Recursive function to explore all connected resource entities
        local function explore_resource_patch(entity, visited)
            local key = entity.position.x .. "," .. entity.position.y
            if visited[key] then
                return 0
            end
            visited[key] = true
            expand_bounding_box(bounding_box, entity.position)
            local resource_count = entity.amount

            local neighbors = surface.find_entities_filtered{
                area = {{entity.position.x - 1, entity.position.y - 1}, {entity.position.x + 1, entity.position.y + 1}},
                type = "resource",
                name = resource
            }
            for _, neighbor in pairs(neighbors) do
                if neighbor ~= entity then
                    resource_count = resource_count + explore_resource_patch(neighbor, visited)
                end
            end
            return resource_count
        end

        local visited = {}
        local total_resource = explore_resource_patch(resource_entities[1], visited)

        return {bounding_box = bounding_box, size = total_resource}
    end
end