global.actions.clear_collision_boxes = function(player_index)
    local player = global.agent_characters[player_index]
    if not player then return end

    -- Clean up temporary entities
    local clearance_entities = global.clearance_entities[player_index]
    if not clearance_entities then return end

    -- Define search area around player (500 tile radius)
    local search_area = {
        left_top = {
            x = player.position.x - 500,
            y = player.position.y - 500
        },
        right_bottom = {
            x = player.position.x + 500,
            y = player.position.y + 500
        }
    }

    -- Find all simple-entity-with-owner entities in the area
    local entities = player.surface.find_entities_filtered{
        type = "simple-entity-with-owner",
        area = search_area
    }

    -- Destroy found entities
    local count = 0
    for _, entity in pairs(entities) do
        if entity.valid then
            entity.destroy()
            count = count + 1
        end
    end

    -- Destroy all created entities
    for _, entity in pairs(clearance_entities) do
        if entity.valid then
            entity.destroy()
        end
    end
end