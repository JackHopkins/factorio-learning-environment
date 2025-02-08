global.alerts = {}

-- Define a function to check if the transport belt is blocked
function is_transport_belt_blocked(entity)
    if entity.type == "transport-belt" then
        local line_1 = entity.get_transport_line(1)
        local line_2 = entity.get_transport_line(2)

        local direction_vector = {
            [0] = {x = 0, y = -1},  -- North
            [2] = {x = 1, y = 0},   -- East
            [4] = {x = 0, y = 1},   -- South
            [6] = {x = -1, y = 0},  -- West
        }

        local dx = direction_vector[entity.direction].x
        local dy = direction_vector[entity.direction].y
        local next_position = {x = entity.position.x + dx, y = entity.position.y + dy}
        local next_entities = entity.surface.find_entities_filtered {
            area = {{next_position.x - 0.5, next_position.y - 0.5}, {next_position.x + 0.5, next_position.y + 0.5}},
        }

        local has_sink = false
        for _, next_entity in ipairs(next_entities) do
            if next_entity.type == "transport-belt" or next_entity.type == "splitter" or next_entity.type == "loader" or (next_entity.type == "assembling-machine" and next_entity.get_recipe()) then
                has_sink = true
                break
            end
        end

        if not has_sink then
            local line_1_moving = line_1 and line_1.get_contents() and not line_1.can_insert_at_back()
            local line_2_moving = line_2 and line_2.get_contents() and not line_2.can_insert_at_back()

            if line_1_moving or line_2_moving then
                return true
            end
        end
    end
    return false
end

-- Define a function to check if an entity is full
function is_full(entity)
    -- Map inventory types to string names
    local inventory_names = {
        [defines.inventory.rocket_silo_rocket] = "rocket",
        [defines.inventory.rocket_silo_input] = "rocket input",
        [defines.inventory.rocket_silo_output] = "rocket output",
        [defines.inventory.rocket_silo_modules] = "rocket modules",
        [defines.inventory.fuel] = "fuel source",
        [defines.inventory.burnt_result] = "burnt result",
        [defines.inventory.assembling_machine_input] = "assembling machine input",
        [defines.inventory.assembling_machine_output] = "assembling machine output",
        [defines.inventory.chest] = "chest",
        [defines.inventory.furnace_source] = "furnace source",
        [defines.inventory.furnace_result] = "furnace result",
    }

    local full_inventories = {}

    -- Iterate over all possible inventory types
    for inventory_id, inventory_name in pairs(inventory_names) do
        local inventory = entity.get_inventory(inventory_id)
        -- Check if the entity has this type of inventory and if it's full
        if inventory and #inventory > 0 then
            for i = 1, #inventory do
                -- Check if the slot is completely filled
                local stack = inventory[i]
                if not stack.valid_for_read or stack.count < stack.prototype.stack_size then  -- Slot is not completely filled
                    goto continue
                end
            end

            -- Determine a more specific message depending on the entity type
            if entity.type == "furnace" then
                if inventory_id == defines.inventory.fuel then
                    inventory_name = "furnace fuel source"
                elseif inventory_id == defines.inventory.furnace_source then
                    inventory_name = "furnace source"
                elseif inventory_id == defines.inventory.furnace_result then
                    inventory_name = "furnace result"
                end
            elseif entity.type == "assembling-machine" then
                if inventory_id == defines.inventory.assembling_machine_input then
                    inventory_name = "assembler input"
                elseif inventory_id == defines.inventory.assembling_machine_output then
                    inventory_name = "assembler output"
                end
            elseif entity.type == "rocket-silo" then
                if inventory_id == defines.inventory.rocket_silo_input then
                    inventory_name = "rocket silo input"
                elseif inventory_id == defines.inventory.rocket_silo_output then
                    inventory_name = "rocket silo output"
                elseif inventory_id == defines.inventory.rocket_silo_modules then
                    inventory_name = "rocket silo modules"
                elseif inventory_id == defines.inventory.rocket then
                    inventory_name = "rocket"
                end
            elseif entity.type == "mining-drill" then
                if inventory_id == defines.inventory.chest then
                    inventory_name = "fuel source"
                end
            elseif entity.type == "chest" then
                if inventory_id == defines.inventory.chest then
                    inventory_name = "chest storage"
                end
            end

            table.insert(full_inventories, inventory_name .. " is full")  -- Add the name of the full inventory to the list

            ::continue::
        end
    end

    return full_inventories
end

function can_mine(entity)
    if entity.type == "mining-drill" then
        -- Check if there's no resource under the drill
        if entity.mining_target == nil then
           return false
        end
    end
    return true
end
-- Define a function to check if the entity is a burner and has fuel
function has_fuel(entity)
    if entity.burner then
        if not entity.burner.currently_burning then
            local fuel_inventory = entity.get_inventory(defines.inventory.fuel)
            for item_name, item_count in pairs(fuel_inventory.get_contents()) do
                local fuel_value = game.item_prototypes[item_name].fuel_value
                if fuel_value and fuel_value > 0 then
                    return true
                end
            end
            return false
        else
            return true
        end
    end
    return true
end

-- Define a function to check if the entity (furnace) has ingredients
function has_ingredients(entity)
    if entity.type == "furnace" and entity.get_recipe() == nil then
        return false
    end
    return true
end
-- Define a function to check if the entity is a drill and has space to output
--function has_output_space(entity)
--    if entity.type == "mining-drill" and entity.mining_target then
--        local output_inventory = entity.get_output_inventory()
--        if output_inventory and output_inventory.is_full() then
--            return false
--        end
--    end
--    if entity.type == "mining-drill" then
--        local resource = entity.surface.find_entities_filtered{position = entity.position, type = "resource"}[1]
--        local output_inventory = entity.get_output_inventory()
--        local drop_position = entity.drop_position
--        local items_on_ground = entity.surface.find_entities_filtered{area = {{drop_position.x - 0.5, drop_position.y - 0.5}, {drop_position.x + 0.5, drop_position.y + 0.5}}, type = "item-entity"}
--
--        if #items_on_ground >= 1 or (resource and output_inventory and not output_inventory.is_empty() and output_inventory and output_inventory.can_insert(resource.prototype.mined_item) == false) then
--            return false
--        end
--    end
--    return true
--end

function has_output_space(entity)
    if entity.status == defines.entity_status.waiting_for_space_in_destination then
        return false
    end
    if entity.type == "mining-drill" and entity.mining_target then
        local output_inventory = entity.get_output_inventory()
        if output_inventory and output_inventory.is_full() then
            return false
        end

        local drop_position = entity.drop_position
        local items_on_ground = entity.surface.find_entities_filtered{
            area = {{drop_position.x - 0.5, drop_position.y - 0.5}, {drop_position.x + 0.5, drop_position.y + 0.5}},
            type = "item-entity"
        }

        local destination_entity = entity.surface.find_entities_filtered{
            position = drop_position,
            type = {"container", "transport-belt", "underground-belt", "splitter"}
        }[1]

        if #items_on_ground >= 1 then
            return false
        elseif destination_entity then
            if destination_entity.type == "container" then
                local chest_inventory = destination_entity.get_inventory(defines.inventory.chest)
                return not chest_inventory.is_full()
            else
                -- For belts, undergrounds, and splitters, assume there's space
                return true
            end
        else
            -- No destination entity, check if output inventory is not empty and can't insert more
            local resource = entity.mining_target
            return not (output_inventory and not output_inventory.is_empty() and
                        output_inventory.can_insert({name = resource.name, count = 1}) == false)
        end
    end
    return true
end

--function has_electricity(entity)
--    if entity.prototype.electric_energy_source_prototype then
--        if entity.electric_drain <= 0 then
--            return false
--        end
--    end
--    return true
--end

function has_electricity(entity)
    if entity.prototype.electric_energy_source_prototype then
        -- Check if the entity is connected to an electric network
        if entity.electric_network_id then
            -- Check if the entity is receiving power
            local energy_usage = entity.energy / entity.electric_buffer_size
            return energy_usage > 0
        else
            -- Entity is not connected to an electric network
            return false
        end
    end
    -- Entity doesn't require electricity
    return true
end

-- Define a function to check if the entity (boiler) has necessary input liquid
function has_input_liquid(entity)
    if entity.type == "boiler" then
        local fluid_box = entity.fluidbox[1]
        if fluid_box == nil or fluid_box.amount <= 0 then
            return false
        end
    end
    -- If the entity is a steam engine, check if it has water
    if entity.type == "generator" then
        local fluid_box = entity.fluidbox[1]
        if fluid_box == nil or fluid_box.amount <= 0 then
            return false
        end
    end
    return true
end

function is_inserter_waiting_for_source(entity)
    if entity.type == "inserter" then
        local pickup_target = entity.pickup_target
        if pickup_target and pickup_target.valid then
            local pickup_inventory = pickup_target.get_inventory(defines.inventory.chest)
            if pickup_inventory and pickup_inventory.is_empty() then
                return true
            end
        end
    end
    return false
end


function get_issues(entity)
    local issues = {}

    if not can_mine(entity) then
        table.insert(issues, "\'nothing to mine\'")
    end
    if not has_fuel(entity) then
        table.insert(issues, "\'out of fuel\'")
    end
    if not has_ingredients(entity) then
        table.insert(issues, "\'no ingredients to smelt\'")
    end
    if is_inserter_waiting_for_source(entity) then
        table.insert(issues, "\'inserter waiting for source items\'")
    end

    local full_inventories = is_full(entity)
    for _, full_inventory in ipairs(full_inventories) do
        table.insert(issues, "\'"..full_inventory.."\'")
    end

    --if not has_output_space(entity) then
    --    if entity.drop_position ~= nil then
    --        local rounded_x = round_to_half(entity.drop_position.x)
    --        local rounded_y = round_to_half(entity.drop_position.y)
    --
    --        table.insert(issues, "\'waiting for space in destination as the output is full. Place a sink object at (" .. entity.drop_position.x .. ", ".. entity.drop_position.y .. ") to unblock.\'")
    --    else
    --        table.insert(issues, "\'waiting for space in destination\'")
    --    end
    --end
    if not has_output_space(entity) then
        if entity.drop_position then
            local rounded_x = round_to_half(entity.drop_position.x)
            local rounded_y = round_to_half(entity.drop_position.y)

            local destination_entity = entity.surface.find_entities_filtered{
                position = entity.drop_position,
                type = {"container", "transport-belt", "underground-belt", "splitter", "furnace"}
            }[1]

            if destination_entity then
                if destination_entity.type == "container" then
                    table.insert(issues, "\'chest at drop position is full. Empty the chest at (" .. rounded_x .. ", " .. rounded_y .. ") to continue mining.\'")
                elseif destination_entity.type == "furnace" then
                    table.insert(issues, "\'furnace belt at drop position is blocked.\'")
                else
                    table.insert(issues, "\'transport belt at drop position is blocked. Clear the belt at (" .. rounded_x .. ", " .. rounded_y .. ") to continue mining.\'")
                end
            else
                table.insert(issues, "\'output blocked by item on the ground. There is no sink entity in place to accept the output.\'")
            end
        else
            table.insert(issues, "\'waiting for space in destination\'")
        end
    end

    if not has_electricity(entity) then
        if entity.electric_network_id and (entity.type ~= 'solar-panel' and entity.type ~= 'generator') then
            table.insert(issues, "\'not receiving electricity\'")
        else
            table.insert(issues, "\'not connected to power network\'")
        end
    end

    local assembler_issue = lacks_assembler_resources(entity)
    if assembler_issue then
        table.insert(issues, assembler_issue)
    end

    if is_transport_belt_blocked(entity) then
        table.insert(issues, "\'transport belt blocked. Place an inserter to drain entities from it.\'")
    end

    if not has_input_liquid(entity) then
        table.insert(issues, "\'no input liquid\'")
    end
    return issues
end
function is_not_fluid(name)
    local items = { "crude-oil", "petroleum-gas", "sulfuric-acid", "water", "steam", "light-oil", "heavy-oil", "lubricant" }
    for _,v in pairs(items) do
      if v == name then
        return false
      end
    end
    return true
end
-- Define a function to check if the entity is an assembler machine and lacks resources
function lacks_assembler_resources(entity)
    if entity.type == "assembling-machine" then
        local recipe = entity.get_recipe()
        if recipe then
            local ingredients = recipe.ingredients
            local input_inventory = entity.get_inventory(defines.inventory.assembling_machine_input)
            local missing_resources = {}

            for _, ingredient in pairs(ingredients) do
                -- don't perform a check in the case of liquids like crude-oil, water etc.
                if is_not_fluid(ingredient.name) then
                    if game.item_prototypes[ingredient.name].type ~= "fluid" then
                        local available_amount = input_inventory.get_item_count(ingredient.name)
                        local missing_amount = ingredient.amount - available_amount
                        if missing_amount > 0 then
                            table.insert(missing_resources, ingredient.name .. " (" .. tostring(missing_amount) .. ")")
                        end
                    end
                end
            end

            if #missing_resources > 0 then
                return "\'cannot create " .. recipe.name .. " due to missing resources: " .. table.concat(missing_resources, ",_").."\'"

            end
        end
    end
    return false
end

-- Define a helper function to round a number to the nearest 0.5
function round_to_half(number)
    return math.floor(number * 2 + 0.5) / 2
end


-- Define a function to be called every tick
local function on_tick(event)
    -- Run the check every 60 ticks (1 second)
    if event.tick % 60 == 0 then
        for _, surface in pairs(game.surfaces) do
            local entities = surface.find_entities_filtered({force = "player"})
            for _, entity in pairs(entities) do
                local issues = get_issues(entity)

                if #issues > 0 then
                    local position = entity.position
                    local entity_key = entity.name .. "_" .. position.x .. "_" .. position.y
                    local name = '"'..entity.name:gsub(" ", "_")..'"'
                    if not global.alerts[entity_key] then
                        global.alerts[entity_key] = {
                            position = position,
                            issues = issues,
                            entity_name = name,
                            tick = event.tick
                        }
                    end
                end
            end
        end
    end
end

-- Define a function to get alerts older than the number of seconds
global.get_alerts = function(seconds)
    local current_tick = game.tick
    local old_alerts = {}

    for key, alert in pairs(global.alerts) do
        if current_tick - alert.tick > 60*seconds then
            table.insert(old_alerts, alert)
            global.alerts[key] = nil
        end
    end

    return old_alerts
end

-- Register the on_tick function to the on_tick event
script.on_event(defines.events.on_tick, on_tick)