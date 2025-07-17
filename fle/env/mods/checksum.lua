if not global.__lua_script_checksums then
    global.__lua_script_checksums = {}
end

global.get_lua_script_checksums = function()
    return game.table_to_json(global.__lua_script_checksums)
end

global.set_lua_script_checksum = function(name, checksum)
    global.__lua_script_checksums[name] = checksum
end

global.clear_lua_script_checksums = function()
    global.__lua_script_checksums = {}
end