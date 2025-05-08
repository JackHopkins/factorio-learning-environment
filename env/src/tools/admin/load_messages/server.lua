-- Initialize agent inboxes if they don't exist
if not global.agent_inbox then
    global.agent_inbox = {}
end

global.actions.load_messages = function(messages)
    -- If agent inbox already has messages, exit early
    local has_messages = false
    for _, _ in pairs(global.agent_inbox) do
        has_messages = true
        break
    end
    --if has_messages then
    --    return true
    --end

    -- Parse the messages list
    local messages_loaded = 0
    for _, msg in ipairs(messages) do
        local message = msg.message
        local sender = msg.sender
        local recipient = msg.recipient
        local timestamp = msg.timestamp
        
        if sender and message and timestamp and recipient then
            sender = tonumber(sender)
            timestamp = tonumber(timestamp)
            recipient = tonumber(recipient)
            
            -- If recipient is -1, send to all agents except sender
            if recipient == -1 then
                for agent_idx, _ in pairs(global.agent_characters) do
                    if agent_idx ~= sender then
                        if not global.agent_inbox[agent_idx] then
                            global.agent_inbox[agent_idx] = {}
                        end
                        
                        table.insert(global.agent_inbox[agent_idx], {
                            sender = sender,
                            message = message, 
                            timestamp = timestamp,
                            recipient = agent_idx
                        })
                        
                        messages_loaded = messages_loaded + 1
                    end
                end
            else
                -- Send to specific recipient
                if not global.agent_inbox[recipient] then
                    global.agent_inbox[recipient] = {}
                end
                
                table.insert(global.agent_inbox[recipient], {
                    sender = sender,
                    message = message,
                    timestamp = timestamp,
                    recipient = recipient
                })
                
                messages_loaded = messages_loaded + 1
            end
        end
    end
    
    return messages_loaded
end
