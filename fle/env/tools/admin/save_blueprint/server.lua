global.actions.save_blueprint = function(player_index)
    local player = global.agent_characters[player_index]
    local force = player.force
    if not force then
        return nil, "Force not found"
    end

    local surface = game.surfaces[1] -- Get primary surface
    local entities = surface.find_entities_filtered{force = force}

    if #entities == 0 then
        return nil, "No entities found for force"
    end

    -- Calculate bounding box containing all force entities
    local min_x, min_y = math.huge, math.huge
    local max_x, max_y = -math.huge, -math.huge

    for _, entity in pairs(entities) do
        local pos = entity.position
        min_x = math.min(min_x, pos.x)
        min_y = math.min(min_y, pos.y)
        max_x = math.max(max_x, pos.x)
        max_y = math.max(max_y, pos.y)
    end

    -- Calculate center point of the blueprint
    local center_x = (min_x + max_x) / 2
    local center_y = (min_y + max_y) / 2

    -- Add some padding to the box
    local area = {
        left_top = {x = min_x - 1, y = min_y - 1},
        right_bottom = {x = max_x + 1, y = max_y + 1}
    }

     -- Create blueprint item stack
    local bp = player.cursor_stack
    bp.set_stack({name = "blueprint"})
    bp.label = "Saved Entities"
    bp.allow_manual_label_change = true

   -- Create blueprint from area
    bp.create_blueprint{
        surface = surface,
        force = force,
        area = area,
        include_entities = true,
        include_modules = true,
        include_station_names = true,
        include_trains = true,
        include_fuel = true
    }

    local stack_string = bp.export_stack()

    -- Clear cursor and delete blueprint
    bp.clear()

    return dump({blueprint='\"'..stack_string..'\"', center_x=center_x, center_y=center_y})
end