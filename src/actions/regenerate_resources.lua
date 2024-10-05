global.actions.regenerate_resources = function(player_index)
    local player = game.get_player(player_index)
    local surface = player.surface
    for _, ore in pairs(surface.find_entities_filtered({type="resource"})) do
        ore.amount = 10000
    end
    player.force.reset()
end

global.actions.regenerate_resources2 = function(player_index)
    local player = game.players[player_index]

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