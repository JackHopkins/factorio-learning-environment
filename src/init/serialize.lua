-- Library for serializing items in Factorio
-- Based on code from playerManager and trainTeleports

global.utils = {}

local function version_to_table(version)
	local t = {}
	for p in string.gmatch(version, "%d+") do
		t[#t + 1] = tonumber(p)
	end
	return t
end

-- 0.17 compatibility
local supports_bar, get_bar, set_bar, version
if (pcall(function() local mods = script.active_mods end)) then
	supports_bar = "supports_bar"
	get_bar = "get_bar"
	set_bar = "set_bar"
	version = version_to_table(script.active_mods.base)
else
	supports_bar = "hasbar"
	get_bar = "getbar"
	set_bar = "setbar"
	version = version_to_table("0.17.69")
end

-- returns true if the game version is greater than or equal to the given version
local function version_ge(comp)
	comp = version_to_table(comp)
	for i=1, 3 do
		if comp[i] > version[i] then
			return false
		elseif comp[i] < version[i] then
			return true
		end
	end
	return true
end

local has_create_grid = version_ge("1.1.7")


-- Equipment Grids are serialized into an array of equipment entries
-- where ench entry is a table with the following fields:
--	 n: name
--	 p: position (array of 2 numbers corresponding to x and y)
--	 s: shield (optional)
--	 e: energy (optional)
-- If the equipment is a burner the following is also present:
--	 i: burner inventory
--	 r: result inventory
--	 b: curently burning (optional)
--	 f: remaining_burning_fuel (optional)
global.utils.serialize_equipment_grid = function(grid)
	local serialized = {}
	local processed = {}
	for y = 0, grid.height - 1 do
		for x = 0, grid.width - 1 do
			local equipment = grid.get({x, y})
			if equipment ~= nil then
				local pos = equipment.position
				local combined_pos = pos.x + pos.y * grid.width + 1
				if not processed[combined_pos] then
					processed[combined_pos] = true
					local entry = {
						n = equipment.name,
						p = {pos.x, pos.y},
					}
					if equipment.shield > 0 then entry.s = equipment.shield end
					if equipment.energy > 0 then entry.e = equipment.energy end
					-- TODO: Test with Industrial Revolution
					if equipment.burner then
						local burner = equipment.burner
						entry.i = global.utils.serialize_inventory(burner.inventory)
						entry.r = global.utils.serialize_inventory(burner.burnt_result_inventory)
						if burner.curently_burning then
							entry.b = {}
                            global.utils.serialize_item_stack(burner.curently_burning, entry.b)
							entry.f = burner.remaining_burning_fuel
						end
					end
					table.insert(serialized, entry)
				end
			end
		end
	end
	return serialized
end

global.utils.deserialize_equipment_grid = function(grid, serialized)
	grid.clear()
	for _, entry in ipairs(serialized) do
		local equipment = grid.put({
			name = entry.n,
			position = entry.p,
		})
		if equipment then
			if entry.s then equipment.shield = entry.s end
			if entry.e then equipment.energy = entry.e end
			if entry.i then
				if entry.b then global.utils.deserialize_item_stack(burner.currently_burning, entry.b) end
				if entry.f then burner.remaining_burning_fuel = entry.f end
				global.utils.deserialize_inventory(burner.burnt_result_inventory, entry.r)
				global.utils.deserialize_inventory(burner.inventory, entry.i)
			end
		end
	end
end

-- Item stacks are serialized into a table with the following fields:
--	 n: name
--	 c: count
--	 h: health (optional)
--	 d: durability (optional)
--	 a: ammo count (optional)
--	 l: label (optional)
--	 g: equipment grid (optional)
--	 i: item inventory (optional)
-- If the item stack is exportable it has the following property instead
--	 e: export string
-- Label is a table with the following fields:
--	 t: label text (optional)
--	 c: color (optional)
--	 a: allow manual label change
global.utils.serialize_item_stack = function(slot, entry)
	if
		slot.is_blueprint
		or slot.is_blueprint_book
		or slot.is_upgrade_item
		or slot.is_deconstruction_item
		or slot.is_item_with_tags
	then
		local call_success, call_return = pcall(slot.export_stack)
		if not call_success then
			print("Error: '" .. call_return .. "' thrown exporting '" .. slot.name .. "'")
		else
			entry.e = call_return
		end

		return
	end

	entry.n = slot.name
	entry.c = slot.count
	if slot.health < 1 then entry.h = slot.health end
	if slot.durability then entry.d = slot.durability end
	if slot.type == "ammo" then entry.a = slot.ammo end
	if slot.is_item_with_label then
		local label = {}
		if slot.label then label.t = slot.label end
		if slot.label_color then label.c = slot.label_color end
		label.a = slot.allow_manual_label_change
		entry.l = label
	end

	if slot.grid then
		entry.g = global.utils.serialize_equipment_grid(slot.grid)
	end

	if slot.is_item_with_inventory then
		local sub_inventory = slot.get_inventory(defines.inventory.item_main)
		entry.i = global.utils.serialize_inventory(sub_inventory)
	end
end

global.utils.deserialize_item_stack = function(slot, entry)
	if entry.e then
		local success = slot.import_stack(entry.e)
		if success == 1 then
			print("Error: import of '" .. entry.e .. "' succeeded with errors")
		elseif success == -1 then
			print("Error: import of '" .. entry.e .. "' failed")
		end

		return
	end

	local item_stack = {
		name = entry.n,
		count = entry.c,
	}
	if entry.h then item_stack.health = entry.h end
	if entry.d then item_stack.durability = entry.d end
	if entry.a then item_stack.ammo = entry.a end

	local call_success, call_return = pcall(slot.set_stack, item_stack)
	if not call_success then
		print("Error: '" .. call_return .. "' thrown setting stack ".. serpent.line(entry))

	elseif not call_return then
		print("Error: Failed to set stack " .. serpent.line(entry))

	else
		if entry.l then
			-- TODO test this with AAI's unit-remote-control
			local label = entry.l
			if label.t then slot.label = label.t end
			if label.c then slot.label_color = label.c end
			slot.allow_manual_label_change = label.a
		end
		if entry.g then
			if slot.grid then
				global.utils.deserialize_equipment_grid(slot.grid, entry.g)
			elseif slot.type == "item-with-entity-data" and has_create_grid then
				slot.create_grid()
				global.utils.deserialize_equipment_grid(slot.grid, entry.g)
			else
				print("Error: Attempt to deserialize equipment grid on an unsupported entity")
			end
		end
		if entry.i then
			local sub_inventory = slot.get_inventory(defines.inventory.item_main)
			global.utils.deserialize_inventory(sub_inventory, entry.i)
		end
	end
end

-- Inventories are serialized into a table with the following fields:
--	 i: array of item stack or exportable item entries
--	 b: bar position (optional)
-- Each item entry has the following fields
--	 s: index (optional, equals to previous plus one if not present)
--	 r: repeat count (optional)
--	 f: slot filter (optional)
-- Pluss all the fields for item stacks (see deserialize_item_stack)
-- It's also possible that the slot is empty but has a slot filter.
global.utils.serialize_inventory = function(inventory)
	local serialized = {}
	if inventory[supports_bar]() and inventory[get_bar]() <= #inventory then
		serialized.b = inventory[get_bar]()
	end

	serialized.i = {}
	local previous_index = 0
	local previous_serialized = nil
	for i = 1, #inventory do
		local item = {}
		local slot = inventory[i]
		if inventory.supports_filters() then
			item.f = inventory.get_filter(i)
		end

		if slot.valid_for_read then
			global.utils.serialize_item_stack(slot, item)
		end

		if item.n or item.f or item.e then
			local item_serialized = game.table_to_json(item)
			if item_serialized == previous_serialized then
				local previous_item = serialized.i[#serialized.i]
				previous_item.r = (previous_item.r or 0) + 1
				previous_index = i

			else
				if i ~= previous_index + 1 then
					item.s = i
				end

				previous_index = i
				previous_serialized = item_serialized
				table.insert(serialized.i, item)
			end

		else
			-- Either an empty slot or serilization failed
			previous_index = 0
			previous_serialized = nil
		end
	end

	return serialized
end

global.utils.deserialize_inventory = function(inventory, serialized)
	if serialized.b and inventory[supports_bar]() then
		inventory[set_bar](serialized.b)
	end

	local last_slot_index = 0
	for _, entry in ipairs(serialized.i) do
		local base_index = entry.s or last_slot_index + 1

		local repeat_count = entry.r or 0
		for offset = 0, repeat_count do
			-- XXX what if the inventory is smaller on this instance?
			local index = base_index + offset
			local slot = inventory[index]
			if entry.f then
				local call_success, call_return = pcall(inventory.set_filter, index, entry.f)
				if not call_success then
					print("Error: '" .. call_return .. "' thrown setting filter " .. entry.f)

				elseif not call_return then
					print("Error: Failed to set filter " .. entry.f)
				end
			end

			if entry.n or entry.e then
                global.utils.deserialize_item_stack(slot, entry)
			end
		end
		last_slot_index = base_index + repeat_count
	end
end

global.utils.serialize_recipe = function(recipe)
    local serialized = {
        name = "\"" .. recipe.name .. "\"",
        category = "\"" .. recipe.category .. "\"",
        enabled = recipe.enabled,
        --hidden = recipe.hidden,
        energy = recipe.energy,
        --order = recipe.order,
        --group = recipe.group and "\"" .recipe.group.name.. "\"" or nil,
        --subgroup = recipe.subgroup and "\"" .recipe.subgroup.name.. "\"" or nil,
        --force = recipe.force and recipe.force.name or nil,
    }

    -- Serialize ingredients
    serialized.ingredients = {}
    for _, ingredient in pairs(recipe.ingredients) do
        table.insert(serialized.ingredients, {name = "\""..ingredient.name.."\"", type = "\""..ingredient.type.."\"", amount = ingredient.amount})
    end

    -- Serialize products
    serialized.products = {}
    for _, product in pairs(recipe.products) do
        local product_table = {name = "\""..product.name.."\"", type = "\""..product.type.."\"", amount = product.amount}
        if product.probability then product_table.probability = product.probability end
        table.insert(serialized.products, product_table)
    end

    return serialized
end

global.utils.serialize_fluidbox = function(fluidbox)
    local serialized = {
        owner = fluidbox.owner and fluidbox.owner.name or nil,
        length = #fluidbox,
    }

    -- Serialize each fluid box
    serialized.fluidboxes = {}
    for i = 1, #fluidbox do
        local box = fluidbox[i]
        local prototype = fluidbox.get_prototype(i)
        local connections = fluidbox.get_connections(i)
        local filter = fluidbox.get_filter(i)
        local flow = fluidbox.get_flow(i)
        local locked_fluid = fluidbox.get_locked_fluid(i)
        local fluid_system_id = fluidbox.get_fluid_system_id(i)

        local serialized_box = {
            prototype = prototype and prototype.name or nil,
            capacity = fluidbox.get_capacity(i),
            connections = {},
            filter = filter,
            flow = flow,
            locked_fluid = locked_fluid,
            fluid_system_id = fluid_system_id,
        }

        -- Serialize fluid
        if box then
            serialized_box.fluid = {
                name = box.name,
                amount = box.amount,
                temperature = box.temperature,
            }
        end

        -- Serialize connections
        for _, connection in pairs(connections) do
            table.insert(serialized_box.connections, connection.owner and connection.owner.name or nil)
        end

        serialized.fluidboxes[i] = serialized_box
    end

    return serialized
end

local function get_offshore_pump_pipe_position(entity)
	local x, y = entity.position.x, entity.position.y
	local orientation = entity.orientation * 8

	game.print("Getting pipe position for offshore pump with orientation: " .. orientation)
	local dx, dy
	if orientation == defines.direction.north then
		dx, dy = 0, 1
	elseif orientation == defines.direction.south then
		dx, dy = 0, -1
	elseif orientation == defines.direction.east then
		dx, dy = -1, 0
	elseif orientation == defines.direction.west then
		dx, dy = 1, 0
	end

	if dy == nil then
		return { {x = x, y = y - 1} }
	end

	return { {x = x + dx, y = y + dy} }
end

local function get_pipe_positions(entity)
    local x, y = entity.position.x, entity.position.y
    local orientation = entity.orientation
	local entity_prototype = game.entity_prototypes[entity.name]
	game.print("Getting pipe position for entity: " .. entity.name .. " with orientation: " .. orientation)
    local dx, dy = 0, 0
	local offsetx, offsety = 0, 0
    if orientation == 0 or orientation == defines.direction.north then
        dx, dy = 0, -1
		--offsetx, offsety = 0, 0
    elseif orientation == 0.25 or orientation == defines.direction.east then
        dx, dy = 1, 0
		--offsetx, offsety = -0.5, 0
    elseif orientation == 0.5 or orientation == defines.direction.south then
        dx, dy = 0, -1
		--offsetx, offsety = 0, -0.5
    elseif orientation == 0.75 or orientation == defines.direction.west then
        dx, dy = 1, 0
		--offsetx, offsety = 0, 0
    else
        -- Log detailed information about the unexpected orientation
        local orientation_info = string.format(
            "Numeric value: %s, Type: %s, Defines values: N=%s, E=%s, S=%s, W=%s",
            tostring(orientation),
            type(orientation),
            tostring(defines.direction.north),
            tostring(defines.direction.east),
            tostring(defines.direction.south),
            tostring(defines.direction.west)
        )
        error(string.format(
            "Unexpected orientation for entity: %s at position: %s. Orientation info: %s",
            entity.name,
            serpent.line(entity.position),
            orientation_info
        ))
    end
	local height = entity_prototype.tile_height/2
	game.print("Height: " .. height)
    local pipe_positions = {
        {x = x + (height*dx) + offsetx, y = y + (height*dy) + offsety},
        {x = x - (height*dx) + offsetx, y = y - (height*dy) + offsety}
    }

    return pipe_positions
end

function get_boiler_pipe_positions(entity)
    local x, y = entity.position.x, entity.position.y
    local orientation = entity.orientation

    local dx, dy
    if orientation == defines.direction.north then
        dx, dy = 1, 0
    elseif orientation == defines.direction.south then
        dx, dy = -1, 0
    elseif orientation == defines.direction.east then
        dx, dy = 0, 1
    elseif orientation == defines.direction.west then
        dx, dy = 0, -1
    end
	local water_inputs = {}
	water_inputs[1] = {x = x + 1*dx, y = y + 1*dy}
	water_inputs[2] = {x = x - 1*dx, y = y - 1*dy}

    local pipe_positions = {
        water_inputs = water_inputs,
        steam_output = {x = x, y = y - 1*dy}
    }

    return pipe_positions
end

function add_burner_inventory(serialized, burner)
	local fuel_inventory = burner.inventory
	if fuel_inventory and #fuel_inventory > 0 then
		serialized.fuel_inventory = {}
		serialized.remaining_fuel = 0
		for i = 1, #fuel_inventory do
			local item = fuel_inventory[i]
			if item and item.valid_for_read then
				table.insert(serialized.fuel_inventory, {name = item.name, count = item.count})
				serialized.remaining_fuel = serialized.remaining_fuel + item.count
			end
		end
	end
end

function get_entity_direction(entity, direction)
	--game.print("Getting direction: " .. entity .. " with direction: " .. direction)
	game.print(direction)

	-- If direction is nil then return north
	if direction == nil then
		return defines.direction.north
	end

	local prototype = game.entity_prototypes[entity]
	game.print(prototype)
	local cardinals = {
		defines.direction.north,
		defines.direction.east,
		defines.direction.south,
		defines.direction.west
	}
	if prototype and (prototype.name == "boiler" or prototype.type == "generator") then
		if direction == 0 then
			return defines.direction.north
		elseif direction == 1 then
			return defines.direction.east
		elseif direction == 2 then
			return defines.direction.south
		else
			return defines.direction.west
		end
	elseif prototype and prototype.name == "offshore-pump" then
		if direction == 2 then
			return defines.direction.north
		elseif direction == 3 then
			return defines.direction.east
		elseif direction == 0 then
			return defines.direction.south
		else
			return defines.direction.west
		end
	elseif prototype and prototype.type == "transport-belt" then
			game.print("Transport belt direction: " .. direction)
			if direction == 0 then
				return defines.direction.north
			elseif direction == 3 then
				return defines.direction.west
			elseif direction == 2 then
				return defines.direction.south
			else
				return defines.direction.east
			end
		elseif prototype and prototype.type == "inserter" then
			--return cardinals[(direction % 4)]
			if direction == 0 then
				return defines.direction.south
			elseif direction == 1 then
				return defines.direction.west
			elseif direction == 2 then
				return defines.direction.north
			else
				return defines.direction.east
			end
		elseif prototype.type == "mining-drill" then
			if direction == 1 then
				return cardinals[2]
			elseif direction == 2 then
				return cardinals[3]
			elseif direction == 3 then
				return cardinals[4]
			else
				return cardinals[1]
			end
		else
			return direction
		end

		game.print("Returning direction: ")
		return direction
	end

function get_inverse_entity_direction(entity, factorio_direction)
	local prototype = game.entity_prototypes[entity]

	if not factorio_direction then
		return 0  -- Assuming 0 is the default direction in your system
	end

	if prototype and prototype.name == "offshore-pump" then
		if factorio_direction == defines.direction.west then
			return defines.direction.east
		elseif factorio_direction == defines.direction.east then
			return defines.direction.west
		elseif factorio_direction == defines.direction.south then
			return defines.direction.north
		else
			return defines.direction.south
		end
	end
	game.print("Getting inverse direction: " .. entity .. " with direction: " .. factorio_direction)
	if prototype and prototype.type == "inserter" then
		if factorio_direction == defines.direction.south then
			return defines.direction.north
		elseif factorio_direction == defines.direction.west then
			return defines.direction.east
		elseif factorio_direction == defines.direction.north then
			return defines.direction.south
		elseif factorio_direction == defines.direction.east then
			return defines.direction.west
		else
			return -1
		end
	--elseif prototype and prototype.type == "mining-drill" then
	--	if factorio_direction == defines.direction.east then
	--		return defines.direction.east
	--	elseif factorio_direction == defines.direction.south then
	--		return defines.direction.south
	--	elseif factorio_direction == defines.direction.west then
	--		return defines.direction.west
	--	else  -- north
	--		return defines.direction.north
	--	end
	else
		game.print("Returning direction: " .. math.floor(factorio_direction / 2) .. ', '.. factorio_direction)
		-- For other entity types, convert Factorio's direction to 0-3 range
		return factorio_direction
		--return factorio_direction
	end
end

global.utils.get_entity_direction = get_entity_direction

global.utils.serialize_entity = function(entity)

	if entity == nil then
		return {}
	end
	--game.print("Serializing entity: " .. entity.name .. " with direction: " .. entity.direction)
	local direction = entity.direction

	-- This is needed because the entity.direction on the map is not always the actual direction
	-- (e.g inserters and offshore pumps have opposite directions on the map to the actual cardinal)
	--if entity.direction ~= nil then
	--	direction = get_inverse_entity_direction(entity.name, entity.direction/2)*2--get_inverse_entity_direction(entity.name, entity.direction)
	--end

	--if direction == nil then
	direction = get_entity_direction(entity.name, entity.direction)
	--end
	game.print(direction)
	game.print("Serializing entity: " .. entity.name .. " with direction: " .. direction)
	local serialized = {
		name = "\""..entity.name.."\"",
		position = entity.position,
		direction = direction,
		health = entity.health,
		energy = entity.energy,
		type = "\""..entity.type.."\""
	}

	if entity.grid then
		serialized.grid = global.utils.serialize_equipment_grid(entity.grid)
	end

	if entity.get_inventory then
		for i = 1, #defines.inventory do
			local inventory = entity.get_inventory(i)
			if inventory and #inventory > 0 then
				serialized["inventory_" .. i] = global.utils.serialize_inventory(inventory)
			end
		end
	end

	-- Add dimensions of the entity
	local prototype = game.entity_prototypes[entity.name]
	local collision_box = prototype.collision_box
	serialized.dimensions = {
		width = math.abs(collision_box.right_bottom.x - collision_box.left_top.x),
		height = math.abs(collision_box.right_bottom.y - collision_box.left_top.y),
	}

	-- Add input and output locations if the entity is a transport belt
	if entity.type == "transport-belt" then
		-- input_position is the position upstream of the belt
		--local direction = entity.direction
		local x, y = entity.position.x, entity.position.y
		if entity.direction == defines.direction.north then
			y = y - 1
		elseif entity.direction == defines.direction.south then
			y = y + 1
		elseif entity.direction == defines.direction.east then
			x = x + 1
		elseif entity.direction == defines.direction.west then
			x = x - 1
		end

		serialized.input_position = {x = x, y = y}

		-- output_position is the position downstream of the belt
		local x, y = entity.position.x, entity.position.y
		if entity.direction == defines.direction.north then
			y = y + 1
		elseif entity.direction == defines.direction.south then
			y = y - 1
		elseif entity.direction == defines.direction.east then
			x = x - 1
		elseif entity.direction == defines.direction.west then
			x = x + 1
		end

		serialized.output_position = {x = x, y = y}
	end

	-- Add input and output locations if the entity is an inserter
	if entity.type == "inserter" then
		serialized.pickup_position = entity.pickup_position
		serialized.drop_position = entity.drop_position

		-- if pickup_position is nil, compute it from the entity's position and direction
		if not serialized.pickup_position then
			--local direction = entity.direction
			local x, y = entity.position.x, entity.position.y
			if entity.direction == defines.direction.north then
				serialized.pickup_position = {x = x, y = y - 1}
			elseif entity.direction == defines.direction.south then
				serialized.pickup_position = {x = x, y = y + 1}
			elseif entity.direction == defines.direction.east then
				serialized.pickup_position = {x = x + 1, y = y}
			elseif entity.direction == defines.direction.west then
				serialized.pickup_position = {x = x - 1, y = y}
			end
		end

		local burner = entity.burner
		if burner then
			add_burner_inventory(serialized, burner)
		end
	end

	-- Add input and output locations if the entity is a splitter
	if entity.type == "splitter" then
		serialized.input_position = entity.input_position
		serialized.output_position = entity.output_position
	end

	-- Add input and output locations if the entity is a pipe
	if entity.type == "pipe" then
		serialized.connections = {}
		for _, connection in pairs(entity.fluidbox.get_pipe_connections(1)) do
			table.insert(serialized.connections, connection.position)
		end
	end

	-- Add input and output locations if the entity is a pipe-to-ground
	if entity.type == "pipe-to-ground" then
		serialized.input_position = entity.fluidbox.get_connections(1)[1].position
		serialized.output_position = entity.fluidbox.get_connections(2)[1].position
	end

	-- Add input and output locations if the entity is a pump
	if entity.type == "pump" then
		serialized.input_position = entity.fluidbox.get_connections(1)[1].position
		serialized.output_position = entity.fluidbox.get_connections(2)[1].position
	end

	-- Add input and output locations if the entity is a offshore pump
	if entity.type == "offshore-pump" then
		local burner = entity.burner
		if burner then
			add_burner_inventory(serialized, burner)
		end
	end

	-- Add tile dimensions of the entity
	serialized.tile_dimensions = {
		tile_width = prototype.tile_width,
		tile_height = prototype.tile_height,
	}

	-- Add drop position if the entity is a mining drill
	--game.print("Entity type: " .. entity.type)
	--game.print("Entity has burner: " .. tostring(entity.burner ~= nil))
	--game.print("Burner is burning: " .. tostring(entity.burner and entity.burner.currently_burning ~= nil))

	if entity.type == "mining-drill" then
		serialized.drop_position = {
			x = entity.drop_position.x,
			y = entity.drop_position.y
		}
		game.print("Mining drill drop position: " .. serpent.line(serialized.drop_position))
		local burner = entity.burner
		if burner then
			add_burner_inventory(serialized, burner)
		end
	end

	-- Add recipes if the entity is a crafting machine
	if entity.type == "assembling-machine" or entity.type == "furnace" then
		if entity.get_recipe() then
			serialized.recipe = global.utils.serialize_recipe(entity.get_recipe())
		end
	end

	-- Add fluid input point if the entity is a boiler
	if entity.type == "boiler" then
		local burner = entity.burner
		if burner then
			add_burner_inventory(serialized, burner)
		end

		--local direction = entity.direction
		local x, y = entity.position.x, entity.position.y

		if entity.direction == defines.direction.north then
			game.print("Boiler direction is north")
			serialized.connection_points = {{x = x - 2, y = y + 0.5}, {x = x + 2, y = y + 0.5}}
			serialized.steam_output_point = {x = x, y = y - 2}
		elseif entity.direction == defines.direction.south then
			game.print("Boiler direction is south")
			serialized.connection_points = {{x = x - 2, y = y - 0.5}, {x = x + 2, y = y - 0.5}}
			serialized.steam_output_point = {x = x, y = y + 2}
		elseif entity.direction == defines.direction.east then
			game.print("Boiler direction is east")
			serialized.connection_points = {{x = x - 0.5, y = y - 2}, {x = x - 0.5, y = y + 2}}
			serialized.steam_output_point = {x = x + 2, y = y}
		elseif entity.direction == defines.direction.west then
			game.print("Boiler direction is west")
			serialized.connection_points = {{x = x + 0.5, y = y - 2}, {x = x + 0.5, y = y + 2}}
			serialized.steam_output_point = {x = x - 2, y = y}
		end

		--serialized.fluid_input_point = entity.fluidbox.get_connections(1)[1].position
	end

	if entity.type == "generator" then
		serialized.connection_points = get_pipe_positions(entity)

		--create_beam_point(game.players[1], serialized.connection_points[1])
		--create_beam_point(game.players[1], serialized.connection_points[2])
	end

	-- Add fuel and input ingredients if the entity is a furnace or burner
	if entity.type == "furnace" or entity.type == "burner" then
		local burner = entity.burner
		if burner then
			add_burner_inventory(serialized, burner)
		end
		local input_inventory = entity.get_inventory(defines.inventory.furnace_source)
		if input_inventory and #input_inventory > 0 then
			serialized.input_inventory = {}
			for i = 1, #input_inventory do
				local item = input_inventory[i]
				if item and item.valid_for_read then
					table.insert(serialized.input_inventory, {name = item.name, count = item.count})
				end
			end
		end
	end

	-- Add fluid box if the entity is an offshore pump
	if entity.type == "offshore-pump" then
		local fluid_box = entity.fluidbox
		if fluid_box and #fluid_box > 0 then
			serialized.fluid_box = {}
			for i = 1, #fluid_box do
				local fluid = fluid_box[i]
				if fluid then
					table.insert(serialized.fluid_box, {name = fluid.name, amount = fluid.amount, temperature = fluid.temperature})
				end
			end
		end
		serialized.connection_points = get_offshore_pump_pipe_position(entity)
	end

	serialized.direction = get_inverse_entity_direction(entity.name, entity.direction) --api_direction_map[entity.direction]


	return serialized
end
