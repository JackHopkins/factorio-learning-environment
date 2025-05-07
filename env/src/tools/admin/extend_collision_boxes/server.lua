-- Helper function for pumpjack fluid positions
--local function get_pumpjack_connection_positions(pumpjack)
--    local positions = {}
--    local x, y = pumpjack.position.x, pumpjack.position.y
--
--    -- Pumpjack output position changes based on direction
--    if pumpjack.direction == defines.direction.north then
--        table.insert(positions, {x = x, y = y - 2})
--    elseif pumpjack.direction == defines.direction.south then
--        table.insert(positions, {x = x, y = y + 2})
--    elseif pumpjack.direction == defines.direction.east then
--        table.insert(positions, {x = x + 2, y = y})
--    elseif pumpjack.direction == defines.direction.west then
--        table.insert(positions, {x = x - 2, y = y})
--    end
--
--    return positions
--end

---- Helper function for boiler fluid positions
--local function get_boiler_connection_positions(boiler)
--    local positions = {}
--    local x, y = boiler.position.x, boiler.position.y
--
--    if boiler.direction == defines.direction.north then
--        -- Water input points
--        table.insert(positions, {x = x - 2, y = y + 0.5})
--        table.insert(positions, {x = x + 2, y = y + 0.5})
--        -- Steam output point
--        table.insert(positions, {x = x, y = y - 1.5})
--    elseif boiler.direction == defines.direction.south then
--        -- Water input points
--        table.insert(positions, {x = x - 2, y = y - 0.5})
--        table.insert(positions, {x = x + 2, y = y - 0.5})
--        -- Steam output point
--        table.insert(positions, {x = x, y = y + 1.5})
--    elseif boiler.direction == defines.direction.east then
--        -- Water input points
--        table.insert(positions, {x = x - 0.5, y = y - 2})
--        table.insert(positions, {x = x - 0.5, y = y + 2})
--        -- Steam output point
--        table.insert(positions, {x = x + 1.5, y = y})
--    elseif boiler.direction == defines.direction.west then
--        -- Water input points
--        table.insert(positions, {x = x + 0.5, y = y - 2})
--        table.insert(positions, {x = x + 0.5, y = y + 2})
--        -- Steam output point
--        table.insert(positions, {x = x - 1.5, y = y})
--    end
--
--    return positions
--end



local function add_clearance_entities(surface, force, region, start_pos, end_pos)
    local created_entities = {}
    local all_positions = {}

    local epsilon = 0.707 -- Small value for floating point comparison

    -- Helper function to check if a position is start or end
    local function is_excluded_position(pos)
        return (math.abs(pos.x - start_pos.x) < epsilon and math.abs(pos.y - start_pos.y) < epsilon) or
               (math.abs(pos.x - end_pos.x) < epsilon and math.abs(pos.y - end_pos.y) < epsilon)
    end

    -- Find all relevant entities in the region
    local entities = {
        pipes = surface.find_entities_filtered{name = "pipe", force = force, area = region},
        boilers = surface.find_entities_filtered{name = "boiler", force = force, area = region},
        drills = surface.find_entities_filtered{type = "mining-drill", force = force, area = region},
        pumpjacks = surface.find_entities_filtered{name = "pumpjack", force = force, area = region},
        refineries = surface.find_entities_filtered{name = "oil-refinery", force = force, area = region},
        chemical_plants = surface.find_entities_filtered{name = "chemical-plant", force = force, area = region},
        storage_tanks = surface.find_entities_filtered{name = "storage-tank", force = force, area = region}
    }


    -- Draw debug circles for start and end positions
    rendering.draw_circle{only_in_alt_mode=true, width = 1, color = {r = 1, g = 0, b = 0}, surface = surface, radius = 0.5, filled = false, target = start_pos, time_to_live = 60000}
    rendering.draw_circle{only_in_alt_mode=true, width = 1, color = {r = 0, g = 1, b = 0}, surface = surface, radius = 0.5, filled = false, target = end_pos, time_to_live = 60000}

    -- Collect positions from pipes
    for _, pipe in pairs(entities.pipes) do
        local pipe_positions = {
            {x = pipe.position.x + 1, y = pipe.position.y},
            {x = pipe.position.x - 1, y = pipe.position.y},
            {x = pipe.position.x, y = pipe.position.y + 1},
            {x = pipe.position.x, y = pipe.position.y - 1}
        }
        for _, pos in pairs(pipe_positions) do
            if not is_excluded_position(pos) then
                table.insert(all_positions, pos)
            end
        end
    end

    -- Collect positions from boilers
    for _, boiler in pairs(entities.boilers) do
        for _, pos in pairs(global.utils.get_boiler_connection_points(boiler)) do
            if not is_excluded_position(pos) then
                table.insert(all_positions, pos)
            end
        end
    end

    -- Collect positions from pumpjacks
    for _, pumpjack in pairs(entities.pumpjacks) do
        for _, pos in pairs(global.utils.get_pumpjack_connection_points(pumpjack)) do
            if not is_excluded_position(pos) then
                table.insert(all_positions, pos)
            end
        end
    end

    -- Collect positions from refineries
    for _, refinery in pairs(entities.refineries) do
        for _, pos in pairs(global.utils.get_refinery_connection_points(refinery)) do
            if not is_excluded_position(pos) then
                table.insert(all_positions, pos)
            end
        end
    end

    -- Collect positions from chemical plants
    for _, plant in pairs(entities.chemical_plants) do
        for _, pos in pairs(global.utils.get_chemical_plant_connection_points(plant)) do
            if not is_excluded_position(pos) then
                table.insert(all_positions, pos)
            end
        end
    end

     -- Collect positions from storage tanks
    for _, tank in pairs(entities.storage_tanks) do
        for _, pos in pairs(global.utils.get_storage_tank_connection_points(tank)) do
            if not is_excluded_position(pos) then
                table.insert(all_positions, pos)
            end
        end
    end
    -- game.print("There are "..#entities.drills)
    for _, drill in pairs(entities.drills) do
        -- game.print(serpent.block(drill))
    end
    -- Collect positions from mining drills
    for _, drill in pairs(entities.drills) do
        -- game.print("Drop position ".. serpent.line(drill.drop_position))
        local drop_pos = drill.drop_position--{x=math.round(drill.drop_position.x*2)/2, y=math.round(drill.drop_position.y*2)/2}
        if not is_excluded_position(drop_pos) then
            table.insert(all_positions, drop_pos)
        end
    end

    -- Create entities at filtered positions
    for _, pos in pairs(all_positions) do
        -- Draw debug circles for connection points
        rendering.draw_circle{only_in_alt_mode=true, width = 1, color = {r = 0, g = 1, b = 1}, surface = surface, radius = 0.33, filled = false, target = pos, time_to_live = 60000}

        local entity = surface.create_entity{
            name = "simple-entity-with-owner",
            position = pos,
            force = force,
            graphics_variation = 255,
            render_player_index = 65535,
            raise_built = false
        }
        if entity then
            entity.destructible = false
            entity.graphics_variation = 255
            entity.color = {r = 0, g = 0, b = 0, a = 0}
            table.insert(created_entities, entity)
        end
    end

    return created_entities
end

global.actions.extend_collision_boxes = function(player_index, start_x, start_y, goal_x, goal_y)
    local player = global.agent_characters[player_index]
    local start_pos = {x=start_x, y=start_y}
    local end_pos = {x=goal_x, y=goal_y}
    -- Define region for entity checking (add some margin around start/goal)
    local region = {
        left_top = {
            x = math.min(start_x, goal_x) - 20,
            y = math.min(start_y, goal_y) - 20
        },
        right_bottom = {
            x = math.max(start_x, goal_x) + 20,
            y = math.max(start_y, goal_y) + 20
        }
    }

    -- Add buffer entities around all pipes, boilers, and drill drop positions
    local created = add_clearance_entities(player.surface, player.force, region, start_pos, end_pos)
    global.clearance_entities[player_index] = created

    return true
end