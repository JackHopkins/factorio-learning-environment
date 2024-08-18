local player = game.players[arg1]
--rcon.print(player.get_main_inventory.clear())
--rcon.print(player.get_main_inventory().get_insertable_count())
rcon.print(player.get_main_inventory().insert{name="arg2", count=100})
--rcon.print(player.force.item_production_statistics.get_input_count('arg2'))

--player.get_main_inventory().insert({name="arg2", count=arg3})
--rcon.print(player.get_main_inventory().get_item_count("arg2"))
--rcon.print(dump(player.get_main_inventory().get_contents()))