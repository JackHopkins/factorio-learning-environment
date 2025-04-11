-- Initialize agent inboxes if they don't exist
if not global.agent_inbox then
    global.agent_inbox = {}
end

global.actions.get_messages = function(player_index)
    -- Return messages for this player
    if not global.agent_inbox[player_index] then
        global.agent_inbox[player_index] = {}
    end
    
    -- Convert messages to a simple string format
    local messages = {}
    for _, msg in ipairs(global.agent_inbox[player_index]) do
        table.insert(messages, string.format("%d|%s|%d|%d", 
            msg.sender, 
            msg.message, 
            msg.timestamp, 
            msg.recipient))
    end
    
    return table.concat(messages, "\n")
end 