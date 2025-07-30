global.actions.set_research = function(player_index, technology_name)
    local player = global.agent_characters[player_index]
    local force = player.force

    -- Helper function to check if technology can be researched
    local function can_research_technology(force, tech_name)
        local tech = force.technologies[tech_name]

        if not tech then
            return false, "technology doesn't exist"
        end

        if tech.researched then
            return false, "technology is already researched"
        end

        if not tech.enabled then
            return false, "technology is not enabled"
        end

        -- Check prerequisites
        for _, prerequisite in pairs(tech.prerequisites) do
            if not prerequisite.researched then
                return false, "missing prerequisite - " .. prerequisite.name
            end
        end

        -- Check if we have the required research ingredients
        for _, ingredient in pairs(tech.research_unit_ingredients) do
            if not force.recipes[ingredient.name].enabled then
                return false, "missing required science pack recipe - " .. ingredient.name
            end
        end

        return true, tech
    end

    -- Main logic
    local can_research, result = can_research_technology(force, technology_name)

    if not can_research then
        error(string.format("\"Cannot research %s because %s\"",
            technology_name, result))
    end
    if force.current_research then
        force.set_saved_technology_progress(force.current_research.name, force.research_progress)
    end
    -- Cancel current research if any
    --force.cancel_current_research()

    -- Set new research using add_research
    local success = force.add_research(technology_name)
    if not success then
        error(string.format("\"Failed to start research for %s\"", technology_name))
    end

    -- Collect and return the research ingredients
    local ingredients = {}
    local tech = result  -- Using the technology object from can_research_technology

    -- Get the count of research units needed
    local units_required = tech.research_unit_count

    -- Collect all ingredients and their counts
    for _, ingredient in pairs(tech.research_unit_ingredients) do
        table.insert(ingredients, {
            name = "\""..ingredient.name.."\"",
            count = ingredient.amount * units_required,
            type = ingredient.type
        })
    end

    return ingredients
end