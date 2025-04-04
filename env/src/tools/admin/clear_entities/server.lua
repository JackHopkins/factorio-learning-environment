global.actions.clear_entities = function(player_index)
    local function clear_area_of_entities(character, area, force_filter)
        local surface = character.surface
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
            if entity and entity.valid and entity ~= character then
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

    local function reset_character_inventory(character)
        for inventory_id, inventory in pairs(defines.inventory) do
            local character_inventory = character.get_inventory(inventory)
            if character_inventory then
                character_inventory.clear()
            end
        end
    end

    -- Main execution
    local character = game.get_player(player_index).character
    if not character then return end

    local area = {
        {character.position.x - 1000, character.position.y - 1000},
        {character.position.x + 1000, character.position.y + 1000}
    }

    -- Clear player force entities
    clear_area_of_entities(character, area, character.force)
    -- Clear neutral force entities
    clear_area_of_entities(character, area, "neutral")

    reset_character_inventory(character)
    character.force.reset()
    return 1
end