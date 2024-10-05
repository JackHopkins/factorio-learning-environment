-- Observe.lua
global.actions.observe_all = function(player_index,
                                      chunk_x,
                                      chunk_y,
                                      localBoundingBox,
                                      field_x,
                                      field_y,
                                      search_radius,
                                      debug,
                                      include)
    local player = game.get_player(player_index)
    player.walking_state = {walking = false, direction = defines.direction.north}
    local inventory = player.get_main_inventory().get_contents()
    local surface = player.surface

    local response = {}

    if include['inventory'] == nil or include['inventory'] then
        response['inventory'] = inventory
    end

    if include['points_of_interest'] == nil or include['points_of_interest'] then
        response['points_of_interest'] = observe_points_of_interest(surface, player, search_radius)
        response['distance_to_points_of_interest'] = global.distances_to_nearest
    end

    if include['local_environment'] == nil or include['local_environment'] then
        --response['local_environment'] = get_local_environment(player,  surface, localBoundingBox, field_x, field_y, debug)
        response['local_environment'] = get_locality(player, surface, localBoundingBox)
    end

    if include['buildable'] == nil or include['buildable'] then
        response['buildable'] = observe_buildable(player, inventory)
    end

    if include['chunk'] == nil or include['chunk'] then
        response['chunk'] = observe_chunk(player, surface, chunk_x, chunk_y)
    end

    if include['position'] == nil or include['position'] then
        response['position'] = player.position
    end

    if include['objective'] == nil or include['objective'] then
        response['objective'] = observe_statistics(player)
    end

    if include['collision'] == nil or include['collision'] then
        response['collision'] = find_passable_tiles(player, localBoundingBox)
    end

    if include['statistics'] == nil or include['statistics'] then
        response['statistics'] = get_productivity(player)
    end

    response['score'] = production_score.get_production_scores()

    return response
end