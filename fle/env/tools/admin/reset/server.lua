local function safe_json_to_table(json)
	if not json or json == '' then return {} end
	local ok, result = pcall(function()
		return game.json_to_table(json)
	end)
	if ok and type(result) == 'table' then return result end
	return {}
end

local function get_inventory_for_index(inventories, index)
	if type(inventories) ~= 'table' then return {} end
	-- Support both array-style and map-style inputs
	local inv = inventories[index]
	if inv == nil then
		inv = inventories[tostring(index)]
	end
	if type(inv) ~= 'table' then return {} end
	return inv
end

global.actions.reset = function(inventories_json, reset_position, all_technologies_researched, clear_entities)

	-- Clear alerts, reset game state, and production stats
	game.reset_game_state()
	global.alerts = {}
	global.actions.reset_production_stats()
	global.elapsed_ticks = 0

	local inventories = safe_json_to_table(inventories_json)

	-- Re-generate resources per agent (mirrors instance _reset)
	if global.agent_characters then
		for i, character in pairs(global.agent_characters) do
			global.actions.regenerate_resources(i)
			global.actions.clear_walking_queue(i)

			if reset_position and character and character.valid then
				local y_offset = (tonumber(i) or 1) - 1
				character.teleport{ x = 0, y = y_offset * 2 }
			end

			-- Clear entities around each agent and reset inventories
			if clear_entities then
				global.actions.clear_entities(i)
			end

			local inv_table = get_inventory_for_index(inventories, i)
			local inv_json = game.table_to_json(inv_table)
			global.actions.set_inventory(i, inv_json)
		end
	end

	-- Research handling
	if all_technologies_researched == true then
		global.agent_characters[1].force.research_all_technologies()
	else
		global.agent_characters[1].force.reset()
	end

	return 1
end

