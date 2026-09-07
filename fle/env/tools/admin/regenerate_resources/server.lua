storage.actions.regenerate_resources = function(player_index)
    local player = storage.agent_characters[player_index]
    local surface = player.surface

    local function resource_key(name, position)
        return name .. ":" .. tostring(position.x) .. ":" .. tostring(position.y)
    end

    -- Lab scenarios contain manually placed resource patches. Record their
    -- original entities before an episode can mine them away; map-generator
    -- regeneration cannot restore these scenario-authored patches.
    if not storage.initial_resources then
        storage.initial_resources = {}
        for _, resource in pairs(surface.find_entities_filtered({type="resource"})) do
            local key = resource_key(resource.name, resource.position)
            storage.initial_resources[key] = {
                name = resource.name,
                position = {x = resource.position.x, y = resource.position.y},
                amount = resource.amount
            }
        end
    end

    local resources_by_key = {}
    for _, resource in pairs(surface.find_entities_filtered({type="resource"})) do
        resources_by_key[resource_key(resource.name, resource.position)] = resource
    end

    for key, initial in pairs(storage.initial_resources) do
        local resource = resources_by_key[key]
        if resource and resource.valid then
            resource.amount = initial.amount
        else
            surface.create_entity({
                name = initial.name,
                position = initial.position,
                amount = initial.amount
            })
        end
    end
    player.force.reset()
end

storage.actions.regenerate_resources2 = function(player_index)
    local player = storage.agent_characters[player_index]

    local surface = player.surface
    for _, e in pairs(surface.find_entities_filtered{type="resource"}) do
      if e.prototype.infinite_resource then
        e.amount = e.initial_amount
      else
        e.destroy()
      end
    end
    local non_infinites = {}
    for resource, prototype in pairs(game.get_filtered_entity_prototypes{{filter="type", type="resource"}}) do
      if not prototype.infinite_resource then
        table.insert(non_infinites, resource)
      end
    end
    surface.regenerate_entity(non_infinites)
    for _, e in pairs(surface.find_entities_filtered{type="mining-drill"}) do
        e.update_connections()
    end
    return 1
end
