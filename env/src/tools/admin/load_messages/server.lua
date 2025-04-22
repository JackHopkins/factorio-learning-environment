-- Initialize agent inboxes if they don't exist
if not global.agent_inbox then
    global.agent_inbox = {}
end

global.actions.load_messages = function(messages_str)
    -- If agent inbox already has messages, exit early
    local has_messages = false
    for _, _ in pairs(global.agent_inbox) do
        has_messages = true
        break
    end
    if has_messages then
        return true
    end

    -- Parse the messages string
    local messages = {}
    for line in string.gmatch(messages_str, "[^\n]+") do
        local sender, message, timestamp, recipient = string.match(line, "(%d+)|(.+)|(%d+)|(%d+)")
        if sender and message and timestamp and recipient then
            -- Convert string values to numbers where appropriate
            sender = tonumber(sender)
            timestamp = tonumber(timestamp)
            recipient = tonumber(recipient)
            
            -- Initialize recipient's inbox if it doesn't exist
            if not global.agent_inbox[recipient] then
                global.agent_inbox[recipient] = {}
            end
            
            -- Add message to recipient's inbox
            table.insert(global.agent_inbox[recipient], {
                sender = sender,
                message = message,
                timestamp = timestamp,
                recipient = recipient
            })
        end
    end
    
    return true
end
