-- Library for serializing items in Factorio
-- Based on code from playerManager and trainTeleports

if not global.utils then
    global.utils = {}
end

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

-- Add this helper function at the top level
local function is_fluid_handler(entity_type)
    return entity_type == "boiler" or
           entity_type == "offshore-pump" or
           entity_type == "pump" or
           entity_type == "generator" or
           entity_type == "oil-refinery" or
    	   entity_type == "chemical-plant"
           --entity_type == "pipe" or
           --entity_type == "pipe-to-ground"
end


-- Equipment Grids are serialized into an array of equipment entries
-- where ench entry is a table with the following fields:
--   n: name
--   p: position (array of 2 numbers corresponding to x and y)
--   s: shield (optional)
--   e: energy (optional)
-- If the equipment is a burner the following is also present:
--   i: burner inventory
--   r: result inventory
--   b: curently burning (optional)
--   f: remaining_burning_fuel (optional)
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
--   n: name
--   c: count
--   h: health (optional)
--   d: durability (optional)
--   a: ammo count (optional)
--   l: label (optional)
--   g: equipment grid (optional)
--   i: item inventory (optional)
-- If the item stack is exportable it has the following property instead
--   e: export string
-- Label is a table with the following fields:
--   t: label text (optional)
--   c: color (optional)
--   a: allow manual label change
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

----- DEPRECATED
--global.utils.serialize_inventory = function(inventory)
--    local serialized = {}
--    for i = 1, #inventory do
--        local slot = inventory[i]
--        if slot.valid_for_read then
--            local item_name = "\"" .. slot.name .. "\""
--            if serialized[item_name] then
--                serialized[item_name] = serialized[item_name] + slot.count
--            else
--                serialized[item_name] = slot.count
--            end
--        end
--    end
--    return serialized
--end

----- DEPRECATED
--global.utils.serialize_inventory_old = function(inventory)
--  local serialized = {}
--  if inventory[supports_bar]() and inventory[get_bar]() <= #inventory then
--      serialized.b = inventory[get_bar]()
--  end
--
--  serialized.i = {}
--  local previous_index = 0
--  local previous_serialized = nil
--  for i = 1, #inventory do
--      local item = {}
--      local slot = inventory[i]
--      if inventory.supports_filters() then
--          item.f = inventory.get_filter(i)
--      end
--
--      if slot.valid_for_read then
--          global.utils.serialize_item_stack(slot, item)
--      end
--
--      if item.n or item.f or item.e then
--          local item_serialized = game.table_to_json(item)
--          if item_serialized == previous_serialized then
--              local previous_item = serialized.i[#serialized.i]
--              previous_item.r = (previous_item.r or 0) + 1
--              previous_index = i
--
--          else
--              if i ~= previous_index + 1 then
--                  item.s = i
--              end
--
--              previous_index = i
--              previous_serialized = item_serialized
--              table.insert(serialized.i, item)
--          end
--
--      else
--          -- Either an empty slot or serilization failed
--          previous_index = 0
--          previous_serialized = nil
--      end
--  end
--
--  return serialized
--end

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

    -- First try normal products
    local output_list = recipe.products
    if output_list then
        for _, product in pairs(output_list) do
            local product_table = {name = "\""..product.name.."\"", type = "\""..product.type.."\"", amount = product.amount}
            if product.probability then product_table.probability = product.probability end
            table.insert(serialized.products, product_table)
        end
    end

    return serialized
end

global.utils.serialize_fluidbox = function(fluidbox)
    local serialized = {
        length = #fluidbox,
    }
    if fluidbox.owner and fluidbox.owner.name then
        serialized[fluidbox.owner] = fluidbox.owner.name
    end

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
            prototype = prototype and prototype.object_name or nil,
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
            if connection.owner and connection.owner.name then
                table.insert(serialized_box.connections, "\""..connection.owner.name .. "\"")

            end
        end

        serialized.fluidboxes[i] = serialized_box
    end

    return serialized
end


-- Helper function to get relative direction of neighbor
local function get_neighbor_direction(entity, neighbor)
    local dx = neighbor.position.x - entity.position.x
    local dy = neighbor.position.y - entity.position.y

    -- Determine primary direction based on which delta is larger
    if math.abs(dx) > math.abs(dy) then
        return dx > 0 and defines.direction.east or defines.direction.west
    else
        return dy > 0 and defines.direction.south or defines.direction.north
    end
end

-- Helper function to expand a bounding box by a given amount
local function expand_box(box, amount)
    return {
        left_top = {
            x = box.left_top.x - amount,
            y = box.left_top.y - amount
        },
        right_bottom = {
            x = box.right_bottom.x + amount,
            y = box.right_bottom.y + amount
        }
    }
end

local function serialize_neighbours(entity)
    local neighbours = {}

    -- Get entity's prototype collision box
    local prototype = game.entity_prototypes[entity.name]
    local collision_box = prototype.collision_box

    -- Create a slightly larger search box
    local search_box = expand_box(collision_box, 0.707) -- Expand by 0.5 tiles

    -- Convert to world coordinates
    local world_box = {
        left_top = {
            x = entity.position.x + search_box.left_top.x,
            y = entity.position.y + search_box.left_top.y
        },
        right_bottom = {
            x = entity.position.x + search_box.right_bottom.x,
            y = entity.position.y + search_box.right_bottom.y
        }
    }

    -- Find entities within the expanded collision box
    local nearby = entity.surface.find_entities_filtered{
        area = world_box
    }

    -- Process each nearby entity
    for _, neighbor in pairs(nearby) do
        -- Skip if it's the same entity or if it has no unit number
        if neighbor.unit_number and neighbor.unit_number ~= entity.unit_number then
            table.insert(neighbours, {
                unit_number = neighbor.unit_number,
                direction = get_neighbor_direction(entity, neighbor),
                name = "\""..neighbor.name.."\"",
                position = neighbor.position
                --type = neighbor.type
            })
        end
    end

    return neighbours
end

function add_burner_inventory(serialized, burner)
    local fuel_inventory = burner.inventory
    if fuel_inventory and #fuel_inventory > 0 then
        serialized.fuel_inventory = {}
        serialized.remaining_fuel = 0
        for i = 1, #fuel_inventory do
            local item = fuel_inventory[i]
            if item and item.valid_for_read then

                table.insert(serialized.fuel_inventory, {name = "\""..item.name.."\"", count = item.count})
                serialized.remaining_fuel = serialized.remaining_fuel + item.count
            end
        end
    end
end

function get_entity_direction(entity, direction)

    -- If direction is nil then return north
    if direction == nil then
        return defines.direction.north
    end
    --game.print("Getting direction: " .. entity .. " with direction: " .. direction)


    local prototype = game.entity_prototypes[entity]
    -- if prototype is nil (e.g because the entity is a ghost or player character) then return the direction as is
    if prototype == nil then
        return direction
    end
    --game.print(game.entity_prototypes[entity].name, {skip=defines.print_skip.never})

    local cardinals = {
        defines.direction.north,
        defines.direction.east,
        defines.direction.south,
        defines.direction.west
    }
    if prototype and (prototype.name == "boiler" or prototype.type == "generator" or prototype.name == "heat-exchanger") then
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
    elseif prototype and prototype.name == "oil-refinery" then
        if direction == 0 then
            return defines.direction.north
        elseif direction == 1 then
            return defines.direction.east
        elseif direction == 2 then
            return defines.direction.south
        else
            return defines.direction.west
        end
    elseif prototype and prototype.name == "chemical-plant" then
        if direction == 2 then
            return defines.direction.north
        elseif direction == 3 then
            return defines.direction.east
        elseif direction == 0 then
            return defines.direction.south
        else
            return defines.direction.west
        end
    elseif prototype and prototype.type == "transport-belt" or prototype.type == "splitter"  then
        --game.print("Transport belt direction: " .. direction)
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
    elseif prototype.type == "underground-belt" then
        if direction == 1 then
            return defines.direction.east
        elseif direction == 2 then
            return defines.direction.south
        elseif direction == 3 then
            return defines.direction.west
        else
            return defines.direction.north
        end
    elseif prototype.type == "pipe-to-ground" then
        if direction == 1 then
            return defines.direction.west
        elseif direction == 2 then
            return defines.direction.north
        elseif direction == 3 then
            return defines.direction.east
        else
            return defines.direction.south
        end
    elseif prototype.type == "assembling-machine" then
        if direction == 0 then
            return defines.direction.north
        elseif direction == 1 then
            return defines.direction.east
        elseif direction == 2 then
            return defines.direction.south
        else
            return defines.direction.west
        end
    elseif prototype.type == "storage-tank" then
        if direction == 0 then
            return defines.direction.north
        elseif direction == 1 then
            return defines.direction.east -- Only 2 directions
        elseif direction == 2 then
            return defines.direction.south -- Only 2 directions
        else
            return defines.direction.west -- Only 2 directions
        end
    else
        return direction
    end
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
    --game.print("Getting inverse direction: " .. entity .. " with direction: " .. factorio_direction)
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
    else
        --game.print("Returning direction: " .. math.floor(factorio_direction / 2) .. ', '.. factorio_direction)
        -- For other entity types, convert Factorio's direction to 0-3 range
        return factorio_direction
    end
end

-- Helper function to check if a position is valid (not colliding with water or other impassable tiles)
global.utils.is_valid_connection_point = function(surface, position)
    -- Get the tile at the position
    local tile = surface.get_tile(position.x, position.y)

    -- Check if the tile is water or other impassable tiles
    local invalid_tiles = {
        ["water"] = true,
        ["deepwater"] = true,
        ["water-green"] = true,
        ["deepwater-green"] = true,
        ["water-shallow"] = true,
        ["water-mud"] = true,
    }

    -- Return false if the tile is invalid, true otherwise
    return not invalid_tiles[tile.name]
end

-- Helper function to filter connection points
local function filter_connection_points(entity, points)
    if not points then return nil end

    local filtered_points = {}
    for _, point in ipairs(points) do
        if global.utils.is_valid_connection_point(entity.surface, point) then
            table.insert(filtered_points, point)
        end
    end

    -- If all points were filtered out, return nil
    if #filtered_points == 0 then
        return nil
    end

    return filtered_points
end

---- Modified pipe position functions to include filtering
--local function get_pipe_positions_filtered(entity)
--    local positions = global.utils.get_generator_connection_positions(entity)
--    return filter_connection_points(entity, positions)
--end
--
--local function get_pumpjack_pipe_position_filtered(entity)
--    local positions = global.utils.get_pumpjack_connection_points(entity)
--    return filter_connection_points(entity, positions)
--end
--
--local function get_boiler_pipe_positions_filtered(entity)
--    local positions = global.utils.get_boiler_connection_points(entity)
--
--    -- Special handling for boiler since it has a different structure
--    if not positions then return nil end
--
--    local filtered = {
--        water_inputs = filter_connection_points(entity, positions.water_inputs),
--        steam_output = positions.steam_output -- Usually steam output doesn't need filtering as it connects to pipes above ground
--    }
--
--    -- If all water inputs were filtered out, return nil
--    if not filtered.water_inputs or #filtered.water_inputs == 0 then
--        return nil
--    end
--
--    return filtered
--end
--
--local function get_offshore_pump_pipe_position_filtered(entity)
--    local positions = global.utils.get_offshore_pump_connection_points(entity)
--    return filter_connection_points(entity, positions)
--end


global.entity_status_names = {
    [defines.entity_status.working] = "working",
    [defines.entity_status.normal] = "normal",
    [defines.entity_status.no_power] = "no_power",
    [defines.entity_status.low_power] = "low_power",
    [defines.entity_status.no_fuel] = "no_fuel",
    [defines.entity_status.disabled_by_control_behavior] = "disabled_by_control_behavior",
    [defines.entity_status.opened_by_circuit_network] = "opened_by_circuit_network",
    [defines.entity_status.closed_by_circuit_network] = "closed_by_circuit_network",
    [defines.entity_status.disabled_by_script] = "disabled_by_script",
    [defines.entity_status.marked_for_deconstruction] = "marked_for_deconstruction",
    [defines.entity_status.not_plugged_in_electric_network] = "not_plugged_in_electric_network",
    [defines.entity_status.networks_connected] = "networks_connected",
    [defines.entity_status.networks_disconnected] = "networks_disconnected",
    [defines.entity_status.charging] = "charging",
    [defines.entity_status.discharging] = "discharging",
    [defines.entity_status.fully_charged] = "fully_charged",
    [defines.entity_status.out_of_logistic_network] = "out_of_logistic_network",
    [defines.entity_status.no_recipe] = "no_recipe",
    [defines.entity_status.no_ingredients] = "no_ingredients",
    [defines.entity_status.no_input_fluid] = "no_input_fluid",
    [defines.entity_status.no_research_in_progress] = "no_research_in_progress",
    [defines.entity_status.no_minable_resources] = "no_minable_resources",
    [defines.entity_status.low_input_fluid] = "low_input_fluid",
    [defines.entity_status.fluid_ingredient_shortage] = "fluid_ingredient_shortage",
    [defines.entity_status.full_output] = "full_output",
    [defines.entity_status.full_burnt_result_output] = "full_burnt_result_output",
    [defines.entity_status.item_ingredient_shortage] = "item_ingredient_shortage",
    [defines.entity_status.missing_required_fluid] = "missing_required_fluid",
    [defines.entity_status.missing_science_packs] = "missing_science_packs",
    [defines.entity_status.waiting_for_source_items] = "waiting_for_source_items",
    [defines.entity_status.waiting_for_space_in_destination] = "waiting_for_space_in_destination",
    [defines.entity_status.preparing_rocket_for_launch] = "preparing_rocket_for_launch",
    [defines.entity_status.waiting_to_launch_rocket] = "waiting_to_launch_rocket",
    [defines.entity_status.launching_rocket] = "launching_rocket",
    [defines.entity_status.no_modules_to_transmit] = "no_modules_to_transmit",
    [defines.entity_status.recharging_after_power_outage] = "recharging_after_power_outage",
    [defines.entity_status.waiting_for_target_to_be_built] = "waiting_for_target_to_be_built",
    [defines.entity_status.waiting_for_train] = "waiting_for_train",
    [defines.entity_status.no_ammo] = "no_ammo",
    [defines.entity_status.low_temperature] = "low_temperature",
    [defines.entity_status.disabled] = "disabled",
    [defines.entity_status.turned_off_during_daytime] = "turned_off_during_daytime",
    [defines.entity_status.not_connected_to_rail] = "not_connected_to_rail",
    [defines.entity_status.cant_divide_segments] = "cant_divide_segments",
}

global.utils.get_entity_direction = get_entity_direction

global.utils.serialize_entity = function(entity)

    if entity == nil then
        return {}
    end
    --game.print("Serializing entity: " .. entity.name .. " with direction: " .. entity.direction)
    local direction = entity.direction

    if direction ~= nil then
        direction = get_entity_direction(entity.name, entity.direction)
    else
        direction = 0
    end


    --game.print("Serialized direction: ", {skip=defines.print_skip.never})
    local serialized = {
        name = "\""..entity.name.."\"",
        position = entity.position,
        direction = direction,
        health = entity.health,
        energy = entity.energy,
        type = "\""..entity.type.."\"",
        status = global.entity_status_names[entity.status] or "\"normal\"",
    }

    if entity.grid then
        serialized.grid = global.utils.serialize_equipment_grid(entity.grid)
    end
    --game.print(serpent.line(entity.get_inventory(defines.inventory.turret_ammo)))
    serialized.warnings = get_issues(entity)
    --if entity.get_inventory then
    --  for i = 1, #defines.inventory do
    --      local inventory = entity.get_inventory(i)
    --      if inventory and #inventory > 0 then
    --          serialized["inventory_" .. i] = global.utils.serialize_inventory(inventory)
    --      end
    --  end
    --end


    local inventory_types = {
        {name = "fuel", define = defines.inventory.fuel},
        {name = "burnt_result", define = defines.inventory.burnt_result},
        {name = "inventory", define = defines.inventory.chest},
        {name = "furnace_source", define = defines.inventory.furnace_source},
        {name = "furnace_result", define = defines.inventory.furnace_result},
        {name = "furnace_modules", define = defines.inventory.furnace_modules},
        {name = "assembling_machine_input", define = defines.inventory.assembling_machine_input},
        {name = "assembling_machine_output", define = defines.inventory.assembling_machine_output},
        {name = "assembling_machine_modules", define = defines.inventory.assembling_machine_modules},
        {name = "lab_input", define = defines.inventory.lab_input},
        {name = "lab_modules", define = defines.inventory.lab_modules},
        {name = "turret_ammo", define = defines.inventory.turret_ammo}
    }

    for _, inv_type in ipairs(inventory_types) do
        local inventory = entity.get_inventory(inv_type.define)
        if inventory then
            serialized[inv_type.name] = inventory.get_contents()
        end
    end

    -- Add dimensions of the entity
    local prototype = game.entity_prototypes[entity.name]
    local collision_box = prototype.collision_box
    serialized.dimensions = {
        width = math.abs(collision_box.right_bottom.x - collision_box.left_top.x),
        height = math.abs(collision_box.right_bottom.y - collision_box.left_top.y),
    }
    --- Add specific check for gun turrets
    --if entity.type == "ammo-turret" then
    --    local ammo_inventory = entity.get_inventory(defines.inventory.turret_ammo)
    --    if ammo_inventory and #ammo_inventory > 0 then
    --        serialized.ammo_inventory = global.utils.serialize_inventory(ammo_inventory)
    --    end
    --end
    serialized.neighbours = serialize_neighbours(entity)


    -- Add input and output locations if the entity is a transport belt
    --if entity.type == "transport-belt" or entity.type == "underground-belt" then
    --    -- input_position is the position upstream of the belt
    --    --local direction = entity.direction
    --
    --    local x, y = entity.position.x, entity.position.y
    --    if entity.direction == defines.direction.north then
    --        y = y + 1
    --    elseif entity.direction == defines.direction.south then
    --        y = y - 1
    --    elseif entity.direction == defines.direction.east then
    --        x = x - 1
    --    elseif entity.direction == defines.direction.west then
    --        x = x + 1
    --    elseif entity.direction == defines.direction.northeast then
    --        game.print("NORTHEAST")
    --        x = x - 1
    --        y = y + 1
    --    elseif entity.direction == defines.direction.southeast then
    --        x = x - 1
    --        y = y - 1
    --    elseif entity.direction == defines.direction.northwest then
    --        x = x + 1
    --        y = y + 1
    --    elseif entity.direction == defines.direction.southwest then
    --        x = x + 1
    --        y = y - 1
    --    end
    --
    --    serialized.input_position = {x = x, y = y}
    --
    --    -- output_position is the position downstream of the belt
    --    local x, y = entity.position.x, entity.position.y
    --    if entity.direction == defines.direction.north then
    --        y = y - 1
    --    elseif entity.direction == defines.direction.south then
    --        y = y + 1
    --    elseif entity.direction == defines.direction.east then
    --        x = x + 1
    --    elseif entity.direction == defines.direction.west then
    --        x = x - 1
    --    elseif entity.direction == defines.direction.northeast then
    --        x = x + 1
    --        y = y - 1
    --    elseif entity.direction == defines.direction.southeast then
    --        x = x + 1
    --        y = y + 1
    --    elseif entity.direction == defines.direction.northwest then
    --        x = x - 1
    --        y = y - 1
    --    elseif entity.direction == defines.direction.southwest then
    --        x = x - 1
    --        y = y + 1
    --    end
    --    --create_beam_point_with_direction(global.agent_characters[1], entity.direction , {x = x, y = y})
    --    serialized.output_position = {x = x, y = y}
    --    serialized.position = {x = entity.position.x, y = entity.position.y}
    --    --serialized.inventory = entity.get_transport_line(1).get_contents()
    --
    --    -- Get contents from both lines
    --    local line1 = entity.get_transport_line(1)
    --    local line2 = entity.get_transport_line(2)
    --
    --    -- Calculate if belt is full at the end (can't insert more items)
    --    local is_full = not line1.can_insert_at_back() and not line2.can_insert_at_back()
    --
    --    serialized.belt_status = {
    --        status = is_full and "full_output" or "normal"
    --    }
    --
    --    -- Get and merge contents from both lines
    --    serialized.inventory = {}
    --    local line1_contents = line1.get_contents()
    --    local line2_contents = line2.get_contents()
    --
    --    serialized.is_terminus = #entity.belt_neighbours["outputs"] == 0
    --    serialized.is_source = #entity.belt_neighbours["inputs"] == 0
    --
    --    for item_name, count in pairs(line1_contents) do
    --        serialized.inventory[item_name] = (serialized.inventory[item_name] or 0) + count
    --    end
    --    for item_name, count in pairs(line2_contents) do
    --        serialized.inventory[item_name] = (serialized.inventory[item_name] or 0) + count
    --    end
    --
    --    -- Add warning if belt is full
    --    if not serialized.warnings then
    --        serialized.warnings = {}
    --    end
    --    if is_full then
    --        table.insert(serialized.warnings, "Belt output is full")
    --    end
    --
    --    if entity.type == "underground-belt" then
    --        serialized.is_input = entity.belt_to_ground_type == "input"
    --        if serialized.is_input then
    --            serialized.is_terminus = entity.neighbours == nil
    --        else
    --            serialized.is_source = entity.neighbours == nil
    --        end
    --        if entity.neighbours ~= nil then
    --            --game.print(serpent.block(entity.neighbours))
    --            serialized.connected_to = entity.neighbours.unit_number
    --        end
    --    end
    --end
    -- Add input and output locations if the entity is a transport belt
    if entity.type == "transport-belt" or entity.type == "underground-belt" then
        local x, y = entity.position.x, entity.position.y

        -- Initialize positions with default offsets based on belt direction
        local input_offset = {
            [defines.direction.north] = {x = 0, y = 1},
            [defines.direction.south] = {x = 0, y = -1},
            [defines.direction.east] = {x = -1, y = 0},
            [defines.direction.west] = {x = 1, y = 0}
        }

        local output_offset = {
            [defines.direction.north] = {x = 0, y = -1},
            [defines.direction.south] = {x = 0, y = 1},
            [defines.direction.east] = {x = 1, y = 0},
            [defines.direction.west] = {x = -1, y = 0}
        }

        -- Set input position based on upstream connections
        local input_pos = {x = x, y = y}
        if #entity.belt_neighbours["inputs"] > 0 then
            -- Use the position of the first connected input belt
            local input_belt = entity.belt_neighbours["inputs"][1]
            input_pos = {x = input_belt.position.x, y = input_belt.position.y}
        else
            -- No input connection, use default offset
            local offset = input_offset[entity.direction]
            input_pos.x = x + offset.x
            input_pos.y = y + offset.y
        end
        serialized.input_position = input_pos

        -- Set output position based on downstream connections
        local output_pos = {x = x, y = y}
        if #entity.belt_neighbours["outputs"] > 0 then
            -- Use the position of the first connected output belt
            local output_belt = entity.belt_neighbours["outputs"][1]
            output_pos = {x = output_belt.position.x, y = output_belt.position.y}
        else
            -- No output connection, use default offset
            local offset = output_offset[entity.direction]
            output_pos.x = x + offset.x
            output_pos.y = y + offset.y
        end
        serialized.output_position = output_pos

        -- Store the belt's own position
        serialized.position = {x = x, y = y}

        -- Handle belt contents and status
        local line1 = entity.get_transport_line(1)
        local line2 = entity.get_transport_line(2)

        -- Calculate if belt is full at the output
        local is_full = not line1.can_insert_at_back() and not line2.can_insert_at_back()

        serialized.belt_status = {
            status = is_full and "\"full_output\"" or "\"normal\""
        }

        -- Get and merge contents from both lines
        serialized.inventory = {}
        local line1_contents = line1.get_contents()
        local line2_contents = line2.get_contents()

        -- Set terminus and source flags based on connections
        serialized.is_terminus = #entity.belt_neighbours["outputs"] == 0
        serialized.is_source = #entity.belt_neighbours["inputs"] == 0

        -- Merge contents from both belt lines
        for item_name, count in pairs(line1_contents) do
            serialized.inventory[item_name] = (serialized.inventory[item_name] or 0) + count
        end
        for item_name, count in pairs(line2_contents) do
            serialized.inventory[item_name] = (serialized.inventory[item_name] or 0) + count
        end

        -- Add warning if belt is full
        if not serialized.warnings then
            serialized.warnings = {}
        end
        if is_full then
            table.insert(serialized.warnings, "Belt output is full")
        end

        -- Special handling for underground belts
        if entity.type == "underground-belt" then
            serialized.is_input = entity.belt_to_ground_type == "input"
            if serialized.is_input then
                serialized.is_terminus = entity.neighbours == nil
            else
                serialized.is_source = entity.neighbours == nil
            end
            if entity.neighbours ~= nil then
                serialized.connected_to = entity.neighbours.unit_number
            end
        end
    end

    serialized.id = entity.unit_number
    -- Special handling for power poles
    if entity.type == "electric-pole" then
        local stats = entity.electric_network_statistics
        local contents_count = 0
        for name, count in pairs(stats.input_counts) do
            contents_count = contents_count + count
        end

        serialized.flow_rate = contents_count --stats.get_flow_count{name=…, input=…, precision_index=}
    end

    -- Add input and output positions if the entity is a splitter
    if entity.type == "splitter" then
        -- Initialize positions based on entity center
        local x, y = entity.position.x, entity.position.y

        -- Calculate the offset for left/right positions (0.5 tiles)
        local lateral_offset = 0.5

        if entity.direction == defines.direction.north then
            -- Input positions (south side)
            serialized.input_positions = {
                {x = x - lateral_offset, y = y + 1},
                {x = x + lateral_offset, y = y + 1}
            }
            -- Output positions (north side)
            serialized.output_positions = {
                {x = x - lateral_offset, y = y - 1},
                {x = x + lateral_offset, y = y - 1}
            }
        elseif entity.direction == defines.direction.south then
            -- Input positions (north side)
            serialized.input_positions = {
                {x = x + lateral_offset, y = y - 1},
                {x = x - lateral_offset, y = y - 1}
            }
            -- Output positions (south side)
            serialized.output_positions = {
                {x = x + lateral_offset, y = y + 1},
                {x = x - lateral_offset, y = y + 1}
            }
        elseif entity.direction == defines.direction.east then
            -- Input positions (west side)
            serialized.input_positions = {
                {x = x - 1, y = y - lateral_offset},
                {x = x - 1, y = y + lateral_offset}
            }
            -- Output positions (east side)
            serialized.output_positions = {
                {x = x + 1, y = y - lateral_offset},
                {x = x + 1, y = y + lateral_offset}
            }
        elseif entity.direction == defines.direction.west then
            -- Input positions (east side)
            serialized.input_positions = {
                {x = x + 1, y = y + lateral_offset},
                {x = x + 1, y = y - lateral_offset}
            }
            -- Output positions (west side)
            serialized.output_positions = {
                {x = x - 1, y = y + lateral_offset},
                {x = x - 1, y = y - lateral_offset}
            }
        end

        -- Get the contents of both output lines
        serialized.inventory = {
            entity.get_transport_line(1).get_contents(),
            entity.get_transport_line(2).get_contents()
        }
    end

    -- Add input and output locations if the entity is an inserter
    if entity.type == "inserter" then
        serialized.pickup_position = entity.pickup_position
        serialized.drop_position = entity.drop_position

        ---- round to the nearest 0.5
        serialized.pickup_position.x = math.round(serialized.pickup_position.x * 2 ) / 2
        serialized.pickup_position.y = math.round(serialized.pickup_position.y * 2 ) / 2
        serialized.drop_position.x = math.round(serialized.drop_position.x * 2 ) / 2
        serialized.drop_position.y = math.round(serialized.drop_position.y * 2 ) / 2

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
    --if entity.type == "splitter" then
    --  serialized.input_position = entity.input_position
    --  serialized.output_position = entity.output_position
    --end

    -- Add input and output locations if the entity is a pipe
    if entity.type == "pipe" then
        serialized.connections = {}
        local fluid_name = nil
        for _, connection in pairs(entity.fluidbox.get_pipe_connections(1)) do
            table.insert(serialized.connections, connection.position)
        end
        local contents_count = 0
        for name, count in pairs(entity.fluidbox.get_fluid_system_contents(1)) do
            contents_count = contents_count + count
            fluid_name = "\""..name.."\""
        end
        serialized.contents = contents_count
        serialized.fluid = fluid_name
        serialized.fluidbox_id = entity.fluidbox.get_fluid_system_id(1)
        serialized.flow_rate = entity.fluidbox.get_flow(1)
    end

    -- Add input and output locations if the entity is a pipe-to-ground
    if entity.type == "pipe-to-ground" then
        serialized.connections = {}
        local fluid_name = nil
        for _, connection in pairs(entity.fluidbox.get_pipe_connections(1)) do
            table.insert(serialized.connections, connection.position)
        end
        local contents_count = 0
        for name, count in pairs(entity.fluidbox.get_fluid_system_contents(1)) do
            contents_count = contents_count + count
            fluid_name = "\""..name.."\""
        end
        serialized.fluidbox_id = entity.fluidbox.get_fluid_system_id(1)
        serialized.flow_rate = entity.fluidbox.get_flow(1)
        serialized.contents = contents_count
        serialized.fluid = fluid_name
        --serialized.input_position = entity.fluidbox.get_connections(1)[1].position
        --serialized.output_position = entity.fluidbox.get_connections(2)[1].position
    end

    -- Add input and output locations if the entity is a pump
    if entity.type == "pump" then
        serialized.input_position = entity.fluidbox.get_connections(1)[1].position
        serialized.output_position = entity.fluidbox.get_connections(2)[1].position
    end

    -- Add the current research to the lab
    if entity.name == "lab" then
        if global.agent_characters[1].force.current_research ~= nil then
            serialized.research = global.agent_characters[1].force.current_research.name
        else
            serialized.research = nil
        end
    end

    -- Add input and output locations if the entity is a offshore pump
    if entity.type == "offshore-pump" then
        local burner = entity.burner
        if burner then
            add_burner_inventory(serialized, burner)
        end
    end


    if entity.name == "oil-refinery" then
        local x, y = entity.position.x, entity.position.y
        serialized.input_connection_points = {}
        serialized.output_connection_points = {}

        local recipe = entity.get_recipe()
        local mappings = global.utils.get_refinery_fluid_mappings(entity, recipe)
        if mappings then
            serialized.input_connection_points = mappings.inputs
            serialized.output_connection_points = mappings.outputs
        end
        --if entity.direction == defines.direction.north then
        --    -- Two crude oil inputs at the bottom
        --    table.insert(serialized.input_connection_points,
        --            {x = x + 1, y = y + 3
        --            })
        --    table.insert(serialized.input_connection_points,
        --            {x = x - 1, y = y + 3
        --            })
        --    -- Three outputs at the top (petroleum, light oil, heavy oil)
        --    table.insert(serialized.output_connection_points,
        --            {x = x - 2, y = y - 3
        --            })
        --    table.insert(serialized.output_connection_points,
        --            {x = x, y = y - 3
        --            })
        --    table.insert(serialized.output_connection_points,
        --            {x = x + 2, y = y - 3
        --            })
        --elseif entity.direction == defines.direction.south then
        --    -- Two crude oil inputs at the top
        --    table.insert(serialized.input_connection_points,
        --            {x = x + 1, y = y - 3
        --            })
        --    table.insert(serialized.input_connection_points,
        --            {x = x - 1, y = y - 3
        --            })
        --    -- Three outputs at the bottom
        --    table.insert(serialized.output_connection_points,
        --            {x = x - 2, y = y + 3
        --            })
        --    table.insert(serialized.output_connection_points,
        --            {x = x, y = y + 3
        --            })
        --    table.insert(serialized.output_connection_points,
        --            {x = x + 2, y = y + 3
        --            })
        --elseif entity.direction == defines.direction.east then
        --    -- Two crude oil inputs on the left
        --    table.insert(serialized.input_connection_points,
        --            {x = x - 3, y = y + 1
        --            })
        --    table.insert(serialized.input_connection_points,
        --            {x = x - 3, y = y - 1
        --            })
        --    -- Three outputs on the right
        --    table.insert(serialized.output_connection_points,
        --            {x = x + 3, y = y - 2
        --            })
        --    table.insert(serialized.output_connection_points,
        --            {x = x + 3, y = y
        --            })
        --    table.insert(serialized.output_connection_points,
        --            {x = x + 3, y = y + 2
        --            })
        --elseif entity.direction == defines.direction.west then
        --    -- Two crude oil inputs on the right
        --    table.insert(serialized.input_connection_points,
        --            {x = x + 3, y = y + 1
        --            })
        --    table.insert(serialized.input_connection_points,
        --            {x = x + 3, y = y - 1
        --            })
        --    -- Three outputs on the left
        --    table.insert(serialized.output_connection_points,
        --            {x = x - 3, y = y - 2
        --            })
        --    table.insert(serialized.output_connection_points,
        --            {x = x - 3, y = y
        --            })
        --    table.insert(serialized.output_connection_points,
        --            {x = x - 3, y = y + 2
        --            })
        --end

        ---- Filter out any invalid connection points
        --local filtered_input_points = {}
        --for _, point in ipairs(serialized.input_connection_points) do
        --    if global.utils.is_valid_connection_point(game.surfaces[1], point.position) then
        --        table.insert(filtered_input_points, point.positio)
        --    end
        --end
        --serialized.input_connection_points = filtered_input_points
        --
        --local filtered_output_points = {}
        --for _, point in ipairs(serialized.output_connection_points) do
        --    if global.utils.is_valid_connection_point(game.surfaces[1], point.position) then
        --        table.insert(filtered_output_points, point.position)
        --    end
        --end
        --serialized.output_connection_points = filtered_output_points
    end

    if entity.name == "chemical-plant" then
        local x, y = entity.position.x, entity.position.y
        serialized.input_connection_points = {}
        serialized.output_connection_points = {}

        local recipe = entity.get_recipe()
        local mappings = global.utils.get_chemical_plant_fluid_mappings(entity, recipe)
        if mappings then
            serialized.input_connection_points = mappings.inputs
            serialized.output_connection_points = mappings.outputs
        end

        --if direction == defines.direction.north then
        --    -- Input pipes at the bottom
        --    table.insert(serialized.input_connection_points,
        --            {x = x - 1, y = y + 1.5
        --            })
        --    table.insert(serialized.input_connection_points,
        --            {x = x + 1, y = y + 1.5
        --            })
        --    -- Output pipes at the top
        --    table.insert(serialized.output_connection_points,
        --            {x = x - 1, y = y - 1.5
        --            })
        --    table.insert(serialized.output_connection_points,
        --            {x = x + 1, y = y - 1.5
        --            })
        --elseif direction == defines.direction.south then
        --    -- Input pipes at the top
        --    table.insert(serialized.input_connection_points,
        --            {x = x - 1, y = y - 1.5
        --            })
        --    table.insert(serialized.input_connection_points,
        --            {x = x + 1, y = y - 1.5
        --            })
        --    -- Output pipes at the bottom
        --    table.insert(serialized.output_connection_points,
        --            {x = x - 1, y = y + 1.5
        --            })
        --    table.insert(serialized.output_connection_points,
        --            {x = x + 1, y = y + 1.5
        --            })
        --elseif direction == defines.direction.east then
        --    -- Input pipes on the left
        --    table.insert(serialized.input_connection_points,
        --            {x = x - 1.5, y = y - 1
        --            })
        --    table.insert(serialized.input_connection_points,
        --            {x = x - 1.5, y = y + 1,
        --            })
        --    -- Output pipes on the right
        --    table.insert(serialized.output_connection_points,
        --            {x = x + 1.5, y = y - 1,
        --            })
        --    table.insert(serialized.output_connection_points,
        --            {x = x + 1.5, y = y + 1
        --            })
        --elseif direction == defines.direction.west then
        --    -- Input pipes on the right
        --    table.insert(serialized.input_connection_points,
        --            {x = x + 1.5, y = y - 1,
        --            })
        --    table.insert(serialized.input_connection_points,
        --            {x = x + 1.5, y = y + 1
        --            })
        --    -- Output pipes on the left
        --    table.insert(serialized.output_connection_points,
        --            {x = x - 1.5, y = y - 1
        --            })
        --    table.insert(serialized.output_connection_points,
        --            {x = x - 1.5, y = y + 1
        --            })
        --end

        -- Filter out any invalid connection points
        local filtered_input_points = {}
        for _, point in ipairs(serialized.input_connection_points) do
            if global.utils.is_valid_connection_point(game.surfaces[1], point) then
                table.insert(filtered_input_points, point)
            end
        end
        serialized.input_connection_points = filtered_input_points

        -- Filter out any invalid connection points
        local filtered_output_points = {}
        for _, point in ipairs(serialized.output_connection_points) do
            if global.utils.is_valid_connection_point(game.surfaces[1], point) then
                table.insert(filtered_output_points, point)
            end
        end
        serialized.output_connection_points = filtered_output_points

    end


    if entity.type == "storage-tank" then
        -- Get and filter connection points
        local connection_points = global.utils.get_storage_tank_connection_points(entity)
        local filtered_points = {}

        -- Filter out invalid connection points (e.g., those in water)
        for _, point in ipairs(connection_points) do
            if global.utils.is_valid_connection_point(entity.surface, point) then
                table.insert(filtered_points, point)
            end
        end

        -- Add connection points to serialized data
        serialized.connection_points = filtered_points

        -- Add fluid box information
        if entity.fluidbox and #entity.fluidbox > 0 then
            game.print("There is a fluidbox")
            local fluid = entity.fluidbox[1]
            if fluid then
                serialized.fluid = string.format("\"%s\"", fluid.name)
                serialized.fluid_amount = fluid.amount
                serialized.fluid_temperature = fluid.temperature
                serialized.fluid_system_id = entity.fluidbox.get_fluid_system_id(1)
            end
        end

        -- Add warning if some connection points were filtered
        if #filtered_points < #connection_points then
            if not serialized.warnings then
                serialized.warnings = {}
            end
            table.insert(serialized.warnings, "\"some connection points were filtered due to being blocked by water\"")
        end
    end


    if entity.type == "assembling-machine" then
        local x, y = entity.position.x, entity.position.y
        serialized.connection_points = {}

        -- Assembling machine connection points are similar to chemical plants
        if entity.direction == defines.direction.north then
            table.insert(serialized.connection_points,
                    {x = x, y = y - 2
                    })
        elseif entity.direction == defines.direction.south then
            table.insert(serialized.connection_points,
                    {x = x, y = y + 2
                    })
        elseif entity.direction == defines.direction.east then
            table.insert(serialized.connection_points,
                    {x = x + 2, y = y
                    })
        elseif entity.direction == defines.direction.west then
            table.insert(serialized.connection_points,
                    {x = x - 2, y = y
                    })
        end

        -- Filter out any invalid connection points
        local filtered_connection_points = {}
        for _, point in ipairs(serialized.connection_points) do
            game.print(serpent.line(point))
            if global.utils.is_valid_connection_point(game.surfaces[1], point) then
                table.insert(filtered_connection_points, point)
            end
        end

        serialized.connection_points = filtered_connection_points
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

    --if entity.type == "mining-drill" then
    --  serialized.drop_position = {
    --      x = entity.drop_position.x,
    --      y = entity.drop_position.y
    --  }
    --  serialized.drop_position.x = math.round(serialized.drop_position.x * 2 ) / 2
    --  serialized.drop_position.y = math.round(serialized.drop_position.y * 2 ) / 2
    --  game.print("Mining drill drop position: " .. serpent.line(serialized.drop_position))
    --  local burner = entity.burner
    --  if burner then
    --      add_burner_inventory(serialized, burner)
    --  end
    --end

    if entity.type == "mining-drill" then
        serialized.drop_position = {
            x = entity.drop_position.x,
            y = entity.drop_position.y
        }
        serialized.drop_position.x = math.round(serialized.drop_position.x * 2) / 2
        serialized.drop_position.y = math.round(serialized.drop_position.y * 2) / 2
        -- game.print("Mining drill drop position: " .. serpent.line(serialized.drop_position))

        -- Get the mining area
        local prototype = game.entity_prototypes[entity.name]
        local mining_area = prototype.mining_drill_radius * 2

        local position = entity.position

        -- Initialize resources table
        serialized.resources = {}

        -- Calculate the area to check based on mining drill radius
        local start_x = position.x - mining_area/2
        local start_y = position.y - mining_area/2
        local end_x = position.x + mining_area/2
        local end_y = position.y + mining_area/2

        local resources = game.surfaces[1].find_entities_filtered{
            area = {{start_x, start_y}, {end_x, end_y}},
            type = "resource",
        }

        for _, resource in pairs(resources) do
            if not serialized.resources[resource.name] then
                serialized.resources[resource.name] = {
                    name = "\""..resource.name.."\"",
                    count = 0,
                }
            end

            -- Add the resource amount and position
            serialized.resources[resource.name].count = serialized.resources[resource.name].count + resource.amount
        end


        -- Convert resources table to array for consistent ordering
        local resources_array = {}
        for _, resource_data in pairs(serialized.resources) do
            table.insert(resources_array, resource_data)
        end
        serialized.resources = resources_array

        -- Add mining status
        if #resources_array == 0 then
            serialized.status = "\"no_minable_resources\""
            if not serialized.warnings then serialized.warnings = {} end
            table.insert(serialized.warnings, "\"nothing to mine\"")
        end

        -- Add burner info if applicable
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
            -- game.print("Boiler direction is north")
            serialized.connection_points = {{x = x - 2, y = y + 0.5}, {x = x + 2, y = y + 0.5}}
            serialized.steam_output_point = {x = x, y = y - 1.5}
        elseif entity.direction == defines.direction.south then
            -- game.print("Boiler direction is south")
            serialized.connection_points = {{x = x - 2, y = y - 0.5}, {x = x + 2, y = y - 0.5}}
            serialized.steam_output_point = {x = x, y = y + 1.5}
        elseif entity.direction == defines.direction.east then
            -- game.print("Boiler direction is east")
            serialized.connection_points = {{x = x - 0.5, y = y - 2}, {x = x - 0.5, y = y + 2}}
            serialized.steam_output_point = {x = x + 1.5, y = y}
        elseif entity.direction == defines.direction.west then
            -- game.print("Boiler direction is west")
            serialized.connection_points = {{x = x + 0.5, y = y - 2}, {x = x + 0.5, y = y + 2}}
            serialized.steam_output_point = {x = x - 1.5, y = y}
        end
    end

    if entity.type == "rocket-silo" then
        -- Basic rocket silo properties
        serialized.rocket_parts = 0  -- Will be updated with actual count
        serialized.rocket_progress = 0.0  -- Will be updated with actual progress
        serialized.launch_count = entity.launch_count or 0

        -- Get the current rocket details if one exists
        --local rocket_inventory = entity.get_inventory(defines.inventory.rocket_silo_rocket)
        --local rocket = entity.rocket or nil

        --if rocket then
        --    -- If there's a rocket, get its state
        --    serialized.rocket = {
        --        status = global.entity_status_names[rocket.status] or "normal",
        --        launch_progress = rocket.launch_progress * 100.0  -- Convert to percentage
        --    }
        --
        --    -- Check for payload
        --    local payload_inventory = rocket.get_inventory(defines.inventory.cargo_unit)
        --    if payload_inventory and not payload_inventory.is_empty() then
        --        serialized.rocket.payload = payload_inventory.get_contents()
        --    end
        --end

        -- Get part construction progress
        local parts_inventory = entity.get_inventory(defines.inventory.rocket_silo_input)
        if parts_inventory then
            serialized.rocket_parts = parts_inventory.get_item_count("rocket-part")
            -- Each rocket needs 100 parts, calculate progress
            serialized.rocket_progress = (serialized.rocket_parts / 100.0) * 100.0
        end

        -- Get input inventories for rocket components
        local rocket_inventory = {
            rocket_part = entity.get_inventory(defines.inventory.rocket_silo_input),
            result = entity.get_inventory(defines.inventory.rocket_silo_output)
        }

        -- Serialize the component inventories
        for name, inventory in pairs(rocket_inventory) do
            if inventory and not inventory.is_empty() then
                serialized[name .. "_inventory"] = inventory.get_contents()
            end
        end

        -- Update status based on rocket state
        if serialized.rocket then
            if serialized.rocket.launch_progress > 0 then
                serialized.status = "\"launching_rocket\""
            elseif serialized.rocket.payload then
                serialized.status = "\"waiting_to_launch_rocket\""
            end
        elseif serialized.rocket_parts < 100 then
            if serialized.rocket_parts > 0 then
                serialized.status = "\"preparing_rocket_for_launch\""
            end
        end

        -- Add warnings based on state
        if not serialized.warnings then
            serialized.warnings = {}
        end
        if serialized.rocket_parts < 100 and serialized.rocket_parts > 0 then
            table.insert(serialized.warnings, "\"waiting for rocket parts\"")
        elseif serialized.status == "\"waiting_to_launch_rocket\"" then
            table.insert(serialized.warnings, "\"ready to launch\"")
        end
    end

    if entity.type == "solar-panel" then
        serialized.electric_output_flow_limit = entity.electric_output_flow_limit
    end

    if entity.type == 'accumulator' then
        --serialized.energy_source = entity.energy_source
        --serialized.power_usage = entity.power_usage
        --serialized.emissions = entity.emissions
        serialized.energy = entity.energy
    end

    if entity.type == "generator" then
        serialized.connection_points = global.utils.get_generator_connection_positions(entity)
        serialized.energy_generated_last_tick = entity.energy_generated_last_tick
        --serialized.power_production = entity.power_production
    end

    if entity.name == "pumpjack" then
        serialized.connection_points = global.utils.get_pumpjack_connection_points(entity)
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
                    table.insert(serialized.input_inventory, {name = "\""..item.name.."\"", count = item.count})
                end
            end
        end
    end

    -- Add fluid box if the entity is an offshore pump
    if entity.type == "offshore-pump" then
        serialized.connection_points = global.utils.get_offshore_pump_connection_points(entity)
    end

    -- If entity has a fluidbox
    if entity.fluidbox then
        local fluid_box = entity.fluidbox
        if fluid_box and #fluid_box > 0 then
            serialized.fluid_box = {}
            for i = 1, #fluid_box do
                -- game.print("Fluid!")
                local fluid = fluid_box[i]
                if fluid then
                    table.insert(serialized.fluid_box, {name = "\""..fluid.name.."\"", amount = fluid.amount, temperature = fluid.temperature})
                end
            end
        end
    end

    -- Add fluid handler status check
    if is_fluid_handler(entity.type) then
        -- Check if the entity has a fluidbox
        if not entity.fluidbox or #entity.fluidbox == 0 then
            serialized.status = "\"not_connected\""
            if not serialized.warnings then
                serialized.warnings = {}
            end
            table.insert(serialized.warnings, "\"missing fluid connection\"")
        else
            -- Additional fluid-specific checks
            local fluid_systems = {}
            local has_fluid = false
            local fluid_contents = nil
            for i = 1, #entity.fluidbox do
                if entity.fluidbox[i] then
                    local system_id = entity.fluidbox.get_fluid_system_id(i)
                    if system_id then
                        table.insert(fluid_systems, system_id)
                    end
                    has_fluid = true
                    fluid_contents =  "\""..entity.fluidbox[i].name.."\""
                    break
                end
            end
            serialized.fluid_systems = fluid_systems

            if not has_fluid then
                serialized.status = "not_connected"
                if not serialized.warnings then
                    serialized.warnings = {}
                end
                table.insert(serialized.warnings, "\"no fluid present in connections\"")
            else
                serialized.fluid = fluid_contents
            end
            --serialized.fluidbox = global.utils.serialize_fluidbox(entity.fluidbox)
        end
    end

    if entity.electric_network_id then
        serialized.electrical_id = entity.electric_network_id
    end

    serialized.direction = get_inverse_entity_direction(entity.name, entity.direction) --api_direction_map[entity.direction]
    -- Post-process connection points if they exist
    if serialized.connection_points then
        local filtered_points = {}
        for _, point in ipairs(serialized.connection_points) do
            if global.utils.is_valid_connection_point(game.surfaces[1], point) then
                table.insert(filtered_points, point)
            end
        end

        -- Update connection points or remove if all were filtered
        if #filtered_points > 0 then
            serialized.connection_points = filtered_points
        else
            serialized.connection_points = nil
        end

        -- Add warning if points were filtered
        if not serialized.warnings then
            serialized.warnings = {}
        end

        if serialized.connection_points ~= nil then
            if #filtered_points < #serialized.connection_points then
                table.insert(serialized.warnings, "\"some connection points were filtered due to being blocked by water\"")
            end
        end
    end

    -- Handle special case for boilers which have separate steam output points
    if serialized.steam_output_point then
        if not global.utils.is_valid_connection_point(game.surfaces[1], serialized.steam_output_point) then
            serialized.steam_output_point = nil
            if not serialized.warnings then
                serialized.warnings = {}
            end
            table.insert(serialized.warnings, "\"steam output point was filtered due to being blocked by water\"")
        end
    end

    return serialized
end
