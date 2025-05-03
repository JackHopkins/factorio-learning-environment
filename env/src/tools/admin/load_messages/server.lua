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
    -- game.print("Loading messages - " .. serpent.block(messages))
    
    for _, msg in ipairs(messages) do
        local message = msg.message
        local sender = msg.sender
        local recipient = msg.recipient
        local timestamp = msg.timestamp
        
        -- game.print("Message loaded - From: " .. sender .. " To: " .. recipient .. " Message: " .. message .. " Timestamp: " .. timestamp)
        if not global.agent_inbox[recipient] then
            global.agent_inbox[recipient] = {}
        end
        table.insert(global.agent_inbox[recipient], {
            sender = tonumber(sender),
            message = "test message",
            timestamp = tonumber(timestamp),
            recipient = tonumber(recipient)
        })
        
        if sender and message and timestamp and recipient then
            sender = tonumber(sender)
            timestamp = tonumber(timestamp)
            recipient = tonumber(recipient)
            
            if not global.agent_inbox[recipient] then
                global.agent_inbox[recipient] = {}
            end
            
            table.insert(global.agent_inbox[recipient], {
                sender = sender,
                message = message,
                timestamp = timestamp,
                recipient = recipient
            })
            
            -- game.print("Message loaded - From: " .. sender .. " To: " .. recipient .. " Message: " .. message)
            messages_loaded = messages_loaded + 1
        end
    end
    
    return messages_loaded
end
