local function safe_json_to_table(json)
	if not json or json == '' then return {} end
	local ok, result = pcall(function()
		return helpers.json_to_table(json)
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

storage.actions.reset = function(inventories_json, reset_position, all_technologies_researched, clear_entities)
	-- Clear alerts, reset game state, and production stats
	game.reset_game_state()
	storage.alerts = {}
	storage.actions.reset_production_stats()
	storage.elapsed_ticks = 0

	local inventories = safe_json_to_table(inventories_json)

	-- Re-generate resources per agent (mirrors instance _reset)
	if storage.agent_characters then
		for i, character in pairs(storage.agent_characters) do
			-- Only process valid characters
			if character and character.valid then
				storage.actions.regenerate_resources(i)
				storage.actions.clear_walking_queue(i)

				if reset_position then
					local y_offset = (tonumber(i) or 1) - 1
					character.teleport{ x = 0, y = y_offset * 2 }
				end

				-- Clear entities around each agent and reset inventories
				if clear_entities then
					storage.actions.clear_entities(i)
				end

				local inv_table = get_inventory_for_index(inventories, i)
				local inv_json = helpers.table_to_json(inv_table)
				storage.actions.set_inventory(i, inv_json)
			end
		end
	end

	-- Research handling - need to check for valid character first
	local valid_character = nil
	if storage.agent_characters then
		for _, character in pairs(storage.agent_characters) do
			if character and character.valid then
				valid_character = character
				break
			end
		end
	end

	if valid_character then
		if all_technologies_researched == true then
			valid_character.force.research_all_technologies()
		else
			valid_character.force.reset()
		end
	elseif all_technologies_researched == true or all_technologies_researched == false then
		-- If no valid characters but technology reset was requested,
		-- try to use the default force
		local force = game.forces["player"] or game.forces[1]
		if force then
			if all_technologies_researched == true then
				force.research_all_technologies()
			else
				force.reset()
			end
		end
	end

	return 1
end