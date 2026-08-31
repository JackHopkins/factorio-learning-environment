storage.actions.set_research = function(player_index, technology_name)
    local player = storage.agent_characters[player_index]
    local force = player.force

    local tech = force.technologies[technology_name]
    if not tech then
        error(string.format("\"Technology %s does not exist\"", technology_name))
    end

    if tech.researched then
        error(string.format("\"Technology %s is already researched\"", technology_name))
    end

    if not tech.enabled then
        error(string.format("\"Technology %s is not enabled\"", technology_name))
    end

    local missing_prerequisites = {}
    for _, prerequisite in pairs(tech.prerequisites or {}) do
        if not prerequisite.researched then
            table.insert(missing_prerequisites, prerequisite.name)
        end
    end

    if #missing_prerequisites > 0 then
        table.sort(missing_prerequisites)
        error(string.format(
            "\"Cannot start research for %s. Missing prerequisites: %s\"",
            technology_name,
            table.concat(missing_prerequisites, ", ")
        ))
    end

    -- Only switch away from valid current research after validation succeeds.
    force.cancel_current_research()

    local success = force.add_research(technology_name)
    if not success then
        error(string.format("\"Failed to start research for %s\"", technology_name))
    end

    -- Collect and return the research ingredients
    local ingredients = {}
    local units_required = tech.research_unit_count

    for _, ingredient in pairs(tech.research_unit_ingredients) do
        table.insert(ingredients, {
            name = "\""..ingredient.name.."\"",
            count = ingredient.amount * units_required,
            type = ingredient.type
        })
    end

    return ingredients
end
