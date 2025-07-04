-- Function to get the path as a JSON object
global.actions.get_path = function(request_id)
    local request_data = global.path_requests[request_id]
    if not request_data then
        return game.table_to_json({status = "\"invalid_request\""})
    end

    if request_data == "pending" then
        return game.table_to_json({status = "\"pending\""})
    end

    local path = global.paths[request_id]
    if not path then
        return game.table_to_json({status = "\"not_found\""})
    end

    if path == "busy" then
        return game.table_to_json({status = "\"busy\""})
    elseif path == "not_found" then
        return game.table_to_json({status = "\"not_found\""})
    else
        local waypoints = {}
        for _, waypoint in ipairs(path) do
            table.insert(waypoints, {
                x = waypoint.position.x,
                y = waypoint.position.y
            })
        end
        -- create a beam bounding box at the start and end of the path
        local start = path[1].position
        local finish = path[#path].position
        --create_beam_bounding_box(player, surface, 1, {x = start.x - 0.5, y = start.y - 0.5}, {x = finish.x + 0.5, y = finish.y + 0.5})
        return game.table_to_json({
            status = "\"success\"",
            waypoints = waypoints
        })
    end
end