global.actions.harvest_resource = function(player_index, x, y, count, radius)
    local player = game.get_player(player_index)
    if not player then
        error("Player not found")
    end

    local position = {x=x, y=y}
    local surface = player.surface

    local success = 0

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

    function harvest_trees(entities, count, from_position)
        if count == 0 then
            return 0
        end
        local remaining_count = count
        local wood_count = player.get_item_count("wood")

        -- Sort entities by distance from the given position
        entities = sort_entities_by_distance(entities, from_position)

        for _, entity in ipairs(entities) do
            if entity.valid and entity.type == "tree" then
                local products = entity.prototype.mineable_properties.products
                for _, product in pairs(products) do
                    if product.name == "wood" then
                        local to_mine = math.min(remaining_count, product.amount or 1)
                        remaining_count = remaining_count - to_mine

                        -- Calculate the percentage of wood harvested
                        local harvest_percentage = to_mine / (product.amount or 1)

                        -- Insert the harvested wood into the player's inventory
                        player.insert({name="wood", count=to_mine})

                        -- If we've harvested all the wood, replace the tree with a stump
                        if harvest_percentage >= 1 then
                            local tree_position = entity.position
                            local tree_surface = entity.surface
                            local stump_name = entity.name.."-stump"

                            entity.destroy({raise_destroy=true})

                            -- Create a stump entity
                            tree_surface.create_entity({name=stump_name, position=tree_position})
                        else
                            -- If we haven't harvested all the wood, we could optionally change the tree's appearance
                            -- This would require custom graphics for partially harvested trees
                            -- entity.graphics_variation = math.floor(harvest_percentage * 10)
                        end

                        if remaining_count <= 0 then
                            break
                        end
                    end
                end
                if remaining_count <= 0 then
                    break
                end
            end
        end
        return count - remaining_count
    end

    function harvest(entities, count, from_position)
        if count == 0 then
            return 0
        end
        local remaining_count = count

        -- Sort entities by distance from the given position
        entities = sort_entities_by_distance(entities, from_position)

        for _, entity in ipairs(entities) do
            if entity.valid and entity.minable then
                local products = entity.prototype.mineable_properties.products
                for _, product in pairs(products) do
                    local to_mine = math.min(remaining_count, product.amount or 1)
                    remaining_count = remaining_count - to_mine
                    game.print("Harvest mineable")
                    entity.mine({ignore_minable=false, raise_destroyed=true})
                    player.insert({name=product.name, count=to_mine})
                    if remaining_count <= 0 then
                        break
                    end
                end
                if remaining_count <= 0 then
                    break
                end
            end
        end
        return count - remaining_count
    end

    local tree_entities = surface.find_entities_filtered{position=position, radius=radius, type = "tree"}
    local mined_count = harvest_trees(tree_entities, count, position)
    local total = mined_count

    if mined_count < count then
        local mineable_entities = surface.find_entities_filtered{position=position, radius=radius, type = "resource"}
        local harvested_count = harvest(mineable_entities, count - mined_count, position)
        total = (mined_count + harvested_count)

        if total == 0 then
            error("Could not harvest at position ("..position.x..", "..position.y..").")
        elseif total ~= count then
            error("Could only harvest "..total.." at position ("..position.x..", "..position.y..")")
        end
        success = total > 0
    else
        success = true
    end

    if success == 0 then
        error("Nothing within reach to harvest")
    else
        game.print("Harvested "..total.." resources")
        return total
    end
end

global.actions.harvest_resource2 = function(player_index, x, y, count, radius)
    local player = game.get_player(player_index)


    local position = {x=x, y=y}
    --local surface = player.surface
    local surface = game.surfaces[1]

    local success = 0

    function harvest_trees(entities, count)
        if count == 0 then
            return 0
        end
        local remaining_count = count
        local wood_count = player.get_item_count("wood")
        for name, entity in pairs(entities) do
            if entity.valid and entity.minable then
                local can_reach = global.actions.can_reach(player, entity.position.x, entity.position.y)
                if not can_reach then
                    -- teleport player to the entity
                    player.teleport(entity.position)
                end
                local did_mine = player.mine_entity(entity)
                local new_wood_count = player.get_item_count("wood") - wood_count
                if new_wood_count >= count then
                    return new_wood_count
                end
                game.print(new_wood_count)
                if did_mine then
                    remaining_count = remaining_count - new_wood_count
                end
                if remaining_count == 0 then
                    break
                end
            end
        end
        return count - remaining_count
    end

    function harvest(entities, count)
        if count == 0 then
            return 0
        end
        local remaining_count = count
        -- attempt to mine each entity in turn
        for _, entity in pairs(entities) do
            if entity.valid and entity.minable then
                local can_reach = global.actions.can_reach(player, entity.position.x, entity.position.y)
                if can_reach then
                    game.print("Can reach entity!" .. entity.name .. " at position ("..entity.position.x..", "..entity.position.y..")" .. " with count " .. count .. " and remaining count " .. remaining_count,  {skip=defines.print_skip.never})
                    if remaining_count == 0 then
                        break
                    end
                    -- attempt to mine the entity until we have mined the required amount
                    while remaining_count > 0 do
                        local did_mine = false

                        local initial_count = player.get_item_count(entity.name)
                        --player.update_selected_entity({position = entity.position})
                        did_mine = player.mine_entity(entity, true)
                        game.print("Did mine ".. tostring(did_mine), {skip=defines.print_skip.never})
                        -- check player inventory for the mined item
                        local mined_count = player.get_item_count(entity.name) - initial_count
                        game.print("Mined count " .. mined_count, {skip=defines.print_skip.never})
                        if did_mine then
                            game.print("Mined entity" .. entity.name .. " at position ("..entity.position.x..", "..entity.position.y..")",  {skip=defines.print_skip.never})
                        else
                            game.print("Could not mine entity" .. entity.name .. " at position ("..entity.position.x..", "..entity.position.y..")",  {skip=defines.print_skip.never})
                        end

                        remaining_count = remaining_count - 1
                        if remaining_count == 0 then
                            break
                        end
                        if not did_mine then
                            break
                        end
                    end
                end
            end

        end

        return count - remaining_count
    end

    -- Attempt to mine
    local tree_entities = surface.find_entities_filtered{position=position, radius=radius, type = "tree"}
    local mined_count = harvest_trees(tree_entities, count)
    local total = mined_count
    -- Attempt to harvest trees if mining was not fully successful
    if mined_count < count then
        local mineable_entities = surface.find_entities_filtered{position=position, radius=radius, type = "resource"}
        local harvested_count = harvest(mineable_entities, count - mined_count)
        total = (mined_count + harvested_count)

        if total == 0 then
            error("Could not harvest at position ("..position.x..", "..position.y.."). The player position is ("..player.position.x..", "..player.position.y.."). Move nearer and try again.")
        elseif total ~= count then

            error("Could only harvest "..total.." at position ("..position.x..", "..position.y..")")
        end
        success = total > 0
    else
        success = true
    end

    if success == 0 then
        error("Nothing within reach to harvest")
    else
        game.print("Harvested "..total.." resources")
        return total
    end
end