-- Function to get the path as a Lua table
global.actions.get_path = function(request_id)
    local request_data = global.path_requests[request_id]
    if not request_data then
        return {status = "invalid_request"}
    end

    if request_data == "pending" then
        return {status = "pending"}
    end

    local path = global.paths[request_id]
    if not path then
        return {status = "not_found"}
    end

    if path == "busy" then
        return {status = "busy"}
    elseif path == "not_found" then
        return {status = "not_found"}
    else
        local waypoints = {}
        for _, waypoint in ipairs(path) do
            table.insert(waypoints, {
                x = waypoint.position.x,
                y = waypoint.position.y
            })
        end
        return {
            status = "success",
            waypoints = waypoints
        }
    end
end