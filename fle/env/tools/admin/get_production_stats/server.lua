storage.actions.production_stats = function(player)
    local production_diff = {}
    local consumption_diff = {}
    local harvested_items = storage.harvested_items
    local crafted_items = storage.crafted_items
    -- Get total production counts for force
    local force = game.forces.player
    local surface = game.surfaces[1]

    -- Factorio 2.0: production_statistics is now a method requiring surface parameter
    local item_stats = force.get_item_production_statistics(surface)
    local fluid_stats = force.get_fluid_production_statistics(surface)

    local item_input_counts = item_stats.input_counts
    local item_production_counts = item_stats.output_counts
    local fluid_input_counts = fluid_stats.input_counts
    local fluid_production_counts = fluid_stats.output_counts

    for name, count in pairs(item_input_counts) do
        consumption_diff[name] = count
    end

    for name, count in pairs(item_production_counts) do
        production_diff[name] = count
    end

    for name, count in pairs(fluid_input_counts) do
        consumption_diff[name] = count
    end

    for name, count in pairs(fluid_production_counts) do
        production_diff[name] = count
    end
    return {
        output = consumption_diff,
        input = production_diff,
        harvested = harvested_items,
        crafted = crafted_items
    }
end

storage.actions.reset_production_stats = function(player)
    local force = game.forces.player
    local surface = game.surfaces[1]

    -- Factorio 2.0: production_statistics is now a method requiring surface parameter
    -- Reset item statistics
    force.get_item_production_statistics(surface).clear()

    -- Reset fluid statistics
    force.get_fluid_production_statistics(surface).clear()

    storage.harvested_items = {}
    storage.crafted_items = {}
end

