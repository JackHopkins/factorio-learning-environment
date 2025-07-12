-- Initialize the player's inventory
local function init_player_inventory(player)
	player.clear_items_inside()
	player.insert{name="iron-plate", count=8}
	player.insert{name="pistol", count=1}
	player.insert{name="firearm-magazine", count=10}
	player.insert{name="burner-mining-drill", count = 1}
	player.insert{name="stone-furnace", count = 1}
end

local function init_player(player)
	local char_entity = player.surface.create_entity({name="player", position={0,0}, force=player.force})
	player.character = char_entity
	player.surface.always_day = true
	player.game_view_settings.update_entity_selection = false
	player.game_view_settings.show_entity_info = true
	player.game_view_settings.show_controller_gui = true
	init_player_inventory(player)
end

init_player(game.players[arg1])