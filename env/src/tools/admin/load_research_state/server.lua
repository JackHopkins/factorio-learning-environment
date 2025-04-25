-- Load research state
global.actions.load_research_state = function(player_index, research_state)
    local player = global.agent_characters[player_index]
    local force = player.force

    -- Reset all research first
    for _, tech in pairs(force.technologies) do
        tech.researched = false
        force.set_saved_technology_progress(tech.name, nil)
        --tech.enabled = false
    end

    -- Apply saved research states
    for name, tech_state in pairs(research_state.technologies) do
        local tech = force.technologies[name]
        if tech then
            tech.researched = tech_state.researched
            tech.enabled = tech_state.enabled
            -- Level might need special handling for infinite research
            if tech.level ~= tech_state.level then
                tech.level = tech_state.level
            end
        end
    end

    for name, progress in pairs(research_state.progress) do
        force.set_saved_technology_progress(name, progress)
    end

    -- Restore current research and progress
    if research_state.current_research then
        --if force.current_research then
        --    force.cancel_current_research()
        --end
        force.add_research(research_state.current_research)
        force.research_progress = research_state.research_progress
    end

    -- Restore research queue if supported
    if force.research_queue_enabled and research_state.research_queue then
        force.research_queue = {}
        for _, tech_name in ipairs(research_state.research_queue) do
            force.add_research(tech_name)
        end
    end

    return true
end