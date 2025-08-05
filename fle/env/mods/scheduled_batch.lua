-- Batch processing system for scheduling commands at specific game ticks
-- This script allows submitting multiple commands that will be executed at future ticks
-- Override global print to write to a file
local function file_print(msg)
    local str = tostring(msg)
    -- Writes to script-output/server.log, append = true, server only (0)
    if game then
        game.write_file("/home/server.log", str .. "\n", true, 0)
    else
        -- fallback before game is created
        log(str)
    end
end

-- Replace the global print function
print = file_print

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

-- Initialize sequence tracking
if not global.sequence_start_tick then
    global.sequence_start_tick = nil
    game.print("[BATCH] Initialized global.sequence_start_tick")
end

if not global.sequence_grace_period then
    global.sequence_grace_period = 0
    game.print("[BATCH] Initialized global.sequence_grace_period")
end

if not global.current_sequence_id then
    global.current_sequence_id = nil
    game.print("[BATCH] Initialized global.current_sequence_id")
end

if not global.batch_metadata then
    global.batch_metadata = {}
    game.print("[BATCH] Initialized global.batch_metadata")
end

-- Helper function to generate unique batch IDs
local function generate_batch_id()
    local batch_id = "batch_" .. game.tick .. "_" .. math.random(1000, 9999)
    return batch_id
end

-- Function to register a sequence start with optional grace period
global.actions.register_sequence_start = function(sequence_id, grace_period)
    sequence_id = sequence_id or "default"
    grace_period = grace_period or 0
    
    local result
    
    -- Check if this is a new sequence ID (different from current)
    if global.current_sequence_id and global.current_sequence_id ~= sequence_id then
        game.print("[BATCH] New sequence ID detected (" .. sequence_id .. " vs " .. global.current_sequence_id .. "), resetting sequence")
        -- Reset sequence for new sequence ID
        global.sequence_start_tick = nil
        global.sequence_grace_period = 0
        global.current_sequence_id = nil
        global.batch_metadata = {}
        
        -- Clear any pending scheduled commands
        local cleared_commands = 0
        for tick, commands in pairs(global.scheduled_commands) do
            cleared_commands = cleared_commands + #commands
        end
        global.scheduled_commands = {}
        game.print("[BATCH] Auto-reset sequence. Cleared " .. cleared_commands .. " scheduled commands.")
    end
    
    if not global.sequence_start_tick then
        -- First batch submission or after reset - establish the sequence start with grace period
        global.sequence_start_tick = game.tick + grace_period
        global.sequence_grace_period = grace_period
        global.current_sequence_id = sequence_id -- Set the current sequence ID
        result = {
            sequence_id = sequence_id,
            sequence_start_tick = global.sequence_start_tick,
            grace_period = grace_period,
            current_game_tick = game.tick,
            message = "New sequence started with grace period",
            is_new_sequence = true
        }
        game.print("[BATCH] Started new sequence '" .. sequence_id .. "' at game_tick " .. global.sequence_start_tick .. " (grace period: " .. grace_period .. ")")
    else
        -- Subsequent batch - use existing sequence start (same sequence ID)
        result = {
            sequence_id = sequence_id,
            sequence_start_tick = global.sequence_start_tick,
            grace_period = global.sequence_grace_period,
            current_game_tick = game.tick,
            message = "Using existing sequence start",
            is_new_sequence = false
        }
        game.print("[BATCH] Using existing sequence '" .. sequence_id .. "' start at game_tick " .. global.sequence_start_tick)
    end
    
    rcon.print(dump(result))
    return result
end

-- Function to reset/clear the sequence (for new batch sequences)
global.actions.reset_sequence = function()
    global.sequence_start_tick = nil
    global.sequence_grace_period = 0
    global.current_sequence_id = nil -- Reset current sequence ID
    global.batch_metadata = {}
    
    -- Clear any pending scheduled commands
    local cleared_commands = 0
    for tick, commands in pairs(global.scheduled_commands) do
        cleared_commands = cleared_commands + #commands
    end
    global.scheduled_commands = {}
    
    local result = {
        message = "Sequence reset",
        cleared_scheduled_commands = cleared_commands,
        current_game_tick = game.tick
    }
    
    rcon.print(dump(result))
    return result
end

-- Function to clear scheduled commands for a specific sequence ID
global.actions.clear_sequence_commands = function(target_sequence_id)
    if not target_sequence_id then
        local error_result = {error = "target_sequence_id parameter is required"}
        rcon.print(dump(error_result))
        return
    end
    
    local cleared_commands = 0
    local total_commands_before = 0
    
    -- Count total commands before cleanup
    for tick, commands in pairs(global.scheduled_commands) do
        total_commands_before = total_commands_before + #commands
    end
    
    -- Clear scheduled commands that belong to the target sequence
    for tick, commands in pairs(global.scheduled_commands) do
        local remaining_commands = {}
        for _, cmd in ipairs(commands) do
            -- Check if this command belongs to a batch from the target sequence
            -- We need to check batch metadata to see which sequence each batch belongs to
            local batch_metadata = global.batch_metadata[cmd.batch_id]
            if batch_metadata and batch_metadata.sequence_id == target_sequence_id then
                cleared_commands = cleared_commands + 1
                game.print("[BATCH] Clearing command for sequence " .. target_sequence_id .. " at tick " .. tick)
            else
                table.insert(remaining_commands, cmd)
            end
        end
        
        if #remaining_commands == 0 then
            global.scheduled_commands[tick] = nil
        else
            global.scheduled_commands[tick] = remaining_commands
        end
    end
    
    -- Also clear batch metadata for the target sequence
    local cleared_batches = 0
    for batch_id, metadata in pairs(global.batch_metadata) do
        if metadata.sequence_id == target_sequence_id then
            global.batch_metadata[batch_id] = nil
            cleared_batches = cleared_batches + 1
        end
    end
    
    -- If this was the current sequence, reset it
    if global.current_sequence_id == target_sequence_id then
        global.sequence_start_tick = nil
        global.sequence_grace_period = 0
        global.current_sequence_id = nil
        game.print("[BATCH] Reset current sequence as it matched target sequence " .. target_sequence_id)
    end
    
    local result = {
        message = "Sequence-specific commands cleared",
        target_sequence_id = target_sequence_id,
        cleared_commands = cleared_commands,
        cleared_batches = cleared_batches,
        total_commands_before = total_commands_before,
        total_commands_after = total_commands_before - cleared_commands,
        current_game_tick = game.tick
    }
    
    rcon.print(dump(result))
    return result
end

-- Submit a batch of scheduled commands
global.actions.submit_scheduled_batch = function(batch_json)
    local success, result = pcall(function()
        if not batch_json then
            error("batch_json parameter is nil")
        end
        
        if not global.sequence_start_tick then
            error("No sequence start registered. Call register_sequence_start first.")
        end
        
        local batch_data = game.json_to_table(batch_json)
        if not batch_data then
            error("Failed to parse batch_json")
        end
        
        local submitted_count = 0
        local immediate_count = 0
        local sequence_start = global.sequence_start_tick
        local current_tick = game.tick
        local batch_id = generate_batch_id()  -- Generate batch_id internally
        
        -- Store batch metadata
        global.batch_metadata[batch_id] = {
            sequence_start_tick = sequence_start,
            submitted_tick = current_tick,
            total_commands = #batch_data,
            sequence_id = global.current_sequence_id  -- Store the sequence ID for cleanup purposes
        }
        
        -- Initialize results storage for this batch
        global.batch_results[batch_id] = {
            commands = {},
            completed = false,
            total_commands = #batch_data
        }
        
        -- Schedule each command for execution at its absolute tick relative to sequence start
        for i, cmd_data in ipairs(batch_data) do
            local absolute_tick_in_sequence = cmd_data.tick  -- This is your [0, 10, 20] etc.
            local actual_execution_tick = sequence_start + absolute_tick_in_sequence
            
            -- Check if this tick has already passed
            if actual_execution_tick <= current_tick then
                -- Execute immediately - schedule for next tick
                actual_execution_tick = current_tick + 1
                immediate_count = immediate_count + 1
                game.print("[BATCH] Command " .. i .. " (" .. cmd_data.command .. ") scheduled for immediate execution (tick " .. actual_execution_tick .. ") - original tick " .. (sequence_start + absolute_tick_in_sequence) .. " has passed")
            end
            
            -- Initialize the execution tick if it doesn't exist
            if not global.scheduled_commands[actual_execution_tick] then
                global.scheduled_commands[actual_execution_tick] = {}
            end
            
            -- Add the command to be executed at this tick
            table.insert(global.scheduled_commands[actual_execution_tick], {
                batch_id = batch_id,
                command_index = i,
                command = cmd_data.command,
                parameters = cmd_data.parameters,
                raw = cmd_data.raw,
                sequence_tick = absolute_tick_in_sequence,  -- For debugging
                execution_tick = actual_execution_tick,     -- For debugging
                was_immediate = actual_execution_tick <= current_tick + 1,  -- For debugging
                planned_tick = cmd_data.tick  -- Store the original absolute tick from Python
            })
            
            submitted_count = submitted_count + 1
        end
        
        return {
            submitted = submitted_count,
            immediate_commands = immediate_count,
            message = "Batch scheduled successfully",
            batch_id = batch_id,
            sequence_start_tick = sequence_start,
            current_game_tick = current_tick
        }
    end)
    
    if success then
        rcon.print(dump(result))
    else
        local error_msg = type(result) == "string" and result or tostring(result)
        global.last_error = error_msg
        local error_result = {
            error = error_msg,
            submitted = 0,
            message = "Batch submission failed: " .. error_msg
        }
        rcon.print(dump(error_result))
    end
end

-- Process scheduled commands on each tick
script.on_event(defines.events.on_tick, function(event)
    local current_game_tick = event.tick
    
    if global.scheduled_commands[current_game_tick] then
        for _, scheduled_cmd in ipairs(global.scheduled_commands[current_game_tick]) do
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
                result = success and result or (type(result) == "string" and result or tostring(result)),
                game_tick = event.tick,
                was_immediate = scheduled_cmd.was_immediate or false,
                planned_tick = scheduled_cmd.planned_tick  -- Include planned_tick in results
            }
        end
        
        -- Clean up this tick's commands
        global.scheduled_commands[current_game_tick] = nil
    end
end)

-- Get results for a specific batch
global.actions.get_batch_results = function(batch_id)
    if not batch_id then
        local error_result = {error = "batch_id is required"}
        rcon.print(dump(error_result))
        return
    end
    
    local batch_results = global.batch_results[batch_id]
    if not batch_results then
        local error_result = {error = "Batch not found", batch_id = batch_id}
        rcon.print(dump(error_result))
        return
    end
    
    -- Check if all commands have completed
    local completed_count = 0
    for _ in pairs(batch_results.commands) do
        completed_count = completed_count + 1
    end
    
    local is_complete = completed_count >= (batch_results.total_commands or 0)
    batch_results.completed = is_complete
    
    local result = {
        batch_id = batch_id or "unknown",
        results = batch_results.commands or {},
        completed = is_complete or false,
        total_commands = batch_results.total_commands or 0,
        completed_commands = completed_count or 0,
        current_game_tick = game.tick or 0,
        sequence_start_tick = global.sequence_start_tick,
        sequence_grace_period = global.sequence_grace_period
    }
    
    rcon.print(dump(result))
end

-- Clear results for a specific batch or all batches
global.actions.clear_batch_results = function(batch_id)
    local result
    if batch_id then
        global.batch_results[batch_id] = nil
        global.batch_metadata[batch_id] = nil
        result = {message = "Cleared results for batch: " .. batch_id}
    else
        global.batch_results = {}
        global.batch_metadata = {}
        result = {message = "Cleared all batch results and metadata"}
    end
    rcon.print(dump(result))
end

game.print("[BATCH] scheduled_batch.lua script loaded successfully!")