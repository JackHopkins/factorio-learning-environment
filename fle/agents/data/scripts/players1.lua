function dump(o)
   if type(o) == 'userdata' then
      return getmetatable(o)
   elseif type(o) == 'LuaCustomTable' then
      for k,v in pairs(o) do
            game.player.print(p.name); end
   elseif type(o) == 'table' then
      local s = '{ '
      for k,v in pairs(o) do
         if type(k) ~= 'number' then k = '"'..k..'"' end
         s = s .. '['..k..'] = ' .. dump(v) .. ','
      end
      return s .. '} '
   else
      return tostring(o)
   end
end

local player = game.players[arg1]
rcon.print(player)