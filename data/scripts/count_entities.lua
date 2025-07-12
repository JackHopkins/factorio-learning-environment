local player = game.players["arg1"]
local entity="arg2"

local surface=player.surface
local count=0
local out=0
for key, ent in pairs(surface.find_entities_filtered({force=player.force})) do
	if string.find(ent.name,entity) then
		count=count+1
	end
	out=out+1
end
rcon.print(out)
rcon.print(count)