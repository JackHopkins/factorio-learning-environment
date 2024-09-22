--global.actions.harvest_resource2 = function(player_index, x, y, count)
--    local player = game.players[player_index]
--    local position = {x=x, y=y}
--    local surface = player.surface
--    local success = false
--    local total_harvested = 0
--    local max_attempts = 3
--
--    function harvest(entities, count)
--        local remaining_count = count
--        for _, entity in pairs(entities) do
--            if entity.valid and entity.minable and player.can_reach_entity(entity) then
--                while remaining_count > 0 do
--                    local did_mine = player.mine_entity(entity)
--                    if did_mine then
--                        remaining_count = remaining_count - 1
--                    else
--                        break
--                    end
--                    if remaining_count == 0 then
--                        break
--                    end
--                end
--            end
--        end
--        return count - remaining_count
--    end
--
--
--    for attempt = 1, max_attempts do
--        -- Attempt to mine
--        local mineable_entities = surface.find_entities_filtered{position=position, radius=5, type = "resource"}
--        game.print("Found " .. #mineable_entities .. " mineable entities")
--
--        local mined_count = harvest(mineable_entities, count - total_harvested)
--        game.print("Mined " .. mined_count .. " resources")
--        total_harvested = total_harvested + mined_count
--
--        -- Attempt to harvest trees if mining was not fully successful
--        if total_harvested < count then
--            local tree_entities = surface.find_entities_filtered{position=position, radius=5, type = "tree"}
--            local harvested_count = harvest(tree_entities, count - total_harvested)
--            total_harvested = total_harvested + harvested_count
--        end
--
--        if total_harvested == count then
--            success = true
--            break
--        elseif attempt < max_attempts then
--            game.print("Attempt " .. attempt .. " harvested " .. total_harvested .. " resources. Retrying...")
--        end
--    end
--
--    if not success then
--        if total_harvested == 0 then
--            error("Could not harvest any resources at position (" .. position.x .. ", " .. position.y .. ") after " .. max_attempts .. " attempts. Move nearer and try again.")
--        else
--            error("Could only harvest " .. total_harvested .. " out of " .. count .. " requested resources at position (" .. position.x .. ", " .. position.y .. ") after " .. max_attempts .. " attempts.")
--        end
--    else
--        game.print("Successfully harvested " .. total_harvested .. " resources")
--        return 1
--    end
--end
--
--global.actions.harvest_resource_new = function(player_index, x, y, count)
--    local player = game.players[player_index]
--    local position = {x=x, y=y}
--    local surface = player.surface
--    local total_harvested = 0
--    local max_radius = 50
--
--    function harvest_trees(entities, count)
--        local remaining_count = count
--        for name, entity in pairs(entities) do
--            game.print(name)
--            if entity.valid and entity.minable and player.can_reach_entity(entity) then
--                local did_mine = player.mine_entity(entity)
--                if did_mine then
--                    remaining_count = remaining_count - 1
--                end
--                if remaining_count == 0 then
--                    break
--                end
--            end
--        end
--        return count - remaining_count
--    end
--
--    function harvest(entities, remaining_count)
--        local harvested = 0
--        for _, entity in pairs(entities) do
--            if entity.valid and entity.minable and player.can_reach_entity(entity) then
--                local attempts = 0
--                while player.mine_entity(entity) and harvested < remaining_count and attempts < 3 do
--                    harvested = harvested + 1
--                    attempts = attempts + 1
--                    if harvested == remaining_count then
--                        return harvested
--                    end
--                end
--            end
--        end
--        return harvested
--    end
--
--    local radius = 10
--    while total_harvested < count and radius <= max_radius do
--        -- Attempt to harvest trees
--        local tree_entities = surface.find_entities_filtered{position=position, radius=radius, type = "tree"}
--        local harvested_count = harvest_trees(tree_entities, count - total_harvested)
--        total_harvested = total_harvested + harvested_count
--
--        game.print("Harvested " .. harvested_count .. " trees")
--        -- Attempt to mine resources if tree harvesting was not fully successful
--        if total_harvested < count then
--            local mineable_entities = surface.find_entities_filtered{position=position, radius=radius, type = "resource"}
--            local mined_count = harvest(mineable_entities, count - total_harvested)
--            total_harvested = total_harvested + mined_count
--
--        end
--
--        -- Increase radius if we haven't harvested enough
--        if total_harvested < count then
--            radius = radius + 10
--        else
--            break
--        end
--    end
--
--    if total_harvested == 0 then
--        return error("\"Could not harvest any resources at position ("..position.x..", "..position.y..").\"")
--    elseif total_harvested < count then
--        return error("\"Could only harvest "..total_harvested.." out of "..count.." requested resources.\"")
--    else
--        game.print("Successfully harvested "..total_harvested.." resources.")
--        return 1
--    end
--end

global.actions.harvest_resource = function(player_index, x, y, count, radius)
    local player = game.players[player_index]

    local position = {x=x, y=y}
    local surface = player.surface

    local success = 0

    function harvest_trees(entities, count)
        local remaining_count = count
        local wood_count = player.get_item_count("wood")
        for name, entity in pairs(entities) do
            if entity.valid and entity.minable then
                if not player.can_reach_entity(entity) then
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
        local remaining_count = count
        for _, entity in pairs(entities) do
            if entity.valid and entity.minable and player.can_reach_entity(entity) then
                while remaining_count > 0 do
                    local did_mine = false

                    did_mine = player.mine_entity(entity)
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
            error("Could not harvest at position ("..position.x..", "..position.y.."). Move nearer and try again.")
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
        return 1
    end
end