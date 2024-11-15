--- Event Filters
-- Predefined event filter functions
-- @module Event.Filters

local Filters = {
    entity = {},
    player = {},
}

function Filters.on_key(event_key, pattern)
    return function(event)
        local key = event and event[event_key]
        return key and key:match(pattern)
    end
end

function Filters.entity.name(event, pattern)
    local entity = event and (event.created_entity or event.entity)
    return entity.name:match(pattern)
end

function Filters.entity.type(event, pattern)
    local entity = event and (event.created_entity or event.entity)
    return entity.type:match(pattern)
end

function Filters.player.cursor_stack(event, pattern)
    local player = game.get_player(event.player_index)
    local stack = player.cursor_stack
    return stack and stack.valid_for_read and stack.name:match(pattern)
end

function Filters.gui(event, pattern)
    if event.element and event.element.valid then
        local match_str = event.element.name:match(pattern)
        if match_str then
            event.match = match_str
            event.state = event.name == defines.events.on_gui_checked_state_changed and event.element.state or nil
            event.text = event.name == defines.events.on_gui_text_changed and event.element.text or nil
            return match_str
        end
    end
end

return Filters
