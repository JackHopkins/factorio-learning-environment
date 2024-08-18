local Game = require('__stdlib__/stdlib/game')
local Event = require('__stdlib__/stdlib/event/event')
local Player = require('__stdlib__/stdlib/event/player')

--local player2, player_data2 = Player.get(2)
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


Event.on_init(
    function(event)
        Player.register_events(true)

        local player1, playerdata = Player.init(1, true)
        --Player.init('dummy3')
        --Player.init('dummy4')
        print("Getting player 1", player1, playerdata)
        global.players[1] = player1


        --print(dump(global.players))
        --game.players[1] = player1
        --table.insert(global.players, player1)
        print("Global players", global.players[1], #global.players)
        print("Game players", game.players[1], #game.players)
        print(Game.get_player(1))
        --player1.create_character()
        --print("Creating character for player 1")

    end
)
Event.register(defines.events.on_player_created,
    function(event)
        local player1 = Player.get(1)
        print("Getting player 1", player1)
    end
)

Event.on_configuration_changed(
    function(event)
        --Player.init('dummy1')
        --Player.init('dummy2')

        Player.register_events()



    end
)
--Event.register(defines.events.on_init, function(event) Player.init(1) end )