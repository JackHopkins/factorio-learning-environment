local player = game.players[arg1]
player.teleport({arg2, arg3})
rcon.print(player.position.x .. ", " .. player.position.y)