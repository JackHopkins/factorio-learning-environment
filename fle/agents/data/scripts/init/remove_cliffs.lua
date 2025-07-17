for _, v in pairs(game.player.surface.find_entities_filtered{type="cliff"}) do
  v.destroy()
end