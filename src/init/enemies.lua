game.forces["enemy"].kill_all_units()  -- Removes all biters
game.map_settings.enemy_expansion.enabled = false  -- Stops biters from expanding
game.map_settings.enemy_evolution.enabled = false  -- Stops biters from evolving
local surface = game.surfaces[1]
for _, entity in pairs(surface.find_entities_filtered({type="unit-spawner"})) do
    entity.destroy()
end
