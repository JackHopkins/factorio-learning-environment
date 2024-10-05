global.actions.nearest_buildable = function(player_index, entity_name)
    local player = game.get_player(player_index)

    local function is_buildable_position(surface, position, entity_name, force)
        local can_place = surface.can_place_entity{
            name = entity_name,
            position = position,
            force = force
        }
        return can_place
    end

    local function find_nearest_buildable_position(player, entity_name)
        local surface = player.surface
        local force = player.force
        local position = player.position
        local search_radius = 1
        local max_search_radius = 50
        local search_increment = 1

        while search_radius <= max_search_radius do
            for dx = -search_radius, search_radius, search_increment do
                for dy = -search_radius, search_radius, search_increment do
                    local search_position = {x = position.x + dx, y = position.y + dy}
                    if is_buildable_position(surface, search_position, entity_name, force) then
                        return search_position
                    end
                end
            end
            search_radius = search_radius + search_increment
        end

        error("Could not find a buildable position for the entity: " .. entity_name)
    end

    local function find_nearest_buildable_position2(player, entity_name)
        local surface = player.surface
        local force = player.force
        local position = player.position
        local search_radius = 1
        local max_search_radius = 50
        local search_increment = 1

        while search_radius <= max_search_radius do
            local search_area = {
                {position.x - search_radius, position.y - search_radius},
                {position.x + search_radius, position.y + search_radius}
            }
            local search_positions = surface.find_non_colliding_positions(entity_name, search_area, search_increment)

            if #search_positions > 0 then
                local closest_distance = math.huge
                local closest_position = nil

                for _, search_position in ipairs(search_positions) do
                    if is_buildable_position(surface, search_position, entity_name, force) then
                        local distance = ((position.x - search_position.x) ^ 2 + (position.y - search_position.y) ^ 2) ^ 0.5

                        local resource_present, missing_resource = required_resource_present(entity_name, position, player.surface)

                        local water_tile_present = false
                        local tile = player.surface.get_tile(position)
                        if tile.prototype.collision_mask["ground-tile"] then
                            water_tile_present = true
                        end

                        if resource_present and not (entity == "offshore-pump" and not water_tile_present) then
                            if distance < closest_distance then
                                closest_distance = distance
                                closest_position = search_position
                            end
                        end
                    end
                end

                if closest_position ~= nil then
                    return closest_position
                end
            end

            search_radius = search_radius + search_increment
        end

        error("Could not find a buildable position for the entity: " .. entity_name)
    end

    return find_nearest_buildable_position(player, entity_name)
end