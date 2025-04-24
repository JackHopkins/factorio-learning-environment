global.actions.clear_entities = function(player_index)
    local function clear_area_of_entities(player, area, force_filter)
        local surface = player.surface
        local entities = surface.find_entities_filtered{
            area = area,
            force = force_filter,
            type = {
                "accumulator", "ammo-turret", "arithmetic-combinator", "artillery-turret",
                "assembling-machine", "beacon", "boiler", "constant-combinator",
                "container", "curved-rail", "decider-combinator", "electric-pole",
                "electric-turret", "fluid-turret", "furnace", "gate", "generator",
                "heat-interface", "heat-pipe", "inserter", "lab", "lamp",
                "land-mine", "linked-belt", "linked-container", "loader",
                "loader-1x1", "market", "mining-drill", "offshore-pump",
                "pipe", "pipe-to-ground", "power-switch", "programmable-speaker",
                "pump", "radar", "rail-chain-signal", "rail-signal",
                "reactor", "roboport", "rocket-silo", "solar-panel",
                "splitter", "storage-tank", "straight-rail", "train-stop",
                "transport-belt", "underground-belt", "wall"
            }
        }

        for _, entity in ipairs(entities) do
            if entity and entity.valid and entity ~= player then
                entity.destroy()
            end
        end

        -- Clear dropped items separately
        local dropped_items = surface.find_entities_filtered{
            area = area,
            name = "item-on-ground"
        }
        for _, item in ipairs(dropped_items) do
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
    local player = global.agent_characters[player_index]
    local area = {
        {player.position.x - 1000, player.position.y - 1000},
        {player.position.x + 1000, player.position.y + 1000}
    }

    -- Clear player force entities
    clear_area_of_entities(player, area, player.force)
    -- Clear neutral force entities
    clear_area_of_entities(player, area, "neutral")

    reset_character_inventory(player)
    player.force.reset()
    return 1
end