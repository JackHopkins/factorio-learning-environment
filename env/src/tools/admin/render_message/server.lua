global.actions.render_message2 = function(player_index, message, duration)
    duration = duration or 300
    
    local agent = global.agent_characters[player_index]
    if not agent then
        return "Agent not found"
    end
    
    -- Draw background rectangle
    rendering.draw_rectangle{
        surface = agent.surface,
        left_top = {agent.position.x - 0.5, agent.position.y - 1.2},
        right_bottom = {agent.position.x + 0.5, agent.position.y - 0.8},
        color = {r = 0, g = 0, b = 0, a = 0.7},
        filled = true,
        time_to_live = duration
    }
    
    -- Draw text
    rendering.draw_text{
        surface = agent.surface,
        text = message,
        target = {agent.position.x, agent.position.y - 1},
        color = {r = 1, g = 1, b = 1, a = 1},
        alignment = "center",
        time_to_live = duration
    }
    
    return true
end

global.actions.render_message = function(player_index, message, duration)
    -- Get color based on player index
    local color = {r = 1, g = 1, b = 1} -- Default white
    if player_index == 1 then
        color = {r = 0.6, g = 1, b = 0.6} -- Light green
        message = "Player 1 -> 2: " .. message
    elseif player_index == 2 then
        color = {r = 0.6, g = 0.6, b = 1} -- Light blue
        message = "Player 2 -> 1: " .. message
    end

    -- Print message with color
    game.print(message, color)
    return true
end
