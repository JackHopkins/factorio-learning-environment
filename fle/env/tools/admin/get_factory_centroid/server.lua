-- Initialize global camera tracking variables in your script's initialization
-- Put this in your script's on_init or when you initialize your global table
function initialize_camera_tracking(initial_position)
    initial_position = initial_position or {x = 0, y = 0}

    global.camera = global.camera or {}
    global.camera.position = global.camera.position or {x = initial_position.x, y = initial_position.y}
    global.camera.velocity = global.camera.velocity or {x = 0, y = 0}
    global.camera.target = global.camera.target or {x = initial_position.x, y = initial_position.y}
    global.camera.zoom = global.camera.zoom or 1
    global.camera.target_zoom = global.camera.target_zoom or 1

    -- Smoothing coefficients (adjust these values to change camera behavior)
    global.camera.position_smoothing = 0.05  -- How quickly to move toward target (0-1)
    global.camera.zoom_smoothing = 0.1     -- How quickly to zoom toward target (0-1)
    global.camera.velocity_damping = 0.6   -- How quickly velocity decays (0-1)

    -- Maximum velocity to prevent overshooting
    global.camera.max_velocity = 3.0
end

-- Helper function to calculate factory bounds (unchanged)
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

-- Updated function to get factory centroid and update camera smoothly
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
    local centroid = {x=0, y=0}
    -- Check if we found any entities
    if entity_count > 0 then
        -- Calculate average position (centroid)
        centroid = {
            x = total_x / entity_count,
            y = total_y / entity_count
        }
    end

    -- Calculate bounds of the factory
    local bounds = calculate_factory_bounds(force)

    -- Initialize camera tracking if it hasn't been initialized
    if not global.camera then
        initialize_camera_tracking(centroid)
        -- Set initial camera position to centroid
        --global.camera.position = {x = centroid.x, y = centroid.y}
        --global.camera.target = {x = centroid.x, y = centroid.y}
    end

    -- Update camera target
    global.camera.target.x = centroid.x
    global.camera.target.y = centroid.y

    -- Calculate appropriate zoom based on factory size
    if bounds then
        -- Calculate the diagonal size of the factory
        local diagonal = math.sqrt(bounds.width^2 + bounds.height^2)
        -- Determine a good zoom level based on factory size
        -- Lower values = zoomed out more
        global.camera.target_zoom = math.max(0.15, math.min(0.75, 35 / diagonal))
    end

    -- Update camera position with smooth interpolation
    update_camera_position()

    -- Calculate additional statistics
    local stats = {
        centroid = centroid,
        raw_centroid = centroid,
        entity_count = entity_count,
        bounds = bounds,
        camera = {
            position = global.camera.position,
            zoom = global.camera.zoom
        }
    }

    return stats
end

-- Function to update camera position with physics-based smoothing
function update_camera_position()
    -- Calculate delta between current position and target
    local dx = global.camera.target.x - global.camera.position.x
    local dy = global.camera.target.y - global.camera.position.y

    -- Apply acceleration based on distance to target
    global.camera.velocity.x = global.camera.velocity.x + dx * global.camera.position_smoothing
    global.camera.velocity.y = global.camera.velocity.y + dy * global.camera.position_smoothing

    -- Apply velocity damping
    global.camera.velocity.x = global.camera.velocity.x * global.camera.velocity_damping
    global.camera.velocity.y = global.camera.velocity.y * global.camera.velocity_damping

    -- Clamp velocity to maximum
    local velocity_magnitude = math.sqrt(global.camera.velocity.x^2 + global.camera.velocity.y^2)
    if velocity_magnitude > global.camera.max_velocity then
        local factor = global.camera.max_velocity / velocity_magnitude
        global.camera.velocity.x = global.camera.velocity.x * factor
        global.camera.velocity.y = global.camera.velocity.y * factor
    end

    -- Update position based on velocity
    global.camera.position.x = global.camera.position.x + global.camera.velocity.x
    global.camera.position.y = global.camera.position.y + global.camera.velocity.y

    -- Smoothly interpolate zoom
    local dz = global.camera.target_zoom - global.camera.zoom
    global.camera.zoom = global.camera.zoom + dz * global.camera.zoom_smoothing
end
