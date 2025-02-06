-- Store created entities globally
if not global.clearance_entities then
    global.clearance_entities = {}
end

global.actions.request_path = function(player_index, start_x, start_y, goal_x, goal_y, radius, allow_paths_through_own_entities, entity_size)
    local player = game.get_player(player_index)
    if not player then return nil end
    local size = entity_size/2 - 0.01

    local surface = player.surface
    local force = player.force

    -- Define region for pipe checking (add some margin around start/goal)
    local region = {
        left_top = {
            x = math.min(start_x, goal_x) - 10,
            y = math.min(start_y, goal_y) - 10
        },
        right_bottom = {
            x = math.max(start_x, goal_x) + 10,
            y = math.max(start_y, goal_y) + 10
        }
    }

    -- Add temporary collision entities
    --local clearance_entities = add_pipe_clearance_entities(surface, force, region)

    local clearance_entities = {}--add_pipe_clearance_entities(surface, force, region)

    local goal_position = player.surface.find_non_colliding_position(
        "iron-chest",
        {y = goal_y, x = goal_x},
        10,
        0.5,
        true
    )
    local start_position = {y = start_y, x = start_x}

    local path_request = {
        bounding_box = {{-size, -size}, {size, size}},
        collision_mask = { 
            "player-layer",
            "train-layer",
            "consider-tile-transitions",
            "water-tile",
            "object-layer",
            "transport-belt-layer",
            "water-tile"
        },
        start = start_position,
        goal = goal_position,
        force = force,
        radius = radius or 0,
        entity_to_ignore = player.character,
        can_open_gates = true,
        path_resolution_modifier = 0,
        pathfind_flags = {
            cache = false,
            no_break = true,
            prefer_straight_paths = true,
            allow_paths_through_own_entities = allow_paths_through_own_entities
        }
    }

    local request_id = surface.request_path(path_request)

    global.clearance_entities[request_id] = clearance_entities

    -- Clean up temporary entities
    --for _, entity in pairs(clearance_entities) do
    --    if entity.valid then
    --        entity.destroy()
    --    end
    --end

    if not global.path_requests then
        global.path_requests = {}
    end
    if not global.paths then
        global.paths = {}
    end

    global.path_requests[request_id] = player_index

    return request_id
end

-- Modify the pathfinding finished handler to clean up entities
--script.on_event(defines.events.on_script_path_request_finished, function(event)
--    -- Clean up clearance entities
--    if global.clearance_entities[event.id] then
--        for _, entity in pairs(global.clearance_entities[event.id]) do
--            if entity.valid then
--                entity.destroy()
--            end
--        end
--        global.clearance_entities[event.id] = nil
--    end
--end)

script.on_event(defines.events.on_script_path_request_finished, function(event)
    local request_data = global.path_requests[event.id]
    if not request_data then
        log("No request data found for ID: " .. event.id)
        return
    end

    local player = game.get_player(request_data)
    if not player then
        log("Player not found for request ID: " .. event.id)
        return
    end

    if event.path then
        -- Path found successfully
        --player.print("Path found with " .. #event.path .. " waypoints")
        global.paths[event.id] = event.path
        log("Path found for request ID: " .. event.id)
    elseif event.try_again_later then
        player.print("Pathfinder is busy, try again later")
        global.paths[event.id] = "busy"
        log("Pathfinder busy for request ID: " .. event.id)
    else
        player.print("Path not found" .. serpent.block(event))
        global.paths[event.id] = "not_found"
        log("Path not found for request ID: " .. event.id)

    end
end)