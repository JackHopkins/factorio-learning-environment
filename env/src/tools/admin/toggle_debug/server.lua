global.actions.toggle_debug = function(player_index, debug_type, enable)
    local player = game.get_player(player_index)
    
    -- Initialize debug table if it doesn't exist
    if global.debug == nil then
        global.debug = {}
    end
    
    if debug_type == "rendering" then
        if enable == "true" then
            global.debug.rendering = true
            return "\"Debug rendering enabled\""
        elseif enable == "false" then
            global.debug.rendering = false
            return "\"Debug rendering disabled\""
        else
            return "\"Current rendering debug status: " .. tostring(global.debug.rendering) .. "\""
        end
    else
        return "\"Unknown debug type: " .. debug_type .. "\""
    end
end