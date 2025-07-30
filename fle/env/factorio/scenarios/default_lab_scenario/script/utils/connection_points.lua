-- This is primarily used to get the connection points of entities for the purpose of blocking them during pathing.
-- This is to prevent bad cases where connections are blocked by belts / pipes etc.

-- Function to get connection points for storage tanks based on their direction
global.utils.get_storage_tank_connection_points = function(entity)
    local x, y = entity.position.x, entity.position.y
    local connection_points = {}

    -- Storage tanks have two possible orientations:
    -- 1. TopRight/BottomLeft connections (direction = 0 or direction = 2)
    -- 2. TopLeft/BottomRight connections (direction = 1 or direction = 3)

    -- Note: entity.direction is in Factorio's 8-way direction system (0-7)
    -- We need to handle both orientations (0/2 and 1/3)
    if entity.direction == 1 or entity.direction == 2 then
        -- TopRight/BottomLeft connections
        table.insert(connection_points, {x = x + 1, y = y - 2})  -- Top right - Top
        table.insert(connection_points, {x = x + 2, y = y - 1})  -- Top right - Right

        table.insert(connection_points, {x = x - 1, y = y + 2})  -- Bottom left - Bottom
        table.insert(connection_points, {x = x - 2, y = y + 1})  -- Bottom left - Left
    else
        -- TopLeft/BottomRight connections
        table.insert(connection_points, {x = x - 1, y = y - 2})  -- Top left - Top
        table.insert(connection_points, {x = x - 2, y = y - 1})  -- Top left - Left

        table.insert(connection_points, {x = x + 1, y = y + 2})  -- Bottom right - Bottom
        table.insert(connection_points, {x = x + 2, y = y + 1})  -- Bottom right - Right

    end

    return connection_points
end

global.utils.get_chemical_plant_connection_points = function(plant)
    local positions = {}
    local x, y = plant.position.x, plant.position.y

    if plant.direction == defines.direction.north then
        -- Input pipes
        table.insert(positions, {x = x - 1, y = y + 1.5})
        table.insert(positions, {x = x + 1, y = y + 1.5})
        -- Output pipes
        table.insert(positions, {x = x - 1, y = y - 1.5})
        table.insert(positions, {x = x + 1, y = y - 1.5})
    elseif plant.direction == defines.direction.south then
        -- Input pipes
        table.insert(positions, {x = x - 1, y = y - 1.5})
        table.insert(positions, {x = x + 1, y = y - 1.5})
        -- Output pipes
        table.insert(positions, {x = x - 1, y = y + 1.5})
        table.insert(positions, {x = x + 1, y = y + 1.5})
    elseif plant.direction == defines.direction.east then
        -- Input pipes
        table.insert(positions, {x = x - 1.5, y = y - 1})
        table.insert(positions, {x = x - 1.5, y = y + 1})
        -- Output pipes
        table.insert(positions, {x = x + 1.5, y = y - 1})
        table.insert(positions, {x = x + 1.5, y = y + 1})
    elseif plant.direction == defines.direction.west then
        -- Input pipes
        table.insert(positions, {x = x + 1.5, y = y - 1})
        table.insert(positions, {x = x + 1.5, y = y + 1})
        -- Output pipes
        table.insert(positions, {x = x - 1.5, y = y - 1})
        table.insert(positions, {x = x - 1.5, y = y + 1})
    end

    return positions
end


global.utils.get_generator_connection_positions = function(entity)
    local x, y = entity.position.x, entity.position.y
    local orientation = entity.orientation
    local entity_prototype = game.entity_prototypes[entity.name]
    local dx, dy = 0, 0
    local offsetx, offsety = 0, 0
    if orientation == 0 or orientation == defines.direction.north then
        dx, dy = 0, -1
        --offsetx, offsety = 0, 0
    elseif orientation == 0.25 or orientation == defines.direction.east then
        dx, dy = 1, 0
        --offsetx, offsety = -0.5, 0
    elseif orientation == 0.5 or orientation == defines.direction.south then
        dx, dy = 0, -1
        --offsetx, offsety = 0, -0.5
    elseif orientation == 0.75 or orientation == defines.direction.west then
        dx, dy = 1, 0
        --offsetx, offsety = 0, 0
    else
        -- Log detailed information about the unexpected orientation
        local orientation_info = string.format(
            "Numeric value: %s, Type: %s, Defines values: N=%s, E=%s, S=%s, W=%s",
            tostring(orientation),
            type(orientation),
            tostring(defines.direction.north),
            tostring(defines.direction.east),
            tostring(defines.direction.south),
            tostring(defines.direction.west)
        )
        error(string.format(
            "Unexpected orientation for entity: %s at position: %s. Orientation info: %s",
            entity.name,
            serpent.line(entity.position),
            orientation_info
        ))
    end
    local height = entity_prototype.tile_height/2
    local pipe_positions = {
        {x = x + (height*dx) + offsetx, y = y + (height*dy) + offsety},
        {x = x - (height*dx) + offsetx, y = y - (height*dy) + offsety}
    }

    return pipe_positions
end

global.utils.get_pumpjack_connection_points = function(entity)
    local x, y = entity.position.x, entity.position.y
    local orientation = entity.orientation

    local dx, dy
    if orientation == 0 or orientation == defines.direction.north then
        dx, dy = 1, -2
    elseif orientation == 0.25 or orientation == defines.direction.east then
        dx, dy = 2, -1
    elseif orientation == 0.5 or orientation == defines.direction.south then
        dx, dy = -1, 2
    elseif orientation == 0.75 or orientation == defines.direction.west then
        dx, dy = -2, 1
    end

    local pipe_position = {{x = x + dx, y = y + dy}}

    return pipe_position
end

global.utils.get_boiler_connection_points = function(entity)
    local x, y = entity.position.x, entity.position.y
    local orientation = entity.orientation * 8

    local dx, dy = 0, 0
    if orientation == defines.direction.north then
        dx, dy = 1.5, 0.5
        local pipe_positions = {
            --water_inputs = water_inputs,
            --steam_output = {x = x, y = y - 1*dy}
            {x = x + 1*dx, y = y + 1*dy},
            {x = x - 1*dx, y = y + 1*dy},
            {x = x, y = y - 1*dy}
        }
    
        return pipe_positions
    elseif orientation == defines.direction.south then
        dx, dy = -1.5, -0.5
        local pipe_positions = {
            --water_inputs = water_inputs,
            --steam_output = {x = x, y = y - 1*dy}
            {x = x + 1*dx, y = y + 1*dy},
            {x = x - 1*dx, y = y + 1*dy},
            {x = x, y = y - 1*dy}
        }
        return pipe_positions
    elseif orientation == defines.direction.east then
        dx, dy = 0.5, 1.5
        local pipe_positions = {
            --water_inputs = water_inputs,
            --steam_output = {x = x, y = y - 1*dy}
            {x = x + 1*dx, y = y + 1*dy},
            {x = x + 1*dx, y = y - 1*dy},
            {x = x - 1*dx, y = y}
        }
        return pipe_positions
    elseif orientation == defines.direction.west then
        dx, dy = -0.5, -1.5
        local pipe_positions = {
            --water_inputs = water_inputs,
            --steam_output = {x = x, y = y - 1*dy}
            {x = x + 1*dx, y = y + 1*dy},
            {x = x + 1*dx, y = y - 1*dy},
            {x = x - 1*dx, y = y}
        }
    
        return pipe_positions
    end
    --local water_inputs = {}
    --water_inputs[1] = {x = x + 1*dx, y = y + 1*dy}
    --water_inputs[2] = {x = x - 1*dx, y = y - 1*dy}

    --local pipe_positions = {
    --    --water_inputs = water_inputs,
    --    --steam_output = {x = x, y = y - 1*dy}
    --    {x = x + 1*dx, y = y + 1*dy},
    --    {x = x - 1*dx, y = y + 1*dy},
    --    {x = x, y = y - 1*dy}
    --}
    --return pipe_positions
end

global.utils.get_offshore_pump_connection_points = function(entity)
    local x, y = entity.position.x, entity.position.y
    local orientation = entity.orientation * 8

    local dx, dy
    if orientation == defines.direction.north then
        dx, dy = 0, 1
    elseif orientation == defines.direction.south then
        dx, dy = 0, -1
    elseif orientation == defines.direction.east then
        dx, dy = -1, 0
    elseif orientation == defines.direction.west then
        dx, dy = 1, 0
    end

    if dy == nil then
        return { {x = x, y = y - 1} }
    end

    return { {x = x + dx, y = y + dy} }
end

global.utils.get_refinery_connection_points = function(refinery)
    -- Block the middle input point also
    local positions = {}
    local x, y = refinery.position.x, refinery.position.y

    if refinery.direction == defines.direction.north then
        -- Crude oil input
        table.insert(positions, {x = x+1, y = y + 3})
        --table.insert(positions, {x = x+1, y = y + 4}) -- additional clearance
        table.insert(positions, {x = x-1, y = y + 3})
        --table.insert(positions, {x = x-1, y = y + 4}) -- additional clearance

        table.insert(positions, {x = x, y = y + 3})

        -- Outputs (petroleum, light oil, heavy oil)
        table.insert(positions, {x = x - 2, y = y - 3})
        --table.insert(positions, {x = x - 2, y = y - 4}) -- additional clearance

        table.insert(positions, {x = x - 1, y = y - 3})

        table.insert(positions, {x = x, y = y - 3})
        --table.insert(positions, {x = x, y = y - 4}) -- additional clearance

        table.insert(positions, {x = x + 1, y = y - 3})

        table.insert(positions, {x = x + 2, y = y - 3})
        --table.insert(positions, {x = x + 2, y = y - 4}) -- additional clearance
    elseif refinery.direction == defines.direction.south then
        -- Crude oil input
        table.insert(positions, {x = x+1, y = y - 3})
        --table.insert(positions, {x = x+1, y = y - 4}) -- additional clearance

        table.insert(positions, {x = x, y = y - 3})
        table.insert(positions, {x = x-1, y = y - 3})
        --table.insert(positions, {x = x-1, y = y - 4}) -- additional clearance

        -- Outputs
        table.insert(positions, {x = x - 2, y = y + 3})
        --table.insert(positions, {x = x - 2, y = y + 4}) -- additional clearance

        table.insert(positions, {x = x - 1, y = y + 3})
        table.insert(positions, {x = x, y = y + 3})
        --table.insert(positions, {x = x, y = y + 4}) -- additional clearance
        table.insert(positions, {x = x + 2, y = y + 3})
        --table.insert(positions, {x = x + 2, y = y + 4}) -- additional clearance
        table.insert(positions, {x = x + 1, y = y + 3})
    elseif refinery.direction == defines.direction.east then
        -- Crude oil input
        table.insert(positions, {x = x - 3, y = y+1})
        table.insert(positions, {x = x - 4, y = y+1})
        table.insert(positions, {x = x - 3, y = y})
        table.insert(positions, {x = x - 3, y = y-1})
        table.insert(positions, {x = x - 4, y = y-1})
        -- Outputs
        table.insert(positions, {x = x + 3, y = y - 2})
        table.insert(positions, {x = x + 3, y = y - 1})
        table.insert(positions, {x = x + 3, y = y})
        table.insert(positions, {x = x + 3, y = y + 1})
        table.insert(positions, {x = x + 3, y = y + 2})
    elseif refinery.direction == defines.direction.west then
        -- Crude oil input
        table.insert(positions, {x = x + 3, y = y+1})
        table.insert(positions, {x = x + 3, y = y})
        table.insert(positions, {x = x + 3, y = y-1})
        -- Outputs
        table.insert(positions, {x = x - 3, y = y - 2})
        table.insert(positions, {x = x - 3, y = y - 1})
        table.insert(positions, {x = x - 3, y = y})
        table.insert(positions, {x = x - 3, y = y + 1})
        table.insert(positions, {x = x - 3, y = y + 2})
    end

    return positions
end