global.paths = global.paths or {}

global.actions.request_path = function(player_index, start_x, start_y, goal_x, goal_y, radius, allow_paths_through_own_entities)
    local player = game.get_player(player_index)
    if not player then return nil end

    local surface = player.surface
    local force = player.force

    local goal_position = player.surface.find_non_colliding_position(
                "iron-chest", -- TODO: using iron chest bbox so request_path doesn't fail standing near objects using the larger bbox
            {y = goal_y, x = goal_x},
                10,
                0.5,
                true
    )
    --local start_position = player.surface.find_non_colliding_position(
    --            "iron-chest", -- TODO: using iron chest bbox so request_path doesn't fail standing near objects using the larger bbox
    --            {y = start_y, x = start_x},
    --            10,
    --            0.5,
    --            true
    --)
    local start_position = {y = start_y, x = start_x}
    --create_beam_point_with_direction(player, 1, start_position)
    --create_beam_point_with_direction(player, 1, goal_position)
    --
    --create_beam_point_with_direction(player, 2, {y = start_y, x = start_x, })
    --create_beam_point_with_direction(player, 2, {y = goal_y, x = goal_x})

    local path_request = {
        bounding_box = {{-0.49, -0.49}, {0.49, 0.49}}, -- Assuming a 1x1 entity size
        collision_mask = { "player-layer",
                            "train-layer",
                            "consider-tile-transitions",
                            "water-tile",
                            "object-layer"
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

    -- Store the request_id and player_index for later use in the event handler
    if not global.path_requests then
        global.path_requests = {}
    end
    if not global.paths then
        global.paths = {}
    end

    global.path_requests[request_id] = player_index

    return request_id
end

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
        player.print("Path found with " .. #event.path .. " waypoints")
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
