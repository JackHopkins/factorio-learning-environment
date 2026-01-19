-- Function to get the path as a JSON object
storage.actions.get_path = function(request_id)
    local request_data = storage.path_requests[request_id]
    if not request_data then
        return helpers.table_to_json({status = "invalid_request"})
    end

    -- Check if path has been computed yet
    local path = storage.paths[request_id]
    if not path then
        -- Request exists but path not yet computed - still pending
        return helpers.table_to_json({status = "pending"})
    end

    if path == "busy" then
        return helpers.table_to_json({status = "busy"})
    elseif path == "not_found" then
        return helpers.table_to_json({status = "not_found"})
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
        return helpers.table_to_json({
            status = "success",
            waypoints = waypoints
        })
    end
end