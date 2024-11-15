--- Additional lua globals
-- @module Utils.Globals

local config = require('__stdlib__/stdlib/config')

local Table = require('__stdlib__/stdlib/utils/table')
local Math = require('__stdlib__/stdlib/utils/math')
local String = require('__stdlib__/stdlib/utils/string')

local STDLIB = {
    Math = Math,
    String = String,
    Table = Table
}
rawset(_ENV, 'STDLIB', STDLIB)

--Since debug can be overridden we define a fallback function here.
local ignored = {
    data_traceback = true,
    log_trace = true
}

local traceback = type(debug) == 'table' and debug.traceback or function()
        return ''
    end
    rawset(_ENV, 'traceback', traceback)
local data_traceback = type(debug) == 'table' and debug.getinfo and function()
        local str = {}
        local level = 1
        while true do
            local trace = debug.getinfo(level)
            if trace then
                level = level + 1
                if (trace.what == 'Lua' or trace.what == 'main') and not ignored[trace.name] then
                    local cur = trace.source:gsub('.*__stdlib__', '__stdlib__'):gsub('.*/Factorio%-Stdlib', '__stdlib__')
                    cur = cur .. ':' .. (trace.currentline or '0') .. ' in ' .. (trace.name or '???')
                    str[#str + 1] = cur
                end
                if trace.what == 'main' then
                    break
                end
            else
                break
            end
        end
        return ' [' .. table.concat(str, ', ') .. ']'
    end or function()
        return ''
    end
rawset(_ENV, 'data_traceback', data_traceback)

local inspect = require('__stdlib__/stdlib/vendor/inspect')
rawset(_ENV, 'inspect', inspect)

-- Set up faketorio for local testing, defines will already be available in an active mod or busted specs
if not _ENV.defines then
    _ENV.table.unpack = _ENV.table.unpack or _ENV.unpack
    if _ENV.os and _ENV.os.getenv('LOCAL_LUA_DEBUGGER_VSCODE') == '1' then
        require('__stdlib__/faketorio/require')
        _ENV.package.strip_indentifier()
    end
    if config.control or config.game then
        local world = require('__stdlib__/faketorio/world').bootstrap()
        if config.game then
            world.init()
        end
    else
        require('__stdlib__/faketorio/dataloader')
    end
    _ENV.log = function(msg)
        print(msg)
    end
end

-- Defines Mutates
require('__stdlib__/stdlib/utils/defines/color')
require('__stdlib__/stdlib/utils/defines/anticolor')
require('__stdlib__/stdlib/utils/defines/lightcolor')
require('__stdlib__/stdlib/utils/defines/time')

-- Settings Mutates
if _ENV.settings then
    function _ENV.settings.get(cat, key)
        return _ENV.settings[cat][key] and _ENV.settings[cat][key].value
    end
    function _ENV.settings.get_startup(key)
        return _ENV.settings.get('startup', key)
    end
end

-- Dubug Adapter Mutates
if _ENV.__DebugAdapter then
    if _ENV.__DebugAdapter.attach then
        -- Add our custom mutate info to the debugadapter.
        if _ENV.settings and _ENV.settings.get then
            local object_info = require('__debugadapter__/luaobjectinfo.lua')
            object_info.expandKeys['LuaSettings']['get'] = {}
            object_info.expandKeys['LuaSettings']['get_startup'] = {}
        end
    end
else
    _ENV.__DebugAdapter = {
        print = function()
        end,
        stepIgnoreAll = function()
        end,
        stepIgnore = function()
        end,
        breakpoint = function()
        end,
        levelPath = function()
        end
    }
    _ENV.__Profiler = _ENV.DebugAdapter
end

--- Require a file that may not exist
-- @tparam string module path to the module
-- @tparam boolean suppress_all suppress all errors, not just file_not_found
-- @treturn mixed
local function prequire(module, suppress_all)
    local ok, err = pcall(require, module)
    if ok then
        return err
    elseif not suppress_all and not err:find('^module .* not found') then
        error(err)
    end
end
rawset(_ENV, 'prequire', prequire)

--- Temporarily removes __tostring handlers and calls tostring
-- @tparam mixed t object to call rawtostring on
-- @treturn string
local function rawtostring(t)
    local m = getmetatable(t)
    if m then
        local f = m.__tostring
        m.__tostring = nil
        local s = tostring(t)
        m.__tostring = f
        return s
    else
        return tostring(t)
    end
end
rawset(_ENV, 'rawtostring', rawtostring)

--- Returns t if the expression is true. f if false
-- @tparam mixed exp The expression to evaluate
-- @tparam mixed t the true return
-- @tparam mixed f the false return
-- @treturn boolean
local function inline_if(exp, t, f)
    if exp then
        return t
    else
        return f
    end
end
rawset(_ENV, 'inline_if', inline_if)

local function concat(lhs, rhs)
    return tostring(lhs) .. tostring(rhs)
end
rawset(_ENV, 'concat', concat)

--- install the Table library into global table
function STDLIB.install_table()
    for k, v in pairs(Table) do
        _G.table[k] = v
    end
end

--- Install the Math library into global math
function STDLIB.install_math()
    for k, v in pairs(Math) do
        _G.math[k] = v
    end
end

--- Install the string library into global string
function STDLIB.install_string()
    for k, v in pairs(String) do
        _G.string[k] = v
    end
    setmetatable(string, nil)
end

--- Install Math, String, Table into their global counterparts.
function STDLIB.install_global_utils()
    STDLIB.install.math()
    STDLIB.install.string()
    STDLIB.install.table()
end

--- Reload a required file, NOT IMPLEMENTED
function STDLIB.reload_class()
end

--- load the stdlib into globals, by default it loads everything into an ALLCAPS name.
-- Alternatively you can pass a dictionary of `[global names] -> [require path]`.
-- @tparam[opt] table files
-- @usage
-- STDLIB.create_stdlib_globals()
function STDLIB.create_stdlib_globals(files)
    files =
        files or
        {
            GAME = 'stdlib/game',
            AREA = 'stdlib/area/area',
            POSITION = 'stdlib/area/position',
            TILE = 'stdlib/area/tile',
            SURFACE = 'stdlib/area/surface',
            CHUNK = 'stdlib/area/chunk',
            COLOR = 'stdlib/utils/color',
            ENTITY = 'stdlib/entity/entity',
            INVENTORY = 'stdlib/entity/inventory',
            RESOURCE = 'stdlib/entity/resource',
            CONFIG = 'stdlib/misc/config',
            LOGGER = 'stdlib/misc/logger',
            QUEUE = 'stdlib/misc/queue',
            EVENT = 'stdlib/event/event',
            GUI = 'stdlib/event/gui',
            PLAYER = 'stdlib/event/player',
            FORCE = 'stdlib/event/force',
            TABLE = 'stdlib/utils/table',
            STRING = 'stdlib/utils/string',
            MATH = 'stdlib/utils/math'
        }
    for glob, path in pairs(files) do
        rawset(_ENV, glob, require('__stdlib__/' .. (path:gsub('%.', '/')))) -- extra () required to emulate select(1)
    end
end

function STDLIB.create_stdlib_data_globals(files)
    files =
        files or
        {
            RECIPE = 'stdlib/data/recipe',
            ITEM = 'stdlib/data/item',
            FLUID = 'stdlib/data/fluid',
            ENTITY = 'stdlib/data/entity',
            TECHNOLOGY = 'stdlib/data/technology',
            CATEGORY = 'stdlib/data/category',
            DATA = 'stdlib/data/data',
            TABLE = 'stdlib/utils/table',
            STRING = 'stdlib/utils/string',
            MATH = 'stdlib/utils/math',
            COLOR = 'stdlib/utils/color'
        }
    STDLIB.create_stdlib_globals(files)
end

return STDLIB
