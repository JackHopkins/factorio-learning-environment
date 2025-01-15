global.actions.get_research_progress = function(player_index, technology_name)
    local player = game.get_player(player_index)
    local force = player.force

    -- If no technology specified, use current research
    if not technology_name then
        if not force.current_research then
            error("\"No research currently in progress\"")
        end
        technology_name = force.current_research.name
    end

    -- Get the technology
    local tech = force.technologies[technology_name]
    if not tech then
        error(string.format("\"Technology %s doesn't exist\"", technology_name))
    end

    -- Get progress info
    local is_current = force.current_research and force.current_research.name == technology_name
    local progress = 0

    if is_current then
        progress = force.research_progress
    elseif tech.researched then
        progress = 1
    end

    -- Collect ingredients info
    local ingredients = {}
    local units_required = tech.research_unit_count

    for _, ingredient in pairs(tech.research_unit_ingredients) do
        table.insert(ingredients, {
            name = "\""..ingredient.name.."\"",
            count = ingredient.amount * units_required,
            type = ingredient.type
        })
    end

    -- Return structured response
    return ingredients
end