-- Store created entities globally
if not global.clearance_entities then
    global.clearance_entities = {}
end

global.actions.request_path = function(player_index, start_x, start_y, goal_x, goal_y, radius, allow_paths_through_own_entities, entity_size)
    game.print("Starting request_path for player " .. player_index)
    
    -- Check player
    local player = global.agent_characters[player_index]
    if not player then 
        game.print("Error: Player " .. player_index .. " not found in global.agent_characters")
        return -1
    end
    game.print("Player found at position: " .. player.position.x .. "," .. player.position.y)
    
    -- Check surface
    local surface = player.surface
    if not surface then
        game.print("Error: Player has no valid surface")
        return -2
    end
    game.print("Surface is valid")
    
    -- Validate coordinates
    if not start_x or not start_y or not goal_x or not goal_y then
        game.print("Error: Invalid coordinates - start:(" .. (start_x or "nil") .. "," .. (start_y or "nil") .. ") goal:(" .. (goal_x or "nil") .. "," .. (goal_y or "nil") .. ")")
        return -3
    end
    game.print("Coordinates are valid")
    
    local size = entity_size/2 - 0.01
    local start_position = {x = start_x, y = start_y}
    local goal_position = {x = goal_x, y = goal_y}
    game.print("Start position: " .. start_position.x .. "," .. start_position.y)
    game.print("Goal position: " .. goal_position.x .. "," .. goal_position.y)
    
    -- Add debug prints for path request setup
    game.print("About to setup path request...")
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
        force = player.force,
        radius = radius or 0,
        entity_to_ignore = player,
        can_open_gates = true,
        path_resolution_modifier = 0,
        pathfind_flags = {
            allow_paths_through_own_entities = allow_paths_through_own_entities,
            cache = false,
            prefer_straight_paths = true,
            low_priority = false
        }
    }
    game.print("Path request setup complete")
    
    game.print("About to call surface.request_path...")
    local success, result = pcall(function()
        return surface.request_path(path_request)
    end)
    
    if not success then
        game.print("Error in request_path: " .. tostring(result))
        return -6
    end
    
    local request_id = result
    game.print("surface.request_path returned: " .. tostring(request_id))
    
    -- Initialize path_requests if needed
    if not global.path_requests then
        global.path_requests = {}
    end
    
    -- Store the request
    global.path_requests[request_id] = player_index
    game.print("Success: Path request registered with ID " .. request_id)
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
    game.print("Path request finished for ID: " .. event.id)
    
    if not request_data then
        game.print("Error: No request data found for ID: " .. event.id)
        return
    end

    local player = global.agent_characters[request_data]
    if not player then
        game.print("Error: Player not found for request ID: " .. event.id)
        return
    end

    if event.path then
        -- Path found successfully
        game.print("Success: Path found with " .. #event.path .. " waypoints")
        global.paths[event.id] = event.path
    elseif event.try_again_later then
        game.print("Error: Pathfinder is busy, try again later")
        global.paths[event.id] = "busy"
    else
        game.print("Error: Path not found. Event data: " .. serpent.block(event))
        global.paths[event.id] = "not_found"
    end
end)