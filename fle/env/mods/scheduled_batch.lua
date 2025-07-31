-- Batch processing system for scheduling commands at specific game ticks
-- This script allows submitting multiple commands that will be executed at future ticks

game.print("[BATCH] Loading scheduled_batch.lua script...")

-- Initialize storage for scheduled commands and results
if not global.scheduled_commands then
    global.scheduled_commands = {}
    game.print("[BATCH] Initialized global.scheduled_commands")
end

if not global.batch_results then
    global.batch_results = {}
    game.print("[BATCH] Initialized global.batch_results")
end

if not global.last_error then
    global.last_error = nil
    game.print("[BATCH] Initialized global.last_error")
end

-- Initialize parallel user tick counter
if not global.user_tick then
    global.user_tick = 0
    game.print("[BATCH] Initialized global.user_tick to 0")
end

-- Helper function to generate unique batch IDs
local function generate_batch_id()
    local batch_id = "batch_" .. global.user_tick .. "_" .. math.random(1000, 9999)
    game.print("[BATCH] Generated batch_id: " .. batch_id)
    return batch_id
end

game.print("[BATCH] Defining global.actions table...")

-- Submit a batch of scheduled commands
global.actions.submit_scheduled_batch = function(batch_json)
    game.print("Called submit_scheduled_batch")
    game.print("[BATCH] submit_scheduled_batch called with batch_json length: " .. (batch_json and string.len(batch_json) or "nil"))
    
    -- Add error handling and debugging
    local success, result = pcall(function()
        if not batch_json then
            error("batch_json parameter is nil")
        end
        
        game.print("[BATCH] Parsing batch_json...")
        local batch_data = game.json_to_table(batch_json)
        if not batch_data then
            error("Failed to parse batch_json")
        end
        
        game.print("[BATCH] Successfully parsed batch_data with " .. #batch_data .. " commands")
        
        local submitted_count = 0
        local batch_id = generate_batch_id()
        
        -- Initialize results storage for this batch
        global.batch_results[batch_id] = {
            commands = {},
            completed = false,
            total_commands = #batch_data
        }
        
        game.print("[BATCH] Processing " .. #batch_data .. " commands for batch " .. batch_id .. " (current user_tick: " .. global.user_tick .. ")")
        
        -- Schedule each command for execution at its specified tick
        for i, cmd_data in ipairs(batch_data) do
            local target_tick = cmd_data.tick
            local command = cmd_data.command
            local parameters = cmd_data.parameters
            local raw = cmd_data.raw
            
            game.print("[BATCH] Scheduling command " .. i .. ": " .. command .. " at user_tick " .. target_tick)
            
            -- Initialize the tick if it doesn't exist
            if not global.scheduled_commands[target_tick] then
                global.scheduled_commands[target_tick] = {}
            end
            
            -- Add the command to be executed at this tick
            table.insert(global.scheduled_commands[target_tick], {
                batch_id = batch_id,
                command_index = i,
                command = command,
                parameters = parameters,
                raw = raw
            })
            
            submitted_count = submitted_count + 1
        end
        
        game.print("[BATCH] Successfully scheduled " .. submitted_count .. " commands for batch " .. batch_id)
        
        local response_data = {
            submitted = submitted_count,
            message = "Batch scheduled successfully",
            batch_id = batch_id,
            current_user_tick = global.user_tick
        }
        
        game.print("[BATCH] Preparing response data: " .. game.table_to_json(response_data))
        return response_data
    end)
    
    if success then
        game.print("[BATCH] submit_scheduled_batch completed successfully")
        local json_result = game.table_to_json(result)
        game.print("[BATCH] Sending JSON result: " .. json_result)
        rcon.print(dump(result))  -- Use Lua table syntax instead of JSON
    else
        game.print("[BATCH] ERROR in submit_scheduled_batch: " .. tostring(result))
        global.last_error = tostring(result)
        local error_result = {
            error = tostring(result),
            submitted = 0,
            message = "Batch submission failed: " .. tostring(result)
        }
        local json_error = game.table_to_json(error_result)
        game.print("[BATCH] Sending JSON error: " .. json_error)
        rcon.print(dump(error_result))  -- Use Lua table syntax instead of JSON
    end
end

game.print("[BATCH] Defined submit_scheduled_batch function")

-- Process scheduled commands on each tick and increment user tick
script.on_event(defines.events.on_tick, function(event)
    -- Increment our parallel user tick counter
    global.user_tick = global.user_tick + 1
    
    local current_user_tick = global.user_tick
    
    if global.scheduled_commands[current_user_tick] then
        game.print("[BATCH] Processing commands at user_tick " .. current_user_tick .. " (game tick " .. event.tick .. ", found " .. #global.scheduled_commands[current_user_tick] .. " commands)")
        
        for _, scheduled_cmd in ipairs(global.scheduled_commands[current_user_tick]) do
            game.print("[BATCH] Executing command: " .. scheduled_cmd.command .. " (batch: " .. scheduled_cmd.batch_id .. ", index: " .. scheduled_cmd.command_index .. ")")
            
            -- Execute the command using the instance's command system
            local success, result = pcall(function()
                if scheduled_cmd.raw then
                    return global.actions.raw_command(table.unpack(scheduled_cmd.parameters))
                else
                    return global.actions[scheduled_cmd.command](table.unpack(scheduled_cmd.parameters))
                end
            end)
            
            -- Store the result
            if not global.batch_results[scheduled_cmd.batch_id] then
                global.batch_results[scheduled_cmd.batch_id] = {commands = {}, completed = false}
            end
            
            global.batch_results[scheduled_cmd.batch_id].commands[scheduled_cmd.command_index] = {
                command = scheduled_cmd.command,
                success = success,
                result = success and result or tostring(result),
                user_tick = current_user_tick,
                game_tick = event.tick
            }
            
            game.print("[BATCH] Stored result for command " .. scheduled_cmd.command_index .. " in batch " .. scheduled_cmd.batch_id .. ": success=" .. tostring(success))
            
            if success then
                game.print("[BATCH] Command executed successfully")
            else
                game.print("[BATCH] Command failed: " .. tostring(result))
            end
        end
        
        -- Clean up this tick's commands
        global.scheduled_commands[current_user_tick] = nil
        game.print("[BATCH] Cleaned up commands for user_tick " .. current_user_tick)
    end
end)

game.print("[BATCH] Registered on_tick event handler")

-- Get results for a specific batch
global.actions.get_batch_results = function(batch_id)
    game.print("[BATCH] get_batch_results called for batch_id: " .. (batch_id or "nil"))
    
    if not batch_id then
        game.print("[BATCH] ERROR: batch_id is nil")
        local error_result = {error = "batch_id is required"}
        rcon.print(dump(error_result))  -- Use Lua table syntax instead of JSON
        return
    end
    
    local batch_results = global.batch_results[batch_id]
    if not batch_results then
        game.print("[BATCH] ERROR: No results found for batch_id: " .. batch_id)
        local error_result = {error = "Batch not found", batch_id = batch_id}
        rcon.print(dump(error_result))  -- Use Lua table syntax instead of JSON
        return
    end
    
    game.print("[BATCH] Found batch_results for " .. batch_id .. ": " .. game.table_to_json(batch_results))
    
    -- Check if all commands have completed
    local completed_count = 0
    for _ in pairs(batch_results.commands) do
        completed_count = completed_count + 1
    end
    
    game.print("[BATCH] Command count check: " .. completed_count .. " completed out of " .. (batch_results.total_commands or 0) .. " total")
    
    local is_complete = completed_count >= (batch_results.total_commands or 0)
    batch_results.completed = is_complete
    
    -- game.print("[BATCH] Returning results for batch " .. batch_id .. ": " .. completed_count .. "/" .. (batch_results.total_commands or 0) .. " completed (current user_tick: " .. global.user_tick .. ", game_tick: " .. game.tick .. ")")
    
    -- Debug: Print scheduled commands in a concise format
    local scheduled_summary = {}
    for tick, commands in pairs(global.scheduled_commands) do
        scheduled_summary[tick] = #commands
    end
    game.print("[BATCH] Scheduled commands by user_tick: " .. game.table_to_json(scheduled_summary))
    
    local result = {
        batch_id = batch_id or "unknown",
        results = batch_results.commands or {},
        completed = is_complete or false,
        total_commands = batch_results.total_commands or 0,
        completed_commands = completed_count or 0,
        current_user_tick = global.user_tick or 0,
        current_game_tick = game.tick or 0
    }
    
    game.print("[BATCH] Returning results for batch " .. batch_id .. ": " .. game.table_to_json(result))
    log("[BATCH] Returning results for batch " .. batch_id .. ": " .. game.table_to_json(result))
    rcon.print(dump(result))  -- Use Lua table syntax instead of JSON
end

game.print("[BATCH] Defined get_batch_results function")

-- Clear results for a specific batch or all batches
global.actions.clear_batch_results = function(batch_id)
    game.print("[BATCH] clear_batch_results called for batch_id: " .. (batch_id or "all"))
    
    local result
    if batch_id then
        global.batch_results[batch_id] = nil
        game.print("[BATCH] Cleared results for batch: " .. batch_id)
        result = {message = "Cleared results for batch: " .. batch_id}
    else
        global.batch_results = {}
        game.print("[BATCH] Cleared all batch results")
        result = {message = "Cleared all batch results"}
    end
    rcon.print(dump(result))  -- Use Lua table syntax instead of JSON
end

game.print("[BATCH] Defined clear_batch_results function")

-- Reset user tick to a specific value (useful for batch processing)
global.actions.reset_user_tick = function(new_tick)
    new_tick = new_tick or 0
    local previous_user_tick = global.user_tick
    game.print("[BATCH] Resetting user_tick from " .. global.user_tick .. " to " .. new_tick)
    
    -- Clear any existing scheduled commands since tick numbers will be invalid
    local cleared_commands = 0
    for tick, commands in pairs(global.scheduled_commands) do
        cleared_commands = cleared_commands + #commands
    end
    global.scheduled_commands = {}
    
    global.user_tick = new_tick
    
    local result = {
        message = "User tick reset to " .. new_tick,
        previous_user_tick = previous_user_tick,
        current_user_tick = global.user_tick,
        current_game_tick = game.tick,
        cleared_scheduled_commands = cleared_commands
    }
    
    game.print("[BATCH] User tick reset successfully. Cleared " .. cleared_commands .. " scheduled commands.")
    rcon.print(dump(result))  -- Use Lua table syntax instead of JSON
end

game.print("[BATCH] Defined reset_user_tick function")
game.print("[BATCH] scheduled_batch.lua script loaded successfully!") 