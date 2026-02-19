storage.actions.clear_entities = function(player_index)
    -- Clear all entities on the entire surface for a given force
    -- No area limitation to ensure complete test isolation
    local function clear_surface_entities(surface, force_filter, player_character)
        local entities = surface.find_entities_filtered{
            force = force_filter,
            type = {
                -- Power and electricity
                "accumulator", "electric-pole", "power-switch", "solar-panel", "reactor",
                -- Combat/turrets
                "ammo-turret", "electric-turret", "fluid-turret", "artillery-turret", "land-mine",
                -- Circuit network
                "arithmetic-combinator", "constant-combinator", "decider-combinator", "programmable-speaker",
                -- Production
                "assembling-machine", "beacon", "boiler", "furnace", "generator", "lab",
                "mining-drill", "offshore-pump", "rocket-silo",
                -- Storage
                "container", "logistic-container", "linked-container", "infinity-container",
                -- Fluid handling
                "pipe", "pipe-to-ground", "pump", "storage-tank", "infinity-pipe",
                -- Logistics
                "inserter", "transport-belt", "underground-belt", "splitter", "loader", "loader-1x1", "linked-belt",
                -- Rail
                "curved-rail", "straight-rail", "rail-chain-signal", "rail-signal", "train-stop",
                "locomotive", "cargo-wagon", "fluid-wagon", "artillery-wagon",
                -- Heat
                "heat-interface", "heat-pipe",
                -- Defense
                "gate", "wall", "radar",
                -- Robots
                "roboport", "construction-robot", "logistic-robot",
                -- Vehicles
                "car", "spider-vehicle",
                -- Misc
                "lamp", "market", "simple-entity-with-owner"
            }
        }

        for _, entity in ipairs(entities) do
            if entity and entity.valid and entity ~= player_character then
                entity.destroy()
            end
        end

        -- Clear dropped items on entire surface
        local dropped_items = surface.find_entities_filtered{
            force = force_filter,
            name = "item-on-ground"
        }
        for _, item in ipairs(dropped_items) do
            if item and item.valid then
                item.destroy()
            end
        end

        -- Also clear neutral dropped items (they don't have force filter)
        local neutral_items = surface.find_entities_filtered{
            name = "item-on-ground"
        }
        for _, item in ipairs(neutral_items) do
            if item and item.valid then
                item.destroy()
            end
        end
    end

    local function reset_character_inventory(player)
        for inventory_id, inventory in pairs(defines.inventory) do
            local character_inventory = player.get_inventory(inventory)
            if character_inventory then
                character_inventory.clear()
            end
        end
    end

    -- Main execution
    local player = storage.agent_characters[player_index]
    local surface = player.surface

    -- Clear player force entities on entire surface (no area limitation)
    clear_surface_entities(surface, player.force, player)
    -- Clear neutral force entities on entire surface
    clear_surface_entities(surface, "neutral", player)

    reset_character_inventory(player)
    -- Note: technology/force management is handled by reset/server.lua, not here.
    -- Clearing entities should not reset research progress.
    return 1
end