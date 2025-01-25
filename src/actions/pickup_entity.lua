global.actions.pickup_entity = function(player_index, x, y, entity)
    local player = game.get_player(player_index)

    local position = {x=x, y=y}--{x=player.position.x+x, y=player.position.y+y}
    local surface = player.surface

    local success = 0

    -- Function to pick up and add entity to player's inventory
    local function pickup(entities)
        local success = 0
        for _, ent in pairs(entities) do
            if ent.valid then
                if ent.name == entity then
                    local products = ent.prototype.mineable_properties.products
                    if products ~= nil then
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
                        game.print("Picked up "..ent.name)
                        pcall(ent.destroy{raise_destroy=false, do_cliff_correction=false})
                        return true
                    end
                    end
                end
            end
        return false
    end
    -- Attempt to pick up
    player_entities = surface.find_entities_filtered{name=entity, position=position, radius=0.702, force = "player"}
    if #player_entities == 0 then
        error("Couldn't find "..entity.." at position ("..x..", "..y..") to pick up.")
    end
    success = pickup(player_entities)

    if not success then
        error("Could not pick up")
    end

    return {}
end
