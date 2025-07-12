local player = game.players[arg1]
local surface=player.surface

surface.create_entity({name = "character", position = {player.position.x + 5, player.position.y}, force = game.forces.player})
rcon.print("hi", #surface.find_entities_filtered({force=player.force, name="character"}))