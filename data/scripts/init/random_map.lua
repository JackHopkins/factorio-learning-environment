local player = game.players[arg1]
local surface=player.surface
local ore=nil
local size=arg2
local density=arg3
for y=-size, size do
	for x=-size, size do
		a=(size+1-math.abs(x))*10
		b=(size+1-math.abs(y))*10
		if a<b then
			ore=math.random(a*density-a*(density-8), a*density+a*(density-8))
		end
		if b<a then
			ore=math.random(b*density-b*(density-8), b*density+b*(density-8))
		end
		--if surface.get_tile(player.position.x+x, player.position.y+y).collides_with("ground-tile") then
		--	surface.create_entity({name="stone", amount=ore, position={player.position.x+x, player.position.y+y}})
		--end
	end
end