-- Initialize globals
if not global.harvest_queues then
    global.harvest_queues = {}
end

if not global.harvested_items then
    global.harvested_items = {}
end

if not global.pending_mining_events then
    global.pending_mining_events = {}
end

-- Helper functions
local function calculate_mining_ticks(entity)
    local mining_time = entity.prototype.mineable_properties.mining_time or 1
    -- Convert mining time (in seconds) to ticks (60 ticks per second)
    return math.ceil(mining_time * 60)
end

local function update_production_stats(force, entity_name, amount)
    local stats = force.item_production_statistics
    stats.on_flow(entity_name, amount)
    if global.harvested_items[entity_name] then
        global.harvested_items[entity_name] = global.harvested_items[entity_name] + amount
    else
        global.harvested_items[entity_name] = amount
    end
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

-- Function to check if player is within reach of mining position
local function is_player_in_range(player, position)
    local dist_x = player.position.x - position.x
    local dist_y = player.position.y - position.y
    local sq_dist = (dist_x * dist_x) + (dist_y * dist_y)
    local sq_reach = (player.resource_reach_distance * player.resource_reach_distance)
    return sq_dist <= sq_reach
end

-- Helper function to start mining an entity
local function start_mining_entity(player, entity)
    if entity.valid and entity.minable then
        -- Select and begin mining the entity (only once)
        player.selected = entity

        -- Only set mining state if not already mining
        if not player.mining_state.mining then
            player.mining_state = {
                mining = true,
                position = entity.position
            }
        end

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

-- Initialize a harvest queue for a player
local function initialize_harvest_queue(player_index, position, target_yield)
    if not global.harvest_queues then
        global.harvest_queues = {}
    end

    global.harvest_queues[player_index] = {
        entities = {},
        mining_position = position,
        total_yield = 0,
        current_mining = nil,
        target_yield = target_yield,
        mining_started = false
    }

    return global.harvest_queues[player_index]
end

-- Add entities to the queue up to the desired count
local function add_entities_to_queue(queue, entities, count)
    local expected_yield = 0

    sort_entities_by_distance(entities, queue.mining_position)

    for _, entity in ipairs(entities) do
        if entity.valid and entity.minable then
            local yield = get_entity_yield(entity)
            if expected_yield + yield <= count then
                table.insert(queue.entities, entity)
                expected_yield = expected_yield + yield
            elseif expected_yield < count then
                -- Add this entity even though it will exceed count
                table.insert(queue.entities, entity)
                expected_yield = expected_yield + yield
                break
            else
                break
            end
        end
    end

    return expected_yield
end

-- Begin mining the next entity in the queue
local function begin_mining_next_entity(queue, player)
    if not queue.mining_started and #queue.entities > 0 then
        local entity = table.remove(queue.entities, 1)
        if entity and entity.valid and entity.minable then
            queue.current_mining = start_mining_entity(player, entity)
            queue.mining_started = true
            return true
        end
    end
    return false
end

-- Find entities at a position
local function find_entities_at_position(surface, position, entity_types, exact)
    local radius = exact and 0.1 or nil  -- Use tiny radius for exact position check
    return surface.find_entities_filtered{
        position = position,
        type = entity_types,
        radius = radius
    }
end

-- Check if an entity is minable
local function check_inventory_space(player, entity, count)
    -- Get player's main inventory
    local inventory = player.get_main_inventory()
    if not inventory then return false end

    -- Check if there's space for the items
    local can_insert = true
    local products = entity.prototype.mineable_properties.products

    for _, product in pairs(products) do
        local amount = (product.amount or 1) * count
        local test_stack = {name = product.name, count = amount}
        if not inventory.can_insert(test_stack) then
            can_insert = false
            break
        end
    end

    if not can_insert then
        error("Inventory is full")
    end

    return true
end

-- Event registration
-- Note: We'll use global.pending_mining_events to collect events and process them in on_nth_tick

-- Register for on_player_mined_entity event to track mining completion
script.on_event(defines.events.on_player_mined_entity, function(event)
    local player_index = event.player_index
    local entity = event.entity

    -- Store this event to be processed in the next on_nth_tick
    if not global.pending_mining_events[player_index] then
        global.pending_mining_events[player_index] = {}
    end

    table.insert(global.pending_mining_events[player_index], {
        type = "mined_entity",
        entity_name = entity.name,
        products = entity.prototype.mineable_properties.products,
        tick = game.tick
    })
end)

-- Handle mining progress checks and completions in on_nth_tick
script.on_nth_tick(60, function(event)
    -- Process any mining completion events
    if global.pending_mining_events then
        for player_index, events in pairs(global.pending_mining_events) do
            local queue = global.harvest_queues[player_index]
            local player = game.get_player(player_index)

            if queue and player and player.valid then
                for _, mining_event in ipairs(events) do
                    if mining_event.type == "mined_entity" then
                        -- Mining was successful, update total yield
                        local yield = 0
                        for _, product in pairs(mining_event.products) do
                            yield = yield + (product.amount or 1)
                            update_production_stats(player.force, product.name, product.amount or 1)
                        end

                        queue.total_yield = queue.total_yield + yield

                        -- Reset mining flags for next entity
                        queue.current_mining = nil
                        queue.mining_started = false

                        -- Check if we've reached our target
                        if queue.total_yield >= queue.target_yield then
                            -- We've reached or exceeded our target, remove excess items if needed
                            if queue.total_yield > queue.target_yield then
                                local excess = queue.total_yield - queue.target_yield
                                -- Logic to remove excess items could go here
                            end

                            -- Clear the queue
                            global.harvest_queues[player_index] = nil
                        end
                    end
                end
            end

            -- Clear processed events
            global.pending_mining_events[player_index] = {}
        end
    end

    -- Check and update all harvest queues
    if global.harvest_queues then
        for player_index, queue in pairs(global.harvest_queues) do
            local player = game.get_player(player_index)

            -- Skip if player not valid
            if not player or not player.valid then goto continue end

            -- Check if player is still in resource reach distance
            if not is_player_in_range(player, queue.mining_position) then
                -- Too far away, cancel mining and wait
                if player.mining_state.mining then
                    player.mining_state = { mining = false }
                end
                queue.mining_started = false
                goto continue
            end

            -- If we don't have a current mining operation, try to start one
            if not queue.current_mining then
                if not begin_mining_next_entity(queue, player) then
                    -- No more entities to mine
                    if #queue.entities == 0 then
                        global.harvest_queues[player_index] = nil
                    end
                    goto continue
                end
            else
                -- We have a current mining operation
                local entity = queue.current_mining.entity

                -- Check if entity is still valid
                if not entity or not entity.valid or not entity.minable then
                    -- Entity no longer valid, move to next
                    queue.current_mining = nil
                    queue.mining_started = false
                    goto continue
                end

                -- Check if player stopped mining for some reason
                if not player.mining_state.mining then
                    -- Restart mining if player stopped
                    player.selected = entity
                    player.mining_state = {
                        mining = true,
                        position = entity.position
                    }
                end

                -- Check if we've been mining too long (safety fallback)
                local mining_time = calculate_mining_ticks(entity)
                local elapsed_ticks = game.tick - queue.current_mining.start_tick

                -- If we've been mining for twice the expected time, force completion
                if elapsed_ticks > mining_time * 2 then
                    -- Force mine the entity
                    local inv_before = player.get_main_inventory().get_contents()
                    local mined_ok = player.mine_entity(entity)

                    if mined_ok then
                        local inv_after = player.get_main_inventory().get_contents()

                        -- Calculate items gained
                        local items_added = 0
                        for name, after_count in pairs(inv_after) do
                            local before_count = inv_before[name] or 0
                            items_added = items_added + (after_count - before_count)
                        end

                        queue.total_yield = queue.total_yield + items_added
                    end

                    -- Reset for next entity
                    queue.current_mining = nil
                    queue.mining_started = false

                    -- Check if we've reached our target
                    if queue.total_yield >= queue.target_yield then
                        global.harvest_queues[player_index] = nil
                    end
                end
            end

            ::continue::
        end
    end
end)

-- Main harvest resource function (slow version)
local function harvest_resource_slow(player, player_index, surface, position, count)
    local exact_entities = find_entities_at_position(surface, position, {"tree", "resource"}, true)

    if #exact_entities > 0 then
        local queue = initialize_harvest_queue(player_index, position, count)
        local expected_yield = add_entities_to_queue(queue, exact_entities, count)
        begin_mining_next_entity(queue, player)
        return expected_yield
    end

    local radius_entities = find_entities_at_position(surface, position, {"tree", "resource"}, false)
    if #radius_entities == 0 then
        error("No harvestable entities found within range")
    end

    local queue = initialize_harvest_queue(player_index, position, count)
    local expected_yield = add_entities_to_queue(queue, radius_entities, count)
    begin_mining_next_entity(queue, player)
    return expected_yield
end

-- Find entity type at position
local function find_entity_type_at_position(surface, position)
    local exact_entities = surface.find_entities_filtered{
        position = position,
        type = {"tree", "resource", "simple-entity"},
        radius = 1  -- Tiny radius for exact position check
    }

    if #exact_entities > 0 then
        return exact_entities[1].type, exact_entities[1].name
    end
    return nil, nil
end

-- Harvest specific resources
local function harvest_specific_resources(player, surface, position, count, target_type, target_name)
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

    -- For fast mode, use existing harvest functions
    if global.fast then
        if target_type == "tree" then
            return harvest_trees(entities, count, position, player)
        else
            return harvest(entities, count, position, player)
        end
    else
        -- For slow mode, use new event-based system
        local player_index = player.index
        local queue = initialize_harvest_queue(player_index, position, count)
        local expected_yield = add_entities_to_queue(queue, entities, count)
        begin_mining_next_entity(queue, player)
        return expected_yield
    end
end

-- Fast harvest functions (for reference/compatibility)
function harvest(entities, count, from_position, player)
    if count == 0 then return 0 end
    local yield = 0

    -- Check inventory space first
    local reference_entity = nil
    for _, entity in ipairs(entities) do
        if entity.valid and entity.minable then
            reference_entity = entity
            break
        end
    end

    if reference_entity then
        check_inventory_space(player, reference_entity, count)
    end

    entities = sort_entities_by_distance(entities, from_position)

    ::start::
    local has_mined = false
    for _, entity in ipairs(entities) do
        if entity.valid and entity.minable then
            -- Calculate mining ticks before mining the entity
            if global.fast then
                global.elapsed_ticks = global.elapsed_ticks + calculate_mining_ticks(entity)
            end

            local products = entity.prototype.mineable_properties.products
            for _, product in pairs(products) do
                local amount = product.amount or 1
                yield = yield + amount
                entity.mine({ignore_minable=false, raise_destroyed=true})
                entity.mine({ignore_minable=false, raise_destroyed=true})
                player.insert({name=product.name, count=amount})
                update_production_stats(player.force, product.name, amount)
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
    if count == 0 then return 0 end
    local yield = 0
    entities = sort_entities_by_distance(entities, from_position)

    for _, entity in ipairs(entities) do
        if yield >= count then break end
        if entity.valid and entity.type == "tree" then
            -- Calculate mining ticks before mining the tree
            if global.fast then
                global.elapsed_ticks = global.elapsed_ticks + calculate_mining_ticks(entity)
            end

            local products = entity.prototype.mineable_properties.products
            for _, product in pairs(products) do
                if product.name == "wood" then
                    local amount = product.amount or 1
                    player.insert({name="wood", count=amount})
                    update_production_stats(player.force, "wood", amount)
                    yield = yield + amount

                    local tree_position = entity.position
                    local tree_surface = entity.surface
                    local stump_name = entity.name.."-stump"
                    entity.destroy({raise_destroy=true})
                    -- Try to create stump, if fails just continue
                    pcall(function()
                        tree_surface.create_entity({name=stump_name, position=tree_position})
                    end)
                end
            end
        end
    end
    return yield
end

-- Main harvest_resource function
global.actions.harvest_resource = function(player_index, x, y, count, radius)
    local player = game.get_player(player_index)
    if not player then
        error("Player not found")
    end

    local player_position = player.position
    local position = {x=x, y=y}

    local distance = math.sqrt((position.x - player_position.x)^2 + (position.y - player_position.y)^2)
    if distance > player.resource_reach_distance then
        error("Nothing within reach to harvest")
    end

    local surface = player.surface
    local target_type, target_name = find_entity_type_at_position(surface, position)

    if not target_type then
        error("Nothing within reach to harvest")
    end

    if not global.fast then
        return harvest_resource_slow(player, player_index, surface, position, count)
    end

    -- Fast mode implementation remains the same as original
    local total_yield = 0
    if target_type then
        total_yield = total_yield + harvest_specific_resources(player, surface, position, count, target_type, target_name)
        if total_yield >= count then
            game.print("Harvested " .. total_yield .. " items of " .. target_name)
            return total_yield
        end
    end

    -- Fallback to try harvesting each type in sequence
    if total_yield < count then
        -- Try trees first
        local tree_entities = surface.find_entities_filtered{
            position = position,
            radius = radius,
            type = "tree"
        }
        total_yield = total_yield + harvest_trees(tree_entities, count - total_yield, position, player)
    end

    if total_yield < count then
        -- Then try resources
        local mineable_entities = surface.find_entities_filtered{
            position = position,
            radius = radius,
            type = "resource"
        }
        total_yield = total_yield + harvest(mineable_entities, count - total_yield, position, player)
    end

    if total_yield == 0 then
        error("Nothing within reach to harvest")
    else
        game.print("Harvested resources yielding " .. total_yield .. " items")
        return total_yield
    end
end

-- Helper functions for queue management
global.actions.clear_harvest_queue = function(player_index)
    if global.harvest_queues and global.harvest_queues[player_index] then
        -- Stop mining if in progress
        local player = game.get_player(player_index)
        if player and player.valid and player.mining_state.mining then
            player.mining_state = { mining = false }
        end

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