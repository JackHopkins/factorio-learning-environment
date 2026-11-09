-- Move up to `count` items from the entity's inventories into the player's.
-- Each slot is moved with its state: for tools (science packs) the top item of a
-- stack may be part-used, and that partial durability goes with it, so the total
-- durability in the world is unchanged. Returns the number of items moved.
local function move_items_to_player(entity, player, item_name, count)
    local moved = 0
    for index = 1, entity.get_max_inventory_index() do
        local inventory = entity.get_inventory(index)
        if inventory then
            for slot = 1, #inventory do
                if moved >= count then
                    return moved
                end
                local stack = inventory[slot]
                if stack.valid_for_read and stack.name == item_name then
                    local is_tool = stack.prototype.type == "tool"
                    local taken = {
                        name = item_name,
                        count = math.min(count - moved, stack.count),
                        quality = stack.quality.name
                    }
                    if is_tool then
                        taken.durability = stack.durability
                    end
                    local inserted = player.insert(taken)
                    if inserted == 0 then
                        return moved
                    end
                    if inserted >= stack.count then
                        stack.clear()
                    else
                        stack.count = stack.count - inserted
                        if is_tool then
                            -- the part-used item went to the player; the rest are full
                            stack.durability = stack.prototype.get_durability(stack.quality)
                        end
                    end
                    moved = moved + inserted
                end
            end
        end
    end
    return moved
end

storage.actions.extract_item = function(player_index, extract_item, count, x, y, source_name)
    -- Ensure we have a valid character, recreating if necessary
    local player = storage.utils.ensure_valid_character(player_index)
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
            local item_count = building.get_item_count(extract_item)
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
    local available_count = closest_entity.get_item_count(extract_item)
    local extract_count = math.min(count, available_count)

    -- Move the items into the player's inventory (only what fits is removed)
    local number_extracted = move_items_to_player(closest_entity, player, extract_item, extract_count)

    if number_extracted > 0 then
        -- game.print("Extracted " .. number_extracted .. " " .. extract_item)
        return number_extracted
    else
        -- Nothing could be moved (e.g. the player's inventory is full)
        error("\"Failed to extract " .. extract_item .. "\"")
    end
end
