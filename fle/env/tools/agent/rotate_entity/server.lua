storage.actions.rotate_entity = function(player_index, x, y, direction, entity)
    local character = storage.agent_characters[player_index]
    local lua_player = game.players[player_index]  -- Get the actual LuaPlayer object
    local position = {x=x, y=y}
    local surface = character.surface

    local function table_contains(tbl, element)
        for _, value in ipairs(tbl) do
            if value == element then
                return true
            end
        end
        return false
    end

    local closest_distance = math.huge
    local closest_entity = nil
    local area = {{position.x - 0.5, position.y - 0.5}, {position.x + 0.5, position.y + 0.5}}
    local buildings = surface.find_entities_filtered{area = area, force = "player", name=entity}

    -- Find the closest building (skip rotatable check for assemblers, handled below)
    for _, building in ipairs(buildings) do
        if building.name ~= 'character' then
            local distance = ((position.x - building.position.x) ^ 2 + (position.y - building.position.y) ^ 2) ^ 0.5
            if distance < closest_distance then
                closest_distance = distance
                closest_entity = building
            end
        end
    end

    if closest_entity == nil then
        error("No entity to rotate at the given coordinates.")
    end

    -- Factorio 2.0 uses 16-direction system: 0 (north), 4 (east), 8 (south), 12 (west)
    local valid_directions = {0, 4, 8, 12}

    if not table_contains(valid_directions, direction) then
        error("Invalid direction " .. direction .. " provided. Please use 0 (north), 4 (east), 8 (south), or 12 (west).")
    end

    local target_direction = storage.utils.get_entity_direction(closest_entity.name, direction)

    -- For assembling machines in Factorio 2.0, rotation is complex due to fluid_boxes_off_when_no_fluid_recipe
    -- Without the fle-compat mod, assemblers without a fluid recipe cannot be rotated via .rotate(),
    -- and assemblers with a fluid recipe use .rotate() which rotates both entity and fluid boxes.
    -- We always use destroy/recreate for assemblers to handle both cases reliably.
    if closest_entity.type == "assembling-machine" then
        local current = closest_entity.direction
        local target = target_direction

        if current ~= target then
            -- Save entity state
            local saved_name = closest_entity.name
            local saved_position = closest_entity.position
            local saved_recipe = closest_entity.get_recipe()
            local saved_recipe_name = saved_recipe and saved_recipe.name or nil
            local saved_health = closest_entity.health
            local saved_force = closest_entity.force

            -- Save inventory contents
            local saved_inputs = {}
            local saved_outputs = {}
            local saved_modules = {}

            local input_inv = closest_entity.get_inventory(defines.inventory.assembling_machine_input)
            if input_inv then
                for i = 1, #input_inv do
                    local stack = input_inv[i]
                    if stack and stack.valid_for_read then
                        table.insert(saved_inputs, {name = stack.name, count = stack.count})
                    end
                end
            end

            local output_inv = closest_entity.get_inventory(defines.inventory.assembling_machine_output)
            if output_inv then
                for i = 1, #output_inv do
                    local stack = output_inv[i]
                    if stack and stack.valid_for_read then
                        table.insert(saved_outputs, {name = stack.name, count = stack.count})
                    end
                end
            end

            local modules_inv = closest_entity.get_inventory(defines.inventory.assembling_machine_modules)
            if modules_inv then
                for i = 1, #modules_inv do
                    local stack = modules_inv[i]
                    if stack and stack.valid_for_read then
                        table.insert(saved_modules, {name = stack.name, count = stack.count})
                    end
                end
            end

            -- Destroy the entity
            closest_entity.destroy()

            -- Create new entity with target direction
            local new_entity = surface.create_entity{
                name = saved_name,
                position = saved_position,
                direction = target,
                force = saved_force,
                create_build_effect_smoke = false
            }

            if new_entity then
                -- Set the health
                new_entity.health = saved_health

                -- Set recipe (Factorio 2.0: set_recipe takes recipe, quality - not direction)
                if saved_recipe_name then
                    new_entity.set_recipe(saved_recipe_name)
                    -- Factorio 2.0: set_recipe may change the entity direction for fluid box alignment
                    -- Force the direction back to our target after setting recipe
                    if new_entity.direction ~= target then
                        new_entity.direction = target
                    end
                end

                -- Restore inventories
                local new_input_inv = new_entity.get_inventory(defines.inventory.assembling_machine_input)
                if new_input_inv then
                    for _, item in pairs(saved_inputs) do
                        new_input_inv.insert(item)
                    end
                end

                local new_output_inv = new_entity.get_inventory(defines.inventory.assembling_machine_output)
                if new_output_inv then
                    for _, item in pairs(saved_outputs) do
                        new_output_inv.insert(item)
                    end
                end

                local new_modules_inv = new_entity.get_inventory(defines.inventory.assembling_machine_modules)
                if new_modules_inv then
                    for _, item in pairs(saved_modules) do
                        new_modules_inv.insert(item)
                    end
                end

                closest_entity = new_entity
            end
        end
    else
        -- For other entities, try direct assignment first (works for most entities)
        closest_entity.direction = target_direction

        -- If direction didn't change, try using the rotate() method
        if closest_entity.direction ~= target_direction then
            local current = closest_entity.direction
            local target = target_direction
            local rotations_needed = ((target - current + 16) % 16) / 4

            for i = 1, rotations_needed do
                if closest_entity.rotate then
                    closest_entity.rotate()
                end
            end
        end
    end

    -- Ensure the entity is properly aligned to the grid
    local entity_position = closest_entity.position
    local aligned_position = {
        x = math.floor(entity_position.x),
        y = math.floor(entity_position.y)
    }

    if entity_position.x ~= aligned_position.x or entity_position.y ~= aligned_position.y then
        closest_entity.teleport(aligned_position)
    end

    local serialized = storage.utils.serialize_entity(closest_entity)
    return serialized
end