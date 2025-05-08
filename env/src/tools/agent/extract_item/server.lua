-- Helper function to check all possible inventories of an entity
local function get_entity_item_count(entity, item_name)
    local inventory_types = {
        defines.inventory.chest,
        defines.inventory.furnace_source,
        defines.inventory.furnace_result,
        defines.inventory.assembling_machine_input,
        defines.inventory.assembling_machine_output,
        defines.inventory.fuel,
        defines.inventory.burnt_result,
        defines.inventory.reactor_source,
        defines.inventory.reactor_result,
        defines.inventory.lab_input,
        defines.inventory.lab_source,
        defines.inventory.mining_drill_input,
        defines.inventory.item_main,  -- For cargo wagons
        defines.inventory.robot_cargo,
        defines.inventory.robot_repair,
        defines.inventory.car_trunk,
        defines.inventory.car_fuel,
        defines.inventory.roboport_material,
        defines.inventory.roboport_robot,
        defines.inventory.storage_tank,
        defines.inventory.artillery_turret_ammo,
        defines.inventory.turret_ammo,
        defines.inventory.beacon_modules,
        defines.inventory.character_main,
        defines.inventory.character_guns,
        defines.inventory.character_ammo,
        defines.inventory.character_armor,
        defines.inventory.character_vehicle,
        defines.inventory.character_trash
    }

    local total_count = 0
    for _, inv_type in ipairs(inventory_types) do
        local inventory = entity.get_inventory(inv_type)
        if inventory then
            total_count = total_count + entity.get_item_count(item_name)
        end
    end
    return total_count
end

-- Helper function to remove items from any valid inventory
local function remove_items_from_entity(entity, stack)
    local inventory_types = {
        defines.inventory.chest,
        defines.inventory.furnace_source,
        defines.inventory.furnace_result,
        defines.inventory.assembling_machine_input,
        defines.inventory.assembling_machine_output,
        defines.inventory.fuel,
        defines.inventory.burnt_result,
        defines.inventory.reactor_source,
        defines.inventory.reactor_result,
        defines.inventory.lab_input,
        defines.inventory.lab_source,
        defines.inventory.mining_drill_input,
        defines.inventory.item_main,
        defines.inventory.robot_cargo,
        defines.inventory.robot_repair,
        defines.inventory.car_trunk,
        defines.inventory.car_fuel,
        defines.inventory.roboport_material,
        defines.inventory.roboport_robot,
        defines.inventory.storage_tank,
        defines.inventory.artillery_turret_ammo,
        defines.inventory.turret_ammo,
        defines.inventory.beacon_modules,
        defines.inventory.character_main,
        defines.inventory.character_guns,
        defines.inventory.character_ammo,
        defines.inventory.character_armor,
        defines.inventory.character_vehicle,
        defines.inventory.character_trash
    }

    local items_remaining = stack.count
    local total_removed = 0

    for _, inv_type in ipairs(inventory_types) do
        if items_remaining <= 0 then
            break
        end

        local inventory = entity.get_inventory(inv_type)
        if inventory then
            local current_stack = {name = stack.name, count = items_remaining}
            local removed = entity.remove_item(current_stack)
            total_removed = total_removed + removed
            items_remaining = items_remaining - removed
        end
    end

    return total_removed
end

global.actions.extract_item = function(player_index, extract_item, count, x, y, source_name)
    local player = global.agent_characters[player_index]
    local position = {x=x, y=y}
    local surface = player.surface

    -- First validate the request
    if count <= 0 then
        error("\"Invalid count: must be greater than 0\"")
    end

    -- Find all entities in range
    local search_radius = 10
    local area = {{position.x - search_radius, position.y - search_radius},
                  {position.x + search_radius, position.y + search_radius}}
    local buildings = nil

    if source_name ~= nil then
        buildings = surface.find_entities_filtered{
            area = area,
            name = source_name
        }
    else
        buildings = surface.find_entities_filtered{
            area = area
        }
    end

    -- Find the closest building with the item we want
    local closest_distance = math.huge
    local closest_entity = nil
    local found_any_items = false

    for _, building in ipairs(buildings) do
        if building.name ~= 'character' then
            local item_count = get_entity_item_count(building, extract_item)
            if item_count > 0 then
                found_any_items = true
                local distance = ((position.x - building.position.x) ^ 2 +
                                (position.y - building.position.y) ^ 2) ^ 0.5
                if distance < closest_distance then
                    closest_distance = distance
                    closest_entity = building
                end
            end
        end
    end

    -- Error handling in priority order

    if #buildings == 0 then
        error("\"Could not find any entities in range\"")
    end

    if not closest_entity then
        if source_name then
            error("\"Could not find a valid "..source_name.." entity containing " .. extract_item.."\"")
        else
            error("\"Could not find a valid entity containing " .. extract_item .. "\"")
        end
    end

    if closest_distance > search_radius then
        error("\"Entity at ("..closest_entity.position.x..", "..closest_entity.position.y..") is too far away from your position of ("..player.position.x..","..player.position.y.."), move closer.\"")
    end

    if not found_any_items then
        error("\"No " .. extract_item .. " found in any nearby entities\"")
    end

    -- Calculate how many items we can actually extract
    local available_count = get_entity_item_count(closest_entity, extract_item)
    local extract_count = math.min(count, available_count)

    -- Create the stack for extraction
    local stack = {name=extract_item, count=extract_count}

    -- Attempt the extraction
    local number_extracted = remove_items_from_entity(closest_entity, stack)

    if number_extracted > 0 then
        -- Insert items into player inventory
        local inserted = player.insert(stack)

        -- If we couldn't insert all items, put them back in the container
        if inserted < number_extracted then
            stack.count = number_extracted - inserted
            closest_entity.insert(stack)
            number_extracted = inserted
        end

        -- game.print("Extracted " .. number_extracted .. " " .. extract_item)
        return number_extracted
    else
        -- This should rarely happen given our prior checks
        error("\"Failed to extract " .. extract_item .. "\"")
    end
end