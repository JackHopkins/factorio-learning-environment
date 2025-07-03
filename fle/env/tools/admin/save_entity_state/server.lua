-- Helper to ensure all numbers are serializable
local function serialize_number(num)
    if num == math.huge then
        return "inf"
    elseif num == -math.huge then
        return "-inf"
    else
        return tostring(num)
    end
end

-- Helper to serialize position to fixed format
local function serialize_position(pos)
    return {
        x = serialize_number(pos.x),
        y = serialize_number(pos.y)
    }
end

local function serialize_recipe_info(recipe)
    if not recipe then return nil end

    local ingredients = {}
    for _, ingredient in pairs(recipe.ingredients) do
        table.insert(ingredients, {
            name = '"' .. ingredient.name .. '"',
            amount = serialize_number(ingredient.amount),
            type = '"' .. ingredient.type .. '"'
        })
    end

    local products = {}
    for _, product in pairs(recipe.products) do
        table.insert(products, {
            name = '"' .. product.name .. '"',
            amount = serialize_number(product.amount),
            type = '"' .. product.type .. '"',
            probability = product.probability and serialize_number(product.probability) or "1"
        })
    end

    return {
        name = '"' .. recipe.name .. '"',
        category = '"' .. recipe.category .. '"',
        enabled = recipe.enabled,
        energy = serialize_number(recipe.energy),
        ingredients = ingredients,
        products = products
    }
end

-- Main serialization function
global.actions.save_entity_state = function(player_index, distance, player_entities, resource_entities, items_on_ground)
    local surface = global.agent_characters[player_index].surface
    if player_entities then
        entities = surface.find_entities_filtered({area={{-distance, -distance}, {distance, distance}}, force=global.agent_characters[player_index].force})
    else
        if resource_entities then
            entities = surface.find_entities({{-distance, -distance}, {distance, distance}})
        else
            entities = surface.find_entities_filtered({area={{-distance, -distance}, {distance, distance}}, force=global.agent_characters[player_index].force})
        end
    end

    -- Always get items on ground if requested
    if items_on_ground then
        local ground_items = surface.find_entities_filtered({
            area = {{-distance, -distance}, {distance, distance}},
            name = "item-on-ground"
        })
        -- Merge the arrays
        for _, item in pairs(ground_items) do
            table.insert(entities, item)
        end
    end

    local entity_states = {}
    local entity_array = {}
    for _, entity in pairs(entities) do

        -- Serialize inventories by type
        local inventory_defines = {
            chest = defines.inventory.chest,
            furnace_source = defines.inventory.furnace_source,
            furnace_result = defines.inventory.furnace_result,
            fuel = defines.inventory.fuel,
            burnt_result = defines.inventory.burnt_result,
            assembling_machine_input = defines.inventory.assembling_machine_input,
            assembling_machine_output = defines.inventory.assembling_machine_output,
            turret_ammo = defines.inventory.turret_ammo,
            lab_input = defines.inventory.lab_input,
            lab_modules = defines.inventory.lab_modules,
            assembling_machine_modules = defines.inventory.assembling_machine_modules
        }

        if entity.name == "item-on-ground" then
            -- Capture the item details
            local item = entity.stack
            if item and item.valid then
                local state = {
                    name = '\"item-on-ground\"',
                    type = '"' .. item.name .. '"',
                    count = serialize_number(item.count),
                    position = serialize_position(entity.position),
                }
                table.insert(entity_array, state)
            end
        elseif entity.name ~= "character" then
            local state = {
                name = '"' .. entity.name .. '"',
                position = serialize_position(entity.position),
                direction = entity.direction,
                entity_number = entity.unit_number or -1,
                type = '"' .. entity.type .. '"',
                health = serialize_number(entity.health),
                energy = serialize_number(entity.energy or 0),
                active = entity.active,
                status = '"' .. (global.entity_status_names[entity.status] or "normal") .. '"',
                warnings = {},
                inventories = {}
            }

            -- Add any warnings
            for _, warning in pairs(get_issues(entity) or {}) do
                table.insert(state.warnings, '"' .. warning .. '"')
            end

            -- Handle dimensions
            local prototype = game.entity_prototypes[entity.name]
            if prototype then
                local collision_box = prototype.collision_box
                state.dimensions = {
                    width = serialize_number(math.abs(collision_box.right_bottom.x - collision_box.left_top.x)),
                    height = serialize_number(math.abs(collision_box.right_bottom.y - collision_box.left_top.y))
                }
                state.tile_dimensions = {
                    tile_width = serialize_number(prototype.tile_width),
                    tile_height = serialize_number(prototype.tile_height)
                }
            end

            for name, define in pairs(inventory_defines) do
                local inventory = entity.get_inventory(define)
                if inventory then
                    state.inventories[name] = {}
                    -- Get contents with proper item names
                    local contents = inventory.get_contents()
                    for item_name, count in pairs(contents) do
                        if item_name and item_name ~= "" then  -- Ensure valid item name
                            state.inventories[name][tostring(item_name)] = serialize_number(count)
                        end
                    end
                end
            end

            -- Handle fluids
            if entity.fluidbox then
                state.fluid_box = {}
                for i = 1, #entity.fluidbox do
                    local fluid = entity.fluidbox[i]
                    if fluid then
                        table.insert(state.fluid_box, {
                            name = '"' .. fluid.name .. '"',
                            amount = serialize_number(fluid.amount),
                            temperature = serialize_number(fluid.temperature)
                        })
                    end
                end
            end

            -- Handle burner state
            if entity.burner then
                state.burner = {
                    currently_burning = entity.burner.currently_burning and
                            '"' .. entity.burner.currently_burning.name .. '"' or nil,
                    remaining_burning_fuel = serialize_number(entity.burner.remaining_burning_fuel or 0),
                    heat = serialize_number(entity.burner.heat or 0)
                }

                -- Add burner inventory with proper item names
                local burner_inventory = entity.burner.inventory
                if burner_inventory then
                    state.burner.inventory = {}
                    local contents = burner_inventory.get_contents()
                    --game.print("get_contents() results:")
                    for item_name, count in pairs(contents) do
                        if item_name and item_name ~= "" then  -- Ensure valid item name
                            --game.print("Item: '" .. tostring(item_name) .. "' Count: " .. tostring(count))
                            --state.burner.inventory['\"' .. tostring(item_name) .. '\"'] = serialize_number(count)
                            state.burner.inventory[tostring(item_name)] = serialize_number(count)
                        end
                    end
                end
            end

            -- Handle recipe - only for crafting machines and furnaces
            if (entity.type == "assembling-machine" or
                    entity.type == "furnace" or
                    entity.type == "rocket-silo") and
                    entity.get_recipe then
                local recipe = entity.get_recipe()
                if recipe then
                    state.recipe = serialize_recipe_info(recipe)
                end
            end

            -- Handle specific entity types
            --if entity.type == "transport-belt" then
            --    state.input_position = serialize_position(entity.position)
            --    state.output_position = serialize_position(entity.position)
            --    -- Add belt contents
            --    state.inventory = {}
            --    for name, count in pairs(entity.get_transport_line(1).get_contents()) do
            --        state.inventory[tostring(name)] = serialize_number(count)
            --    end
            if entity.type == "transport-belt" then
                --state.input_position = serialize_position(entity.input_position)
                --state.output_position = serialize_position(entity.output_position)
                state.position = serialize_position(entity.position)

                -- Store contents of each transport line separately
                state.transport_lines = {}

                -- Front line (line 1)
                state.transport_lines[1] = {}
                local contents1 = entity.get_transport_line(1).get_contents()
                for name, count in pairs(contents1) do
                    state.transport_lines[1][tostring(name)] = serialize_number(count)
                end

                -- Back line (line 2)
                state.transport_lines[2] = {}
                local contents2 = entity.get_transport_line(2).get_contents()
                for name, count in pairs(contents2) do
                    state.transport_lines[2][tostring(name)] = serialize_number(count)
                end

                -- Total counts (for backwards compatibility)
                state.inventory = {}
                for name, count in pairs(contents1) do
                    state.inventory[tostring(name)] = serialize_number(count)
                end
                for name, count in pairs(contents2) do
                    local existing = state.inventory[tostring(name)]
                    if existing then
                        state.inventory[tostring(name)] = serialize_number(tonumber(existing) + count)
                    else
                        state.inventory[tostring(name)] = serialize_number(count)
                    end
                end

            elseif entity.type == "inserter" then
                state.pickup_position = serialize_position(entity.pickup_position)
                state.drop_position = serialize_position(entity.drop_position)

            elseif entity.type == "splitter" then
                -- Calculate splitter positions based on orientation
                local x, y = entity.position.x, entity.position.y
                state.input_positions = {}
                state.output_positions = {}
                local lateral_offset = 0.5

                if entity.direction == defines.direction.north then
                    state.input_positions = {
                        serialize_position({x = x - lateral_offset, y = y + 1}),
                        serialize_position({x = x + lateral_offset, y = y + 1})
                    }
                    state.output_positions = {
                        serialize_position({x = x - lateral_offset, y = y - 1}),
                        serialize_position({x = x + lateral_offset, y = y - 1})
                    }
                elseif entity.direction == defines.direction.south then
                    state.input_positions = {
                        serialize_position({x = x + lateral_offset, y = y - 1}),
                        serialize_position({x = x - lateral_offset, y = y - 1})
                    }
                    state.output_positions = {
                        serialize_position({x = x + lateral_offset, y = y + 1}),
                        serialize_position({x = x - lateral_offset, y = y + 1})
                    }
                elseif entity.direction == defines.direction.east then
                    state.input_positions = {
                        serialize_position({x = x - 1, y = y - lateral_offset}),
                        serialize_position({x = x - 1, y = y + lateral_offset})
                    }
                    state.output_positions = {
                        serialize_position({x = x + 1, y = y - lateral_offset}),
                        serialize_position({x = x + 1, y = y + lateral_offset})
                    }
                elseif entity.direction == defines.direction.west then
                    state.input_positions = {
                        serialize_position({x = x + 1, y = y + lateral_offset}),
                        serialize_position({x = x + 1, y = y - lateral_offset})
                    }
                    state.output_positions = {
                        serialize_position({x = x - 1, y = y + lateral_offset}),
                        serialize_position({x = x - 1, y = y - lateral_offset})
                    }
                end

                -- Serialize splitter inventories
                state.inventory = {}
                for i = 1, 2 do
                    state.inventory[i] = {}
                    for name, count in pairs(entity.get_transport_line(i).get_contents()) do
                        state.inventory[i][tostring(name)] = serialize_number(count)
                    end
                end

            elseif entity.type == "mining-drill" then
                state.drop_position = serialize_position(entity.drop_position)

            elseif entity.type == "boiler" then
                -- Add connection points
                local x, y = entity.position.x, entity.position.y
                if entity.direction == defines.direction.north then
                    state.connection_points = {
                        serialize_position({x = x - 2, y = y + 0.5}),
                        serialize_position({x = x + 2, y = y + 0.5})
                    }
                    state.steam_output_point = serialize_position({x = x, y = y - 2})
                elseif entity.direction == defines.direction.south then
                    state.connection_points = {
                        serialize_position({x = x - 2, y = y - 0.5}),
                        serialize_position({x = x + 2, y = y - 0.5})
                    }
                    state.steam_output_point = serialize_position({x = x, y = y + 2})
                elseif entity.direction == defines.direction.east then
                    state.connection_points = {
                        serialize_position({x = x - 0.5, y = y - 2}),
                        serialize_position({x = x - 0.5, y = y + 2})
                    }
                    state.steam_output_point = serialize_position({x = x + 2, y = y})
                elseif entity.direction == defines.direction.west then
                    state.connection_points = {
                        serialize_position({x = x + 0.5, y = y - 2}),
                        serialize_position({x = x + 0.5, y = y + 2})
                    }
                    state.steam_output_point = serialize_position({x = x - 2, y = y})
                end
            end

            table.insert(entity_array, state)
        else
            -- Find the index of this character in global.agent_characters
            agent_index = -1
            for idx, agent in pairs(global.agent_characters) do
                if agent == entity then
                    agent_index = idx
                    break
                end
            end
            local state = {
                name = '"' .. entity.name .. '"',
                position = serialize_position(entity.position),
                direction = entity.direction,
                entity_number = entity.unit_number or -1,
                inventories = {},
                agent_index = agent_index,
                color = {
                    r = serialize_number(entity.color.r),
                    g = serialize_number(entity.color.g),
                    b = serialize_number(entity.color.b),
                    a = serialize_number(entity.color.a)
                }
            }
            -- Get the character's inventory using defines
            local inventory = entity.get_inventory(defines.inventory.character_main)

            if inventory then
                state.inventory = {}
                local contents = inventory.get_contents()
                for item_name, count in pairs(contents) do
                    if item_name and item_name ~= "" then
                        state.inventory[tostring(item_name)] = serialize_number(count)
                    end
                end
            end
            table.insert(entity_array, state)
        end
    end
    return entity_array
end
