-- Initialize agent inboxes if they don't exist
if not global.agent_inbox then
    global.agent_inbox = {}
end

global.actions.send_message = function(player_index, message, recipient)
    -- Create message entry
    local message_entry = {
        sender = player_index,
        message = message,
        timestamp = game.tick,
        recipient = recipient
    }
    
    if recipient >= 0 then
        -- Send to specific recipient only
        if not global.agent_inbox[recipient] then
            global.agent_inbox[recipient] = {}
        end
        table.insert(global.agent_inbox[recipient], message_entry)
    else
        -- Send to all agents except sender
        for other_index, _ in pairs(global.agent_characters) do
            if other_index ~= player_index then
                if not global.agent_inbox[other_index] then
                    global.agent_inbox[other_index] = {}
                end
                table.insert(global.agent_inbox[other_index], message_entry)
            end
        end
    end
    
    return true
end