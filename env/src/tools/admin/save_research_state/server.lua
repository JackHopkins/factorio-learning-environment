global.actions.save_research_state = function(player_index)
    local player = global.agent_characters[player_index]
    local force = player.force

    -- Helper to serialize technology state
    local function serialize_technology(tech)
        local prerequisites = {}
        for name, _ in pairs(tech.prerequisites) do
            table.insert(prerequisites, "\""..name.."\"")
        end

        local ingredients = {}
        for _, ingredient in pairs(tech.research_unit_ingredients) do
            table.insert(ingredients, {
                name = "\""..ingredient.name.."\"",
                amount = ingredient.amount
            })
        end

        return {
            name = "\""..tech.name.."\"",
            researched = tech.researched,
            enabled = tech.enabled,
            -- visible = tech.visible,
            level = tech.level,
            research_unit_count = tech.research_unit_count,
            research_unit_energy = tech.research_unit_energy,
            prerequisites = prerequisites,
            ingredients = ingredients,
            --saved_progress = saved_progress  -- This will be nil if no progress is saved
        }
    end

    local research_state = {
        technologies = {},
        current_research = nil,
        research_progress = 0,
        research_queue = {},
        progress = {}
    }

    -- Save all technology states
    for name, tech in pairs(force.technologies) do
        research_state.technologies[name] = serialize_technology(tech)
    end

    -- Save current research and progress
    if force.current_research then
        research_state.current_research = "\""..force.current_research.name.."\""
        research_state.research_progress = force.research_progress

        research_state.progress[force.current_research.name] = force.research_progress or 0
    end

    -- Save research queue if it exists
    if force.research_queue then
        for _, tech in pairs(force.research_queue) do
            table.insert(research_state.research_queue, "\""..tech.name.."\"")
        end
    end
    return research_state
end