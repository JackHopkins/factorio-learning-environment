global.actions.get_research_progress = function(player_index, technology_name)
    local player = global.agent_characters[player_index]
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

    -- Get progress info and calculate remaining work
    local is_current = force.current_research and force.current_research.name == technology_name
    local progress = 0
    local remaining_units = 0

    if tech.researched then
        -- Already researched technologies need no resources
        return {}
    elseif is_current then
        progress = force.research_progress
        -- Calculate remaining research units based on progress
        remaining_units = math.ceil(tech.research_unit_count * (1 - progress))
    else
        -- Not started technologies need all resources
        remaining_units = tech.research_unit_count
    end

    -- Collect remaining ingredients info
    local ingredients = {}
    for _, ingredient in pairs(tech.research_unit_ingredients) do
        table.insert(ingredients, {
            name = "\""..ingredient.name.."\"",
            count = ingredient.amount * remaining_units,
            type = ingredient.type
        })
    end

    return ingredients
end