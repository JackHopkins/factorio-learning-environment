-- Initialize agent inboxes if they don't exist
if not global.agent_inbox then
    global.agent_inbox = {}
end

-- Register event listener for console chat
script.on_event(defines.events.on_console_chat, function(event)
    if event.player_index then  -- Only process player messages
        global.actions.send_message(0, event.message, -1)
    end
end)

global.actions.send_message = function(player_index, message, recipient)
    -- Parse A2A message if it's in JSON format
    local message_entry
    if type(message) == "string" and message:sub(1,1) == "{" then
        -- Try to parse as A2A message
        local success, parsed = pcall(function()
            return game.json_to_table(message)
        end)
        
        if success then
            message_entry = {
                message = parsed.content,
                sender = parsed.sender,
                recipient = parsed.recipient,
                timestamp = parsed.timestamp or game.tick,
                message_type = parsed.message_type or "text",
                metadata = parsed.metadata or {},
                is_new = parsed.is_new
            }
        else
            -- Fallback to regular message if JSON parsing fails
            message_entry = {
                message = message,
                sender = player_index,
                recipient = recipient,
                timestamp = game.tick,
                message_type = "text",
                metadata = {},
                is_new = true
            }
        end
    else
        -- Legacy message format
        message_entry = {
            message = message,
            sender = player_index,
            recipient = recipient,
            timestamp = game.tick,
            message_type = "text",
            metadata = {},
            is_new = true
        }
    end
    
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