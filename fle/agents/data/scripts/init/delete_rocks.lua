local surface = game.player.surface
for c in surface.get_chunks() do
 for key, entity in pairs(surface.find_entities_filtered({area={{c.x * 32, c.y * 32}, {c.x * 32 + 32, c.y * 32 + 32}}, name = "ORE/OBJECT"})) do
     entity.destroy()
 end
end