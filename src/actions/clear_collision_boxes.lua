global.actions.clear_collision_boxes = function(player_index)
    -- Clean up temporary entities
    local clearance_entities = global.clearance_entities[player_index]
    if not clearance_entities then return end

    -- Destroy all created entities
    for _, entity in pairs(clearance_entities) do
        if entity.valid then
            entity.destroy()
        end
    end
end