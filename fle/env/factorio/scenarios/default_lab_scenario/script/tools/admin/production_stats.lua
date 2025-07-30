global.actions.production_stats = function(player)
    local production_diff = {}
    local consumption_diff = {}
    local harvested_items = global.harvested_items
    local crafted_items = global.crafted_items
    -- Get total production counts for force
    local force = game.forces.player

    local item_input_counts = force.item_production_statistics.input_counts
    local item_production_counts = force.item_production_statistics.output_counts
    local fluid_input_counts = force.fluid_production_statistics.input_counts
    local fluid_production_counts = force.fluid_production_statistics.output_counts

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

global.actions.reset_production_stats = function(player)
    local force = game.forces.player
    -- Reset item statistics
    force.item_production_statistics.clear()

    -- Reset fluid statistics
    force.fluid_production_statistics.clear()

    global.harvested_items = {}
    global.crafted_items = {}
end

