--- global.actions.harvest_resource(player_index, x, y, count, radius)

-- Helper function to start mining an entity and track yields
local function start_mining_entity(player, entity)
    if entity.valid and entity.minable then
        game.print("Starting mining entity " .. entity.name .. " at " .. serpent.line(entity.position))

        -- First select the entity
        player.update_selected_entity(entity.position)
        --player.selected = entity

        -- Then set mining state with position
        if not player.mining_state.mining then
            player.mining_state = {
                mining = true,
                position = entity.position
            }
        end

        game.print("Mining state set: mining=" .. tostring(player.mining_state.mining))

        -- Calculate expected yield
        local expected_yield = 0
        local products = entity.prototype.mineable_properties.products
        for _, product in pairs(products) do
            expected_yield = expected_yield + (product.amount or 1)
        end

        return {
            entity = entity,
            start_tick = game.tick,
            expected_yield = expected_yield
        }
    end
    return nil
end

script.on_nth_tick(15, function(event)
    if global.harvest_queues then
        for player_index, queue in pairs(global.harvest_queues) do
            local player = game.get_player(player_index)
            if not player then goto continue end

            if queue.current_mining then
                -- Always maintain mining state at the original position
                player.update_selected_entity(queue.mining_position)

                if not player.mining_state.mining then
                    player.mining_state = {
                        mining = true,
                        position = queue.mining_position
                    }
                end

                local mining_duration = game.tick - queue.current_mining.start_tick

                if mining_duration >= 30 then
                    -- Complete the mining operation
                    if queue.current_mining.entity.valid and queue.current_mining.entity.minable then
                        player.mine_entity(queue.current_mining.entity)
                        queue.total_mined = queue.total_mined + 1
                        queue.total_yield = (queue.total_yield or 0) + queue.current_mining.expected_yield
                    end

                    queue.current_mining = nil

                    -- Start next mining operation from same position
                    if #queue.entities > 0 then
                        local next_entity = table.remove(queue.entities, 1)
                        queue.current_mining = start_mining_entity(player, next_entity)
                    else
                        player.mining_state = { mining = false }
                        -- Return total yield before clearing queue
                        local final_yield = queue.total_yield or 0
                        global.harvest_queues[player_index] = nil
                        return final_yield
                    end
                end
            end

            ::continue::
        end
    end
end)

local function find_entity_type_at_position(surface, position)
    local exact_entities = surface.find_entities_filtered{
        position = position,
        type = {"tree", "resource"},
        radius = 0.1  -- Tiny radius for exact position check
    }

    if #exact_entities > 0 then
        game.print("Found type ".. exact_entities[1].name)
        return exact_entities[1].type, exact_entities[1].name
    end
    return nil, nil
end

local function harvest_specific_resources(player, surface, position, count, target_type, target_name)
    game.print("Harvesting specific resources")
    -- Use existing harvest/harvest_trees functions but filtered to specific type
    local radius = player.resource_reach_distance
    local entities = surface.find_entities_filtered{
        position = position,
        radius = radius,
        type = target_type,
        name = target_name,
        limit = count
    }

    if #entities == 0 then
        error("No matching resources found within range")
    end

    -- Use your existing harvest functions based on type
    if target_type == "tree" then
        return harvest_trees(entities, count, position, player)
    else
        return harvest(entities, count, position, player)
    end
end

-- Function to calculate distance between two points
local function distance(pos1, pos2)
    return math.sqrt((pos1.x - pos2.x)^2 + (pos1.y - pos2.y)^2)
end

-- Function to sort entities by distance from a given position
local function sort_entities_by_distance(entities, from_position)
    table.sort(entities, function(a, b)
        return distance(a.position, from_position) < distance(b.position, from_position)
    end)
    return entities
end


local function harvest_resource_slow(player, player_index, surface, position, count)
    -- Try exact position first
    local exact_entities = find_entities_at_position(surface, position, {"tree", "resource"}, true)

    if #exact_entities > 0 then
        local queue = initialize_harvest_queue(player_index, position)
        local expected_yield = add_entities_to_queue(queue, exact_entities, count)
        begin_mining(queue, player)
        return expected_yield
    end

    -- Fall back to radius search
    local radius_entities = find_entities_at_position(surface, position, {"tree", "resource"}, false)
    if #radius_entities == 0 then
        error("No harvestable entities found within range")
    end

    local queue = initialize_harvest_queue(player_index, position)
    local expected_yield = add_entities_to_queue(queue, radius_entities, count)
    begin_mining(queue, player)
    return expected_yield
end

function harvest(entities, count, from_position, player)
    if count == 0 then return 0 end
    local yield = 0
    entities = sort_entities_by_distance(entities, from_position)
    ::start::
    local has_mined = false
    for _, entity in ipairs(entities) do
        if entity.valid and entity.minable then
            local products = entity.prototype.mineable_properties.products
            for _, product in pairs(products) do
                local amount = product.amount or 1
                yield = yield + amount
                entity.mine({ignore_minable=false, raise_destroyed=true})
                player.insert({name=product.name, count=amount})
                has_mined = true
                if yield >= count then break end
            end
            if yield >= count then break end
        end
    end
    if has_mined == true and yield < count then
        goto start
    end
    return yield
end

function harvest_trees(entities, count, from_position, player)
    game.print("Harvesting "..#entities.." trees")
    if count == 0 then return 0 end
    local yield = 0
    entities = sort_entities_by_distance(entities, from_position)

    for _, entity in ipairs(entities) do
        if yield >= count then break end
        if entity.valid and entity.type == "tree" then
            local products = entity.prototype.mineable_properties.products
            for _, product in pairs(products) do
                if product.name == "wood" then
                    local amount = product.amount or 1
                    player.insert({name="wood", count=amount})
                    yield = yield + amount

                    local tree_position = entity.position
                    local tree_surface = entity.surface
                    local stump_name = entity.name.."-stump"
                    entity.destroy({raise_destroy=true})
                    tree_surface.create_entity({name=stump_name, position=tree_position})
                end
            end
        end
    end
    return yield
end

local function find_entities_at_position(surface, position, entity_types, exact)
    local radius = exact and 0.1 or nil  -- Use tiny radius for exact position check
    return surface.find_entities_filtered{
        position = position,
        type = entity_types,
        radius = radius
    }
end

local function get_entity_yield(entity)
    local yield = 0
    if entity.valid and entity.minable then
        local products = entity.prototype.mineable_properties.products
        for _, product in pairs(products) do
            yield = yield + (product.amount or 1)
        end
    end
    return yield
end


global.actions.harvest_resource = function(player_index, x, y, count, radius)
    local player = game.get_player(player_index)
    if not player then
        error("Player not found")
    end
    local position = {x=x, y=y}
    local surface = player.surface

    if not global.fast then
        return harvest_resource_slow(player, player_index, surface, position, count, radius)
    end

    -- Check what's under the player first
    local target_type, target_name = find_entity_type_at_position(surface, position)
    local total_yield = 0
    if target_type then
        -- If we found something at the exact position, harvest that specific type
        total_yield = total_yield + harvest_specific_resources(player, surface, position, count, target_type, target_name)
        if total_yield >= count then
            game.print("Harvested " .. total_yield .. " items of " .. target_name)
            return total_yield
        end
    end

    -- If nothing at exact position or couldn't get enough yield, fall back to original logic
    local tree_entities = surface.find_entities_filtered{position=position, radius=radius, type = "tree"}
    local tree_yield = harvest_trees(tree_entities, count - total_yield, position, player)
    local total_yield = total_yield + tree_yield

    if tree_yield < count then
        local mineable_entities = surface.find_entities_filtered{position=position, radius=radius, type = "resource"}
        local resource_yield = harvest(mineable_entities, count - total_yield, position, player)
        total_yield = total_yield + resource_yield

        if total_yield == 0 then
            error("Could not harvest at position ("..position.x..", "..position.y..").")
        end
    end

    if total_yield == 0 then
        error("Nothing within reach to harvest")
    else
        game.print("Harvested resources yielding " .. total_yield .. " items")
        return total_yield
    end
end


global.actions.clear_harvest_queue = function(player_index)
    if global.harvest_queues and global.harvest_queues[player_index] then
        global.harvest_queues[player_index] = nil
    end
end

global.actions.get_harvest_queue_length = function(player_index)
    if global.harvest_queues and global.harvest_queues[player_index] then
        return #global.harvest_queues[player_index].entities
    end
    return 0
end

global.actions.get_resource_name_at_position = function(player_index, x, y)
    local player = game.get_player(player_index)
    if not player then
        error("Player not found")
    end

    local position = {x=x, y=y}
    local surface = player.surface

    local entities = surface.find_entities_filtered{
        position = position,
        radius = player.resource_reach_distance,
        type = {"tree", "resource"},
        limit = 1
    }
    local entity_name = nil
    if #entities > 0 then
        entity_name = entities[1].name
    end
    return entity_name
end