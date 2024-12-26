local player = game.players[arg1]
local surface = player.surface

local tiles = {}
for x = -100, 100 do
    for y = -100, 100 do
        local current_tile = surface.get_tile(x, y)
        if current_tile.name == "lab-dark-1" or current_tile.name == "lab-dark-2" then
            table.insert(tiles, {name = "grass-1", position = {x, y}})
        end
    end
end

surface.set_tiles(tiles)