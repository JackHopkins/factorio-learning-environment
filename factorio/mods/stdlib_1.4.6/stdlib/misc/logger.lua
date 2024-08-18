--- For logging debug information to files.
-- @module Misc.Logger
-- @usage
-- local Logger = require('__stdlib__/stdlib/misc/logger')
-- -- or to create a new logger directly:
-- local Log = require('__stdlib__/stdlib/misc/logger').new()
-- -- log files are saved to script-output/modname/log.log by default

local Logger = {
   __class = 'Logger',
    _loggers = {},
    __call = function(self, ...)
        return self.get(...)
    end,
    __index = require('__stdlib__/stdlib/core')
}
setmetatable(Logger, Logger)

local table = require('__stdlib__/stdlib/utils/table')

-- Set on the individual log object, either logs a message or writes immediatly if nil.
local _Log_mt = {
    __call = function(self, msg)
        if msg then
            return self, self.log(msg)
        else
            return self, self.write()
        end
    end
}

local format = string.format

--- Get a saved log or create a new one if there is no saved log.
function Logger.get(...)
    local log_name = (...) or 'log'
    return Logger._loggers[log_name] or Logger.new(...)
end

--- Creates a new logger object.
-- In debug mode, the logger writes to file immediately, otherwise the logger buffers the lines.
-- <p>The logger flushes the logged messages every 60 seconds since the last message.
-- <p>A table of @{options} may be specified when creating a logger.
-- @usage
--Log = Logger.new()
--Log("this msg will be logged in /script-output/YourModName/log.log!")
-- -- Immediately Write everything buffered in the log file
-- Log()
--
-- @usage
--Log = Logger.new('test', true)
--Log("this msg will be logged and written immediately in /script-output/YourModName/test.log!")
--
-- @usage
--Log = Logger.new('cool_mod_name', 'test', true, { file_extension = data })
--Log("this msg will be logged and written immediately in /script-output/YourModName/test.data!")
--
-- @tparam[opt='log'] string log_name the name of the logger
-- @tparam[opt=false] boolean debug_mode toggles the debug state of logger
-- @tparam[opt={...}] options options a table with optional arguments
-- @return (<span class="types">@{Logger}</span>) the logger instance
function Logger.new(log_name, debug_mode, options)

    local mod_name = script and script.mod_name or 'Data'
    log_name = log_name or 'log'

    Logger._loggers[log_name] = nil

    options = options or {}

    local Log = {
       __class = 'Log',
        mod_name = mod_name,
        log_name = log_name,
        debug_mode = debug_mode,
        buffer = {},
        last_written = 0,
        ever_written = false,
    }

    ---
    -- Used in the @{new} function for logging game ticks, specifying logfile extension, or forcing the logs to append to the end of the logfile.
    -- @tfield[opt=false] boolean log_ticks whether to include the game tick timestamp in the logs
    -- @tfield[opt="log"] string file_extension a string that overrides the default logfile extension
    -- @tfield[opt=false] boolean force_append if true, every new message appends to the current logfile instead of creating a new one
    -- @table Log.options
    Log.options = {
        log_ticks = options.log_ticks or false,
        file_extension = options.file_extension or 'log',
        force_append = options.force_append or false
    }

    Log.file_name = mod_name .. '/' .. log_name .. (log_name:find('%.') and '' or '.' .. Log.options.file_extension)
    Log.ever_written = Log.options.force_append

    --- Logs a message.
    -- @tparam string|table msg the message to log. @{table}s will be dumped using [serpent](https://github.com/pkulchenko/serpent) which is included in the official Factorio Lualib
    -- @return (<span class="types">@{Logger}</span>) the logger instance
    -- @see https://forums.factorio.com/viewtopic.php?f=25&t=23844 Debugging utilities built in to Factorio
    function Log.log(msg)

        if type(msg) ~= 'string' then
            msg = serpent.block(msg, {comment = false, nocode = true, sparse = true})
        end

        if _G.game then
            local tick = game.tick
            local floor = math.floor
            local time_s = floor(tick / 60)
            local time_minutes = floor(time_s / 60)
            local time_hours = floor(time_minutes / 60)

            if Log.options.log_ticks then
                table.insert(Log.buffer, format('%02d:%02d:%02d.%02d: %s\n', time_hours, time_minutes % 60, time_s % 60, tick - time_s * 60, msg))
            else
                table.insert(Log.buffer, format('%02d:%02d:%02d: %s\n', time_hours, time_minutes % 60, time_s % 60, msg))
            end

            -- write the log every minute
            if (Log.debug_mode or (tick - Log.last_written) > 3600) then
                return Log.write()
            end
        else
            if _G.script then --buffer when a save is loaded but _G.game isn't available
                if Log.options.log_ticks then
                    table.insert(Log.buffer, format('00:00:00:00: %s\n', msg))
                else
                    table.insert(Log.buffer, format('00:00:00: %s\n', msg))
                end
            else --log in data stage
                log(format('%s/%s: %s', Log.mod_name, Log.log_name, msg))
            end
        end
        return Log
    end

    --- Writes out all buffered messages immediately.
    -- @return (<span class="types">@{Logger}</span>) the logger instance
    function Log.write()
        if _G.game and table.size(Log.buffer) > 0 then
            Log.last_written = game.tick
            game.write_file(Log.file_name, table.concat(Log.buffer), Log.ever_written)
            Log.buffer = {}
            Log.ever_written = true
        end
        return Log
    end

    setmetatable(Log, _Log_mt)
    Logger._loggers[log_name] = Log
    return Log
end

return Logger
