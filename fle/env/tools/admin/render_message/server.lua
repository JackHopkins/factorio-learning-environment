global.actions.render_message = function(player_index, message)
    -- Get color based on player index
    local color = {r = 1, g = 1, b = 1} -- Default white
    if player_index == 1 then
        color = {r = 0.6, g = 1, b = 0.6} -- Light green
        message = "Agent 1: " .. message
    elseif player_index == 2 then
        color = {r = 0.6, g = 0.6, b = 1} -- Light blue
        message = "Agent 2: " .. message
    elseif player_index == 3 then
        color = {r = 1, g = 0.6, b = 0.6} -- Light red
        message = "Agent 3: " .. message
    end

    -- Print message with color
    game.print(message, color)
    return true
end
