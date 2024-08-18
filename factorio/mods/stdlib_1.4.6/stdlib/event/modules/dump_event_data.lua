local function setup_event_data(Event, valid_event_id, id_to_name)
    local function get_registered_counts(reg_type)
        local core, nth, on_events = 0, 0, 0
        local events = {}
        for id, registry in pairs(Event.registry) do
            if tonumber(id) then
                if id < 0 then
                    nth = nth + #registry
                else
                    on_events = on_events + #registry
                end
            else
                if Event.core_events[id] then
                    core = core + #registry
                else
                    on_events = on_events + #registry
                end
            end
            local name = id_to_name(id)
            events[name] = (events[name] or 0) + #registry
        end
        local all = {
            core = core,
            events = events,
            nth = nth,
            on_events = on_events,
            total = on_events + nth + core
        }
        return reg_type and all[reg_type] or all
    end

    local function dump_data()
        local event_data = {
            count_data = get_registered_counts(),
            event_order = script.get_event_order(),
            custom_events = Event.custom_events,
            registry = Event.registry,
            options = {
                protected_mode = Event.options.protected_mode,
                force_crc = Event.options.force_crc,
                inspect_event = Event.options.inspect_event,
                skip_valid = Event.options.skip_valid
            }
        }
        local registry, factorio_events = {}, {}
        for event, data in pairs(Event.registry) do
            registry['[' .. event .. '] ' .. id_to_name(event)] = data
            if valid_event_id(event) then
                factorio_events['[' .. event .. '] ' .. id_to_name(event)] = Event.script.get_event_handler(event)
            end
        end
        game.write_file(Event.get_file_path('Event/Event.lua'), 'return ' .. inspect(event_data))
        game.write_file(Event.get_file_path('Event/Event.registry.lua'), 'return ' .. inspect(registry, {longkeys = true, arraykeys = true}))
        game.write_file(Event.get_file_path('Event/Factorio.registry.lua'), 'return ' .. inspect(factorio_events, {longkeys = true, arraykeys = true}))
    end
    return dump_data
end

return setup_event_data
