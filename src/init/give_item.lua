local player = game.players[arg1]
local name = arg2
rcon.print(player.get_main_inventory().insert{name=name:gsub("_", "-"), count=arg3})