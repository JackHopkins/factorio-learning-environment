local i = 0
for c in game.players[1].surface.get_chunks() do
    i= i + game.players[1].surface.count_entities_filtered({area={{c.x * 32, c.y * 32}, {c.x * 32 + 32, c.y * 32 + 32}}, name="arg1"})
end
rcon.print(i)