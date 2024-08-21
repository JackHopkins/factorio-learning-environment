global.actions.get_resource_patch = function(player_index, resource, x, y)
    local player = game.players[player_index]
    local position = {x = x, y = y}
    local surface = player.surface

    -- Find resource entities at the specified position
    local resource_entities = surface.find_entities_filtered{position = position, name = resource}
    if #resource_entities == 0 then
        error("No resource of type " .. resource .. " at the specified location.")
    end

    -- The function to expand bounding box to include a new area
    local function expand_bounding_box(box, entity)
        box.left_top.x = math.min(box.left_top.x, entity.position.x - (entity.prototype.selection_box.left_top.x))
        box.left_top.y = math.min(box.left_top.y, entity.position.y - (entity.prototype.selection_box.left_top.y))
        box.right_bottom.x = math.max(box.right_bottom.x, entity.position.x + (entity.prototype.selection_box.right_bottom.x))
        box.right_bottom.y = math.max(box.right_bottom.y, entity.position.y + (entity.prototype.selection_box.right_bottom.y))
    end

    -- Recursive function to explore all connected resource entities
    local function explore_resource_patch(entity, visited, bounding_box)
        local key = entity.position.x .. "," .. entity.position.y
        if visited[key] then
            return 0  -- Return 0 as we've already visited this entity, so no resources are counted from this one
        end

        visited[key] = true
        expand_bounding_box(bounding_box, entity)
        local resource_count = entity.amount

        -- Explore neighboring entities in all directions by finding adjacent entities of the same resource type
        local neighbors = surface.find_entities_filtered{
            area = {{entity.position.x - 1, entity.position.y - 1}, {entity.position.x + 1, entity.position.y + 1}},
            type = "resource",
            name = resource
        }
        for _, neighbor in pairs(neighbors) do
            if neighbor ~= entity then  -- Avoid rechecking the same entity
                resource_count = resource_count + explore_resource_patch(neighbor, visited, bounding_box)
            end
        end
        return resource_count
    end

    -- Initialize bounding box and visited entities map
    local bounding_box = {left_top = {x = x, y = y}, right_bottom = {x = x, y = y}}
    local visited = {}

    -- Start exploration from the first found resource entity and calculate the total amount of the resource
    local total_resource = explore_resource_patch(resource_entities[1], visited, bounding_box)

    -- Return the bounding box that encompasses the entire resource patch and the total size of resources
    return {bounding_box = bounding_box, size = total_resource}
end