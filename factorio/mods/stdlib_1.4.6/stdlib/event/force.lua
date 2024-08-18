--- Force global creation.
-- <p>All new forces will be added to the `global.forces` table.
-- <p>This modules events should be registered after any other Init functions but before any scripts needing `global.players`.
-- <p>This modules can register the following events: `on_force_created`, and `on_forces_merging`.
-- @module Event.Force
-- @usage
-- local Force = require('__stdlib__/stdlib/event/force').register_events()
-- -- inside your Init event Force.init() -- to properly handle any existing forces

local Event = require('__stdlib__/stdlib/event/event')

local Force = {
   __class = 'Force',
   __index = require('__stdlib__/stdlib/core'),
    _new_force_data = {}
}
setmetatable(Force, Force)

local Game = require('__stdlib__/stdlib/game')
local table = require('__stdlib__/stdlib/utils/table')
local merge_additional_data = require('__stdlib__/stdlib/event/modules/merge_data')
local assert, type = assert, type

-- return new default force object
local function new(force_name)
    local fdata = {
        index = force_name,
        name = force_name
    }

    merge_additional_data(Force._new_force_data, fdata)

    return fdata
end

function Force.additional_data(...)
    for _, func_or_table in pairs({...}) do
        local var_type = type(func_or_table)
        assert(var_type == 'table' or var_type == 'function', 'Must be table or function')
        Force._new_force_data[#Force._new_force_data + 1] = func_or_table
    end
    return Force
end

--- Get `game.forces[name]` & `global.forces[name]`, or create `global.forces[name]` if it doesn't exist.
-- @tparam string|LuaForce force the force to get data for
-- @treturn LuaForce the force instance
-- @treturn table the force's global data
-- @usage
-- local Force = require('__stdlib__/stdlib/event/force')
-- local force_name, force_data = Force.get("player")
-- local force_name, force_data = Force.get(game.forces["player"])
-- -- Returns data for the force named "player" from either a string or LuaForce object
function Force.get(force)
    force = Game.get_force(force)
    assert(force, 'force is missing')
    return game.forces[force.name], global.forces and global.forces[force.name] or Force.init(force.name)
end

--- Merge a copy of the passed data to all forces in `global.forces`.
-- @tparam table data a table containing variables to merge
-- @usage
-- local data = {a = "abc", b = "def"}
-- Force.add_data_all(data)
function Force.add_data_all(data)
    table.each(
        global.forces,
        function(v)
            table.merge(v, table.deepcopy(data))
        end
    )
end

--- Init or re-init a force or forces.
-- Passing a `nil` event will iterate all existing forces.
-- @tparam[opt] string|table event table or a string containing force name
-- @tparam[opt=false] boolean overwrite the force data
function Force.init(event, overwrite)
    global.forces = global.forces or {}

    local force = Game.get_force(event)

    if force then
        if not global.forces[force.name] or (global.forces[force.name] and overwrite) then
            global.forces[force.name] = new(force.name)
            return global.forces[force.name]
        end
    else
        for name in pairs(game.forces) do
            if not global.forces[name] or (global.forces[name] and overwrite) then
                global.forces[name] = new(name)
            end
        end
    end
    return Force
end

function Force.dump_data()
    game.write_file(Force.get_file_path('Force/force_data.lua'), 'return ' .. inspect(Force._new_force_data, {longkeys = true, arraykeys = true}))
    game.write_file(Force.get_file_path('Force/global.lua'), 'return ' .. inspect(global.forces or nil, {longkeys = true, arraykeys = true}))
end

--- When forces are merged, just remove the original forces data
function Force.merged(event)
    global.forces[event.source_name] = nil
end

function Force.register_init()
    Event.register(Event.core_events.init, Force.init)
    return Force
end

--- Register Events
function Force.register_events(do_on_init)
    Event.register(defines.events.on_force_created, Force.init)
    Event.register(defines.events.on_forces_merged, Force.merged)
    if do_on_init then
        Force.register_init()
    end
    return Force
end

return Force
