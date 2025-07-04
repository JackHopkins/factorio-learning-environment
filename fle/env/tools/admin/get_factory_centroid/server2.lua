-- Helper function to calculate factory bounds
function calculate_factory_bounds(force)
    local min_x = math.huge
    local max_x = -math.huge
    local min_y = math.huge
    local max_y = -math.huge

    -- Entity types to exclude from bounds calculation
    local excluded_types = {
        ["player"] = true,
        ["character"] = true,
        ["character-corpse"] = true,
        ["item-entity"] = true,
        ["particle"] = true,
        ["projectile"] = true,
        ["resource"] = true,
        ["tree"] = true,
        ["simple-entity"] = true
    }

    -- Iterate through all surfaces
    for _, surface in pairs(game.surfaces) do
        local entities = surface.find_entities_filtered{
            force = force
        }

        for _, entity in pairs(entities) do
            if entity.valid and not excluded_types[entity.type] then
                -- Get entity bounding box
                local box = entity.bounding_box

                -- Update min/max coordinates
                min_x = math.min(min_x, box.left_top.x)
                max_x = math.max(max_x, box.right_bottom.x)
                min_y = math.min(min_y, box.left_top.y)
                max_y = math.max(max_y, box.right_bottom.y)
            end
        end
    end

    -- Check if we found any entities
    if min_x == math.huge then
        return nil
    end

    return {
        left_top = {x = min_x, y = min_y},
        right_bottom = {x = max_x, y = max_y},
        width = max_x - min_x,
        height = max_y - min_y
    }
end


global.actions.get_factory_centroid = function(player)
    -- Default to player force if none specified
    local force = "player"

    -- Get all surfaces in the game
    local surfaces = game.surfaces

    -- Variables to track totals
    local total_x = 0
    local total_y = 0
    local entity_count = 0

    -- Entity types to exclude from centroid calculation
    local excluded_types = {
        ["player"] = true,
        ["character"] = true,
        ["character-corpse"] = true,
        ["item-entity"] = true,  -- dropped items
        ["particle"] = true,
        ["projectile"] = true,
        ["resource"] = true,     -- ore patches
        ["tree"] = true,
        ["simple-entity"] = true -- rocks and other decorative elements
    }

    -- Iterate through all surfaces
    for _, surface in pairs(surfaces) do
        -- Get all entities on the surface belonging to the specified force
        local entities = surface.find_entities_filtered{
            force = force
        }

        -- Add up positions of valid entities
        for _, entity in pairs(entities) do
            if entity.valid and not excluded_types[entity.type] then
                total_x = total_x + entity.position.x
                total_y = total_y + entity.position.y
                entity_count = entity_count + 1
            end
        end
    end

    -- Check if we found any entities
    if entity_count == 0 then
        return nil
    end

    -- Calculate average position (centroid)
    local centroid = {
        x = total_x / entity_count,
        y = total_y / entity_count
    }

    -- Calculate additional statistics
    local stats = {
        centroid = centroid,
        entity_count = entity_count,
        -- Find the bounds of the factory
        bounds = calculate_factory_bounds(force)
    }

    return stats
end