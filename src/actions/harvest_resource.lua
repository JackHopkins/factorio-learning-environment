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

local function harvest_resource_slow(player, player_index, surface, position, count)
        local x, y = position.x, position.y
        local radius = player.resource_reach_distance
        local entities = surface.find_entities_filtered{
            position = position,
            radius = radius,
            type = {"tree", "resource"}
        }

        if #entities == 0 then
            error("No harvestable entities found within range")
        end

        local function calculate_distance(entity)
            return ((entity.position.x - x)^2 + (entity.position.y - y)^2)
        end

        table.sort(entities, function(a, b)
            return calculate_distance(a) < calculate_distance(b)
        end)

        local closest_entity = entities[1]

        if not global.harvest_queues then
            global.harvest_queues = {}
        end

        if not global.harvest_queues[player_index] then
            global.harvest_queues[player_index] = {
                entities = {},
                current_mining = nil,
                total_requested = count,
                total_mined = 0,
                total_yield = 0,  -- Track total resources yielded
                mining_position = closest_entity.position
            }
        end

        local queue = global.harvest_queues[player_index]
        local entities_added = 0
        local expected_yield = 0
        local trees_added = {}

        -- First pass: Add trees
        for _, entity in ipairs(entities) do
            if entities_added >= count then break end

            if entity.valid and entity.type == "tree" then
                local entity_key = entity.position.x .. "," .. entity.position.y
                if not trees_added[entity_key] then
                    local products = entity.prototype.mineable_properties.products
                    for _, product in pairs(products) do
                        expected_yield = expected_yield + (product.amount or 1)
                    end
                    table.insert(queue.entities, entity)
                    trees_added[entity_key] = true
                    entities_added = entities_added + 1
                end
            end
        end

        -- Second pass: Add other resources
        if entities_added < count then
            for _, entity in ipairs(entities) do
                if entities_added >= count then break end

                if entity.valid and entity.type == "resource" then
                    local products = entity.prototype.mineable_properties.products
                    for _, product in pairs(products) do
                        expected_yield = expected_yield + (product.amount or 1)
                    end
                    table.insert(queue.entities, entity)
                    entities_added = entities_added + 1
                end
            end
        end

        if not queue.current_mining and #queue.entities > 0 then
            queue.current_mining = start_mining_entity(player, queue.entities[1])
            if queue.current_mining then
                table.remove(queue.entities, 1)
            end
        end

        return expected_yield
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

    -- [Rest of fast mode code remains the same but modified to return actual yield]
    local total_yield = 0

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
    --function harvest_trees(entities, count, from_position)
    --    if count == 0 then return 0 end
    --    local yield = 0
    --    entities = sort_entities_by_distance(entities, from_position)
    --
    --    for _, entity in ipairs(entities) do
    --        if entity.valid and entity.minable and entity.type == "tree" then
    --            local products = entity.prototype.mineable_properties.products
    --            for _, product in pairs(products) do
    --                if product.name == "wood" then
    --                    local amount = product.amount or 1
    --                    yield = yield + amount
    --                    -- Check to see if the entity is valid, if not, continue
    --                    if not entity.valid then
    --                        goto continue
    --                    end
    --                    -- Use mine_entity instead of direct insertion
    --                    player.mine_entity(entity)
    --
    --                    local tree_position = entity.position
    --                    local tree_surface = entity.surface
    --                    local stump_name = entity.name.."-stump"
    --                    tree_surface.create_entity({name=stump_name, position=tree_position})
    --
    --                    if yield >= count then break end
    --                end
    --                ::continue::
    --            end
    --            if yield >= count then break end
    --        end
    --    end
    --    return yield
    --end

    function harvest(entities, count, from_position)
        if count == 0 then return 0 end
        local yield = 0
        entities = sort_entities_by_distance(entities, from_position)

        for _, entity in ipairs(entities) do
            if entity.valid and entity.minable then
                local products = entity.prototype.mineable_properties.products
                for _, product in pairs(products) do
                    local amount = product.amount or 1
                    yield = yield + amount
                    -- Check to see if the entity is valid, if not, continue
                    if not entity.valid then
                        goto continue
                    end
                    -- Use mine_entity instead of entity.mine()
                    player.mine_entity(entity)
                    if yield >= count then break end
                end
                if yield >= count then break end
            end
            ::continue::
        end
        return yield
    end

    function harvest_trees(entities, count, from_position)
        if count == 0 then return 0 end
        local yield = 0
        entities = sort_entities_by_distance(entities, from_position)

        for _, entity in ipairs(entities) do
            if entity.valid and entity.type == "tree" then
                local products = entity.prototype.mineable_properties.products
                for _, product in pairs(products) do
                    if product.name == "wood" then
                        local amount = product.amount or 1
                        yield = yield + amount
                        player.insert({name="wood", count=amount})

                        local tree_position = entity.position
                        local tree_surface = entity.surface
                        local stump_name = entity.name.."-stump"
                        entity.destroy({raise_destroy=true})
                        tree_surface.create_entity({name=stump_name, position=tree_position})

                        if yield >= count then break end
                    end
                end
                if yield >= count then break end
            end
        end
        return yield
    end

    function harvest2(entities, count, from_position)
        if count == 0 then return 0 end
        local yield = 0
        entities = sort_entities_by_distance(entities, from_position)

        for _, entity in ipairs(entities) do
            if entity.valid and entity.minable then
                local products = entity.prototype.mineable_properties.products
                for _, product in pairs(products) do
                    local amount = product.amount or 1
                    yield = yield + amount
                    entity.mine({ignore_minable=false, raise_destroyed=true})
                    player.insert({name=product.name, count=amount})
                    if yield >= count then break end
                end
                if yield >= count then break end
            end
        end
        return yield
    end

    local tree_entities = surface.find_entities_filtered{position=position, radius=radius, type = "tree"}
    local tree_yield = harvest_trees(tree_entities, count, position)
    total_yield = tree_yield

    if tree_yield < count then
        local mineable_entities = surface.find_entities_filtered{position=position, radius=radius, type = "resource"}
        local resource_yield = harvest(mineable_entities, count - tree_yield, position)
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