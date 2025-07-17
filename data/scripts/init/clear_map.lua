local player = game.players[arg1]
local surface=player.surface

for _, entity in ipairs(player.surface.find_entities_filtered{ area={{player.position.x-arg2,
player.position.y-arg2}, {player.position.x+arg2, player.position.y+arg2}}, type="resource"}) do
entity.destroy()
end