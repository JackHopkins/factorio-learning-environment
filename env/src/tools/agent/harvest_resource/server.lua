--- global.actions.harvest_resource(player_index, x, y, count, radius)
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

-- Helper function to start mining an entity and track yields
local function start_mining_entity(player, entity)
    if entity.valid and entity.minable then
        --game.print("Starting mining entity " .. entity.name .. " at " .. serpent.line(entity.position))

        -- First select the entity

        --player.selected = entity

        -- Then set mining state with position
        if not player.mining_state.mining then
            player.update_selected_entity(entity.position)
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


local function add_entities_to_queue(queue, entities, count)
    local expected_yield = 0
    local added = 0

    sort_entities_by_distance(entities, queue.mining_position)

    for _, entity in ipairs(entities) do
        if entity.valid and entity.minable then
            local yield = get_entity_yield(entity)
            if expected_yield + yield <= count then
                table.insert(queue.entities, entity)
                expected_yield = expected_yield + yield
                added = added + 1
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

script.on_nth_tick(15, function(event)
    -- If no queues at all, just return
    if not global.harvest_queues then return end

    for player_index, queue in pairs(global.harvest_queues) do
        local player = global.agent_characters[player_index]
        -- Skip if player not valid
        if not player or not player.valid then goto continue end

        -- Already reached or exceeded our target?
        if queue.total_yield >= queue.target_yield then
            -- Remove this player's queue
            global.harvest_queues[player_index] = nil
            goto continue
        end

        -- Check if player is still in resource reach distance
        local dist_x = player.position.x - queue.mining_position.x
        local dist_y = player.position.y - queue.mining_position.y
        local sq_dist = (dist_x * dist_x) + (dist_y * dist_y)
        local sq_reach = (player.resource_reach_distance * player.resource_reach_distance)
        if sq_dist > sq_reach then
            -- Too far away; do nothing for now
            goto continue
        end

        -- If there's no current mining, pick up the next entity
        if not queue.current_mining then
            local next_entity = table.remove(queue.entities, 1)
            if not next_entity then
                -- No more entities left
                global.harvest_queues[player_index] = nil
                goto continue
            end

            -- Start mining
            queue.current_mining = {
                entity = next_entity,
                start_tick = game.tick
            }
        else
            -- We have a current entity being mined
            local entity = queue.current_mining.entity
            if not entity or not entity.valid or not entity.minable then
                -- Entity no longer valid, skip
                queue.current_mining = nil
                goto continue
            end

            local ticks_mining = game.tick - queue.current_mining.start_tick
            if ticks_mining >= 30 then
                -- Time to finish mining
                local inv_before = player.get_main_inventory().get_contents()
                local mined_ok = player.mine_entity(entity)  -- Instantly mines & adds items
                if mined_ok then
                    local inv_after = player.get_main_inventory().get_contents()

                    -- Figure out how many items we actually gained
                    local items_added = 0
                    for name, after_count in pairs(inv_after) do
                        local before_count = inv_before[name] or 0
                        items_added = items_added + (after_count - before_count)
                    end

                    if items_added > 0 then
                        -- Add to our queue's total_yield
                        local new_total = queue.total_yield + items_added

                        if new_total > queue.target_yield then
                            -- We overshot. Remove the extras from the player's inventory.
                            local overshoot = new_total - queue.target_yield
                            -- We'll try to remove it from whatever items were gained.
                            -- If multiple resource types might drop, you'd handle them individually.

                            local overshoot_left = overshoot
                            for name, after_count in pairs(inv_after) do
                                local before_count = inv_before[name] or 0
                                local gained_this_item = (after_count - before_count)
                                if gained_this_item > 0 then
                                    local to_remove = math.min(overshoot_left, gained_this_item)
                                    local actually_removed = player.remove_item({name = name, count = to_remove})
                                    overshoot_left = overshoot_left - actually_removed
                                    if overshoot_left <= 0 then
                                        break
                                    end
                                end
                            end
                            new_total = queue.target_yield
                        end

                        queue.total_yield = new_total
                    end
                end

                -- Clear current mining
                queue.current_mining = nil
            end
        end
        ::continue::
    end
end)


local function check_inventory_space(player, entity, count)
    -- Get player's main inventory
    local inventory = player.get_main_inventory()
    if not inventory then return false end

    -- Create a temporary inventory to test insertion
    local test_inventory = game.create_inventory(1)
    local can_insert = true

    -- Calculate total items that would be added
    local total_items = 0
    local products = entity.prototype.mineable_properties.products
    for _, product in pairs(products) do
        local amount = (product.amount or 1) * count
        -- Try to insert into test inventory
        local test_stack = {name = product.name, count = amount}
        if not inventory.can_insert(test_stack) then
            can_insert = false
            break
        end
        total_items = total_items + amount
    end

    -- Clean up test inventory
    test_inventory.destroy()

    if not can_insert then
        error("Inventory is full")
    end

    return true
end


local function find_entity_type_at_position(surface, position)
    local exact_entities = surface.find_entities_filtered{
        position = position,
        type = {"tree", "resource", "simple-entity"},--, "optimized-decorative"},
        radius = 1  -- Tiny radius for exact position check
    }

    if #exact_entities > 0 then
        -- game.print("Found type ".. exact_entities[1].name)
        return exact_entities[1].type, exact_entities[1].name
    end
    return nil, nil
end

local function harvest_specific_resources(player, surface, position, count, target_type, target_name)
    -- game.print("Harvesting specific resources")
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


local function find_entities_at_position(surface, position, entity_types, exact)
    local radius = exact and 0.1 or nil  -- Use tiny radius for exact position check
    return surface.find_entities_filtered{
        position = position,
        type = entity_types,
        radius = radius
    }
end

local function begin_mining(queue, player)
    if #queue.entities > 0 then
        local first_entity = table.remove(queue.entities, 1)
        queue.current_mining = start_mining_entity(player, first_entity)
        if not queue.current_mining then
            error("Failed to start mining entity")
        end
    end
end

local function initialize_harvest_queue(player_index, position, target_yield)
   if not global.harvest_queues then
       global.harvest_queues = {}
   end

   global.harvest_queues[player_index] = {
       entities = {},
       mining_position = position,
       total_mined = 0,
       total_yield = 0,
       current_mining = nil,
       target_yield = target_yield
   }

   return global.harvest_queues[player_index]
end


local function harvest_resource_slow(player, player_index, surface, position, count)
   local exact_entities = find_entities_at_position(surface, position, {"tree", "resource"}, true)

   if #exact_entities > 0 then
       local queue = initialize_harvest_queue(player_index, position, count)
       local expected_yield = add_entities_to_queue(queue, exact_entities, count)
       begin_mining(queue, player)
       return expected_yield
   end

   local radius_entities = find_entities_at_position(surface, position, {"tree", "resource"}, false)
   if #radius_entities == 0 then
       error("No harvestable entities found within range")
   end

   local queue = initialize_harvest_queue(player_index, position, count)
   local expected_yield = add_entities_to_queue(queue, radius_entities, count)
   -- game.print("expected "..expected_yield)
   begin_mining(queue, player)
   return expected_yield
end

function harvest(entities, count, from_position, player)
    if count == 0 then return 0 end
    local yield = 0

    -- Check inventory space first using the first valid entity as reference
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
    -- game.print("Harvesting "..#entities.." trees")
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

-- Add function to handle simple entities like rocks and tree stumps
local function harvest_simple_entities(entities, count, from_position, player)
    if count == 0 then return 0 end
    local yield = 0
    entities = sort_entities_by_distance(entities, from_position)

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
                player.insert({name=product.name, count=amount})
                update_production_stats(player.force, product.name, amount)

                if yield >= count then break end
            end
            if yield >= count then break end
        end
    end
    return yield
end


global.actions.harvest_resource = function(player_index, x, y, count, radius)
    local player = global.agent_characters[player_index]
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

    --if not global.fast then
    --    return harvest_resource_slow(player, player_index, surface, position, count, radius)
    --end

    local total_yield = 0
    if target_type then
        total_yield = total_yield + harvest_specific_resources(player, surface, position, count, target_type, target_name)
        if total_yield >= count then
            -- game.print("Harvested " .. total_yield .. " items of " .. target_name)
            return total_yield
        end
    end

    -- Try harvesting each type in sequence if we haven't met our quota
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
        -- Then try simple entities (rocks, stumps, etc.)
        local simple_entities = surface.find_entities_filtered{
            position = position,
            radius = radius,
            type = "simple-entity"
        }
        total_yield = total_yield + harvest_simple_entities(simple_entities, count - total_yield, position, player)
    end

    if total_yield < count then
        -- Finally try standard resources
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
        -- game.print("Harvested resources yielding " .. total_yield .. " items")
        return total_yield
    end
end
--
--global.actions.harvest_resource2 = function(player_index, x, y, count, radius)
--    local player = global.agent_characters[player_index]
--    if not player then
--        error("Player not found")
--    end
--
--    local player_position = player.position
--    local position = {x=x, y=y}
--
--    local distance = math.sqrt((position.x - player_position.x)^2 + (position.y - player_position.y)^2)
--    if distance > player.resource_reach_distance then
--        error("Nothing within reach to harvest")
--    end
--    local surface = player.surface
--
--    -- Check what's under the player first
--    local target_type, target_name = find_entity_type_at_position(surface, position)
--    if not target_type then
--        error("Nothing within reach to harvest")
--    end
--    if not global.fast then
--        return harvest_resource_slow(player, player_index, surface, position, count, radius)
--    end
--
--
--    local total_yield = 0
--    if target_type then
--        -- If we found something at the exact position, harvest that specific type
--        total_yield = total_yield + harvest_specific_resources(player, surface, position, count, target_type, target_name)
--        if total_yield >= count then
--            game.print("Harvested " .. total_yield .. " items of " .. target_name)
--            return total_yield
--        end
--    end
--
--    -- If nothing at exact position or couldn't get enough yield, fall back to original logic
--    local tree_entities = surface.find_entities_filtered{position=position, radius=radius, type = "tree"}
--    local tree_yield = harvest_trees(tree_entities, count - total_yield, position, player)
--    local total_yield = total_yield + tree_yield
--
--    if tree_yield < count then
--        local mineable_entities = surface.find_entities_filtered{position=position, radius=radius, type = "resource"}
--        local resource_yield = harvest(mineable_entities, count - total_yield, position, player)
--        total_yield = total_yield + resource_yield
--
--        if total_yield == 0 then
--            error("Could not harvest at position ("..position.x..", "..position.y..").")
--        end
--    end
--
--    if total_yield == 0 then
--        error("Nothing within reach to harvest")
--    else
--        game.print("Harvested resources yielding " .. total_yield .. " items")
--        return total_yield
--    end
--end


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
    local player = global.agent_characters[player_index]
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