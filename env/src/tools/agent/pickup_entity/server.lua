global.actions.pickup_entity = function(player_index, x, y, entity)
    local player = global.agent_characters[player_index]
    local position = {x=x, y=y}
    local surface = player.surface
    local success = false
    rendering.draw_circle{only_in_alt_mode=true, width = 0.5, color = {r = 0, g = 1, b = 0}, surface = player.surface, radius = 0.25, filled = false, target = position, time_to_live = 12000}

    -- Debug print
    -- game.print("Starting pickup attempt for " .. entity .. " at (" .. x .. ", " .. y .. ")")

    -- Function to check if player can receive items
    local function can_receive_items(items_to_check)
        local main_inventory = player.get_main_inventory()
        -- Check each item individually
        for _, item in pairs(items_to_check) do
            if not main_inventory.can_insert({name = item.name, count = item.count}) then
                return false
            end
        end
        return true
    end

    -- Function to pick up and add entity to player's inventory
    local function pickup_placed_entity(entities)
        for _, ent in pairs(entities) do
            if ent.valid and ent.name == entity then
                -- game.print("Found valid placed entity: " .. ent.name)

                -- Collect all items that need to be inserted
                local items_to_insert = {}

                -- Add entity products
                --local products = ent.prototype.mineable_properties.products
                --if products ~= nil then
                --    for _, product in pairs(products) do
                --        table.insert(items_to_insert, {name=product.name, count=product.amount})
                --    end
                --end

                -- Add chest contents if applicable
                if ent.get_inventory(defines.inventory.chest) then
                    for name, count in pairs(ent.get_inventory(defines.inventory.chest).get_contents()) do
                        table.insert(items_to_insert, {name=name, count=count})
                    end
                end

                -- Add transport belt contents if applicable
                if ent.type == "transport-belt" then
                    -- Check line 1
                    local line1 = ent.get_transport_line(1)
                    local contents1 = line1.get_contents()
                    for name, count in pairs(contents1) do
                        table.insert(items_to_insert, {name=name, count=count})
                    end

                    -- Check line 2
                    local line2 = ent.get_transport_line(2)
                    local contents2 = line2.get_contents()
                    for name, count in pairs(contents2) do
                        table.insert(items_to_insert, {name=name, count=count})
                    end
                end

                -- Add the entity itself
                table.insert(items_to_insert, {name=ent.name, count=1})

                -- Check if player can receive all items
                if not can_receive_items(items_to_insert) then
                    error("Inventory is full")
                end

                -- Insert all items
                for _, item in pairs(items_to_insert) do
                    player.insert(item)
                end

                if ent.can_be_destroyed() then
                    -- game.print("Picked up placed "..ent.name)
                    pcall(ent.destroy{raise_destroy=false, do_cliff_correction=false})
                    return true
                end
            end
        end
        return false
    end

    -- Function to pick up items on ground
    local function pickup_ground_item(ground_items)
        for _, item in pairs(ground_items) do
            if item.valid and item.stack and item.stack.name == entity then
                -- game.print("Found valid ground item: " .. item.stack.name)
                local count = item.stack.count

                -- Check if player can receive the item
                if not can_receive_items({{name=entity, count=count}}) then
                    error("Cannot pick up " .. entity .. " - inventory is full")
                end

                local inserted = player.insert{name=entity, count=count}
                if inserted > 0 then
                    -- game.print("Picked up ground item2 " .. count .. " " .. entity)
                    pcall(item.destroy{raise_destroy=false})
                    return true
                end
            end
            return true
        end
        return false
    end

    -- Find both types of entities first
    local player_entities = surface.find_entities_filtered{
        name=entity,
        position=position,
        radius=0.707,
        force="player"
    }
    -- game.print("Found " .. #player_entities .. " placed entities")

    local ground_items = surface.find_entities_filtered{
        name="item-on-ground",
        position=position,
        radius=0.707
    }
    -- game.print("Found " .. #ground_items .. " ground items")

    -- Try to pick up placed entities first, if any exist
    if #player_entities > 0 then
        success = pickup_placed_entity(player_entities)
        if success then
            -- game.print("Successfully picked up placed entity")
            return {}
        end
    end

    -- Only try ground items if we haven't succeeded with placed entities
    if not success and #ground_items > 0 then
        success = pickup_ground_item(ground_items)
        if success then
            -- game.print("Successfully picked up ground item")
            return {}
        end
    end

    if not success then
        if #player_entities == 0 and #ground_items == 0 then
            error("Couldn't find "..entity.." at position ("..x..", "..y..") to pick up.")
        else
            error("Could not pick up "..entity)
        end
    end

    return {}
end