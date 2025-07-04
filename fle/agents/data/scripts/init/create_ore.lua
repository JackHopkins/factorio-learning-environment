local player = game.players[arg1]
local surface = player.surface;
for y=-arg2, arg2 do
    for x=-arg2, arg2 do
      surface.create_entity({name="arg4", amount=arg3, position={player.position.x+x, player.position.y+y}})
    end
end