-- Store created entities globally
if not global.clearance_entities then
    global.clearance_entities = {}
end
local epsilon = 1.5


local function get_boiler_connection_positions(boiler)
    local positions = {}
    local x, y = boiler.position.x, boiler.position.y

    if boiler.direction == defines.direction.north then
        -- Water input points
        table.insert(positions, {x = x - 2, y = y + 0.5})
        table.insert(positions, {x = x + 2, y = y + 0.5})
        -- Steam output point
        table.insert(positions, {x = x, y = y - 1.5})
    elseif boiler.direction == defines.direction.south then
        -- Water input points
        table.insert(positions, {x = x - 2, y = y - 0.5})
        table.insert(positions, {x = x + 2, y = y - 0.5})
        -- Steam output point
        table.insert(positions, {x = x, y = y + 1.5})
    elseif boiler.direction == defines.direction.east then
        -- Water input points
        table.insert(positions, {x = x - 0.5, y = y - 2})
        table.insert(positions, {x = x - 0.5, y = y + 2})
        -- Steam output point
        table.insert(positions, {x = x + 1.5, y = y})
    elseif boiler.direction == defines.direction.west then
        -- Water input points
        table.insert(positions, {x = x + 0.5, y = y - 2})
        table.insert(positions, {x = x + 0.5, y = y + 2})
        -- Steam output point
        table.insert(positions, {x = x - 1.5, y = y})
    end

    return positions
end

local function add_clearance_entities(surface, force, region, start_pos, end_pos)
    local created_entities = {}
    local all_positions = {}

    local epsilon = 1 --0.707*2  -- Small value for floating point comparison
    -- Helper function to check if a position is start or end
    local function is_excluded_position(pos)
        return (math.abs(pos.x - start_pos.x) < epsilon and math.abs(pos.y - start_pos.y) < epsilon) or
               (math.abs(pos.x - end_pos.x) < epsilon and math.abs(pos.y - end_pos.y) < epsilon)
    end

    -- Find all pipes and boilers in the region
    local pipes = surface.find_entities_filtered{
        name = "pipe",
        force = force,
        area = region
    }

    local boilers = surface.find_entities_filtered{
        name = "boiler",
        force = force,
        area = region
    }

    -- Find all mining drills in the region
    local drills = surface.find_entities_filtered{
        type = "mining-drill", -- Add other drill types if needed
        force = force,
        area = region
    }

    -- Collect all positions for pipes
    for _, pipe in pairs(pipes) do
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

    rendering.draw_circle{width = 1, color = {r = 1, g = 0, b = 0}, surface = surface, radius = 0.5, filled = false, target = start_pos, time_to_live = 60000}
    rendering.draw_circle{width = 1, color = {r = 0, g = 1, b = 0}, surface = surface, radius = 0.5, filled = false, target = end_pos, time_to_live = 60000}

    -- Collect all positions for boilers
    for _, boiler in pairs(boilers) do
        local boiler_positions = get_boiler_connection_positions(boiler)
        for _, pos in pairs(boiler_positions) do
            local is_start = math.abs(pos.x - start_pos.x) < epsilon and math.abs(pos.y - start_pos.y) < epsilon
            local is_end = math.abs(pos.x - end_pos.x) < epsilon and math.abs(pos.y - end_pos.y) < epsilon
            if not is_start and not is_end then
                table.insert(all_positions, pos)
            end
        end
    end

    -- Collect all positions for mining drills
    for _, drill in pairs(drills) do
        local drop_pos = {x=math.round(drill.drop_position.x*2)/2, y=math.round(drill.drop_position.y*2)/2}
        local is_start = math.abs(drop_pos.x - start_pos.x) < epsilon and math.abs(drop_pos.y - start_pos.y) < epsilon
        local is_end = math.abs(drop_pos.x - end_pos.x) < epsilon and math.abs(drop_pos.y - end_pos.y) < epsilon
        if not is_start and not is_end then
            table.insert(all_positions, drop_pos)
        end
    end

    -- Create entities at filtered positions
    for _, pos in pairs(all_positions) do
        rendering.draw_circle{width = 1, color = {r = 0, g = 1, b = 1}, surface = surface, radius = 0.33, filled = false, target = pos, time_to_live = 60000}

        local entity = surface.create_entity{
            name = "simple-entity-with-owner",
            position = pos,
            force = force,
            graphics_variation = 255,
            render_player_index = nil,
            raise_built = false,
            --render_to_forces = {"enemy"}
        }
        if entity then
            entity.destructible = false
            entity.graphics_variation = 255
            --entity.render_to_forces = {"enemy"}
            entity.color = {r = 0, g = 0, b = 0, a = 0}
            table.insert(created_entities, entity)
        end
    end

    return created_entities
end

global.actions.extend_collision_boxes = function(player_index, start_x, start_y, goal_x, goal_y)
    local player = game.players[player_index]
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