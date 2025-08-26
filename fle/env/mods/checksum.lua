checksum = {}

if not global.__lua_script_checksums then
    global.__lua_script_checksums = {}
end

checksum.get_lua_script_checksums = function()
    return game.table_to_json(global.__lua_script_checksums)
end

checksum.set_lua_script_checksum = function(name, checksum)
    global.__lua_script_checksums[name] = checksum
end

checksum.clear_lua_script_checksums = function()
    global.__lua_script_checksums = {}
end

-- return checksum