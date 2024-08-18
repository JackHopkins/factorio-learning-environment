--- Configuration changed event handling.
-- This module registers events
-- @module Event.Changes
-- @usage
-- local Changes = require('__stdlib__/stdlib/event/changes')
-- Changes.register('mod_versions', 'path_to_version_file')
-- @usage
-- -- version files should return a dictionary of functions indexed by version number.
-- return {['1.0.0'] = function() end}
-- @usage
-- -- Other change files should return a single function and will run in the order they are added.
-- -- Multiple files can be registered to a change type.
-- Changes.register('any-first', 'path_to_file_1')
-- Changes.register('any-first', 'path_to_file_2')

local Event = require('__stdlib__/stdlib/event/event')

local Changes = {
    __class = 'Changes',
    __index = require('__stdlib__/stdlib/core'),
    registered_for_events = false
}
setmetatable(Changes, Changes)

--[[
    ConfigurationChangedData
    Table with the following fields:
    old_version :: string (optional): Old version of the map. Present only when loading map version other than the current version.
    new_version :: string (optional): New version of the map. Present only when loading map version other than the current version.
    mod_changes :: dictionary string → ModConfigurationChangedData: Dictionary of mod changes. It is indexed by mod name.
    ModConfigurationChangedData
    Table with the following fields:
    old_version :: string: Old version of the mod. May be nil if the mod wasn't previously present (i.e. it was just added).
    new_version :: string: New version of the mod. May be nil if the mod is no longer present (i.e. it was just removed).
--]]
local table = require('__stdlib__/stdlib/utils/table')

local map_changes = {
    ['map_first'] = true,
    ['any_first'] = true,
    ['mod_first'] = true,
    ['mod_versions'] = true,
    ['mod_last'] = true,
    ['any_last'] = true,
    ['map_last'] = true
}
for change_type in pairs(map_changes) do
    Changes[change_type] = {}
end

local function run_if_exists(path)
    for _, func in pairs(path) do
        if type(func) == 'function' then
            func()
        end
    end
end

function Changes.register_events(change_type, path)
    if map_changes[change_type] then
        if not Changes.registered_for_events then
            Event.register(Event.core_events.configuration_changed, Changes.on_configuration_changed)
            if change_type == 'mod_versions' then
                -- Register on_init only for mod_versions changes
                Event.register(Event.core_events.init, Changes.on_init)
            end
        end
        Changes[change_type][path] = require(path)
    else
        error('Incorrect change type ' .. (change_type or 'nil') .. ' expected: ' .. table.concat(table.keys(map_changes), ', ') .. '.')
    end
    return Changes
end
Changes.register = Changes.register_events

function Changes.register_versions(path)
    return Changes.register_events('mod_versions', path)
end

-- Mark all version changes as complete during Init
function Changes.on_init()
    for _, versions in pairs(Changes.mod_versions) do
        local list = {}
        local cur_version = game.active_mods[script.mod_name]
        for ver in pairs(versions) do
            list[ver] = cur_version
        end
        global._changes = list
    end
end

function Changes.on_configuration_changed(event)
    run_if_exists(Changes.map_first)
    if event.mod_changes then
        run_if_exists(Changes.any_first)
        if event.mod_changes[script.mod_name] then
            run_if_exists(Changes.mod_first)
            local this_mod_changes = event.mod_changes[script.mod_name]
            Changes.on_mod_changed(this_mod_changes)
            log(script.mod_name .. ': version changed from ' .. tostring(this_mod_changes.old_version) .. ' to ' .. tostring(this_mod_changes.new_version))
            run_if_exists(Changes.mod_last)
        end
        run_if_exists(Changes.any_last)
    end
    run_if_exists(Changes.map_last)
end

function Changes.on_mod_changed(this_mod_changes)
    global._changes = global._changes or {}

    local old = this_mod_changes.old_version
    if old then -- Find the last installed version
        local vers = {}
        for _, path in pairs(Changes.mod_versions) do
            for ver, func in pairs(path) do
                if not global._changes[ver] then
                    vers[ver] = this_mod_changes.new_version
                    func()
                    log('Migration completed for version ' .. ver)
                end
            end
        end
        table.each(
            vers,
            function(v, k)
                global._changes[k] = v
            end
        )
    end
end

function Changes.dump_data()
    for change_type in pairs(map_changes) do
        if table.size(Changes[change_type]) > 0 then
            game.write_file(Changes.get_file_path('Changes/' .. change_type .. '.lua'), 'return ' .. inspect(Changes[change_type], {longkeys = true, arraykeys = true}))
        end
    end
    game.write_file(Changes.get_file_path('Changes/global.lua'), 'return ' .. inspect(global._changes or nil, {longkeys = true, arraykeys = true}))
end

return Changes
