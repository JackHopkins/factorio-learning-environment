global.actions.pickup_entity = function(player_index, x, y, entity)
    local player = game.get_player(player_index)
    local position = {x=x, y=y}
    local surface = player.surface
    local success = false

    -- Debug print
    game.print("Starting pickup attempt for " .. entity .. " at (" .. x .. ", " .. y .. ")")

    -- Function to pick up and add entity to player's inventory
    local function pickup_placed_entity(entities)
        for _, ent in pairs(entities) do
            if ent.valid and ent.name == entity then
                game.print("Found valid placed entity: " .. ent.name) -- Debug
                local products = ent.prototype.mineable_properties.products
                if products ~= nil then
                    game.print("Entity has mineable products") -- Debug
                    for _, product in pairs(products) do
                        player.insert{name=product.name, count=product.amount}
                    end
                end
                if ent.get_inventory(defines.inventory.chest) then
                    for name, count in pairs(ent.get_inventory(defines.inventory.chest).get_contents()) do
                        player.insert{name=name, count=count}
                    end
                end
                player.insert{name=ent.name, count=1}
                if ent.can_be_destroyed() then
                    game.print("Picked up placed "..ent.name)
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
                game.print("Found valid ground item: " .. item.stack.name)-- .. " of count "..item.stack.count) -- Debug
                local count = item.stack.count
                local inserted = player.insert{name=entity, count=count}
                if inserted > 0 then
                    game.print("Picked up ground item2 " .. count .. " " .. entity)
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
        radius=0.702,
        force="player"
    }
    game.print("Found " .. #player_entities .. " placed entities") -- Debug

    local ground_items = surface.find_entities_filtered{
        name="item-on-ground",
        position=position,
        radius=0.702
    }
    game.print("Found " .. #ground_items .. " ground items") -- Debug

    -- Try to pick up placed entities first, if any exist
    if #player_entities > 0 then
        success = pickup_placed_entity(player_entities)
        if success then
            game.print("Successfully picked up placed entity")--, {skip=false}) -- Debug
            return {}
        end
    end

    -- Only try ground items if we haven't succeeded with placed entities
    if not success and #ground_items > 0 then
        success = pickup_ground_item(ground_items)
        if success then
            game.print("Successfully picked up ground item") -- Debug
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