-- Observe.lua
global.actions.collision_mask = function(player_index, localBoundingBox)
    local player = game.players[player_index]
    response = find_passable_tiles(player, localBoundingBox)
    rcon.print(player.position)
    return response
end