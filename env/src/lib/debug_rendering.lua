-- debug_rendering.lua
-- This file provides a wrapper around the Factorio rendering API that respects the debug flag

-- Initialize global debug flags if they don't exist
if global.debug == nil then
    global.debug = {
        rendering = false -- Flag to toggle debug rendering of polygons and shapes
    }
end

-- Create a debug rendering namespace
global.debug_rendering = {}

-- Wrapper functions for rendering that check the debug flag
function global.debug_rendering.draw_circle(params)
    if global.debug.rendering then
        return rendering.draw_circle(params)
    end
    return nil
end

function global.debug_rendering.draw_rectangle(params)
    if global.debug.rendering then
        return rendering.draw_rectangle(params)
    end
    return nil
end

function global.debug_rendering.draw_line(params)
    if global.debug.rendering then
        return rendering.draw_line(params)
    end
    return nil
end

function global.debug_rendering.draw_polygon(params)
    if global.debug.rendering then
        return rendering.draw_polygon(params)
    end
    return nil
end

function global.debug_rendering.draw_text(params)
    if global.debug.rendering then
        return rendering.draw_text(params)
    end
    return nil
end

function global.debug_rendering.draw_sprite(params)
    if global.debug.rendering then
        return rendering.draw_sprite(params)
    end
    return nil
end

function global.debug_rendering.clear(...)
    if ... then
        return rendering.clear(...)
    else
        return rendering.clear()
    end
end

-- Create the toggle_debug function
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
            -- Clear all existing rendering entities when disabled
            rendering.clear()
            return "\"Debug rendering disabled\""
        else
            return "\"Current rendering debug status: " .. tostring(global.debug.rendering) .. "\""
        end
    else
        return "\"Unknown debug type: " .. debug_type .. "\""
    end
end