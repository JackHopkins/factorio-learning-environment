-- Agent-facing blueprint capture and placement.
--
-- Differences from the admin tools (deliberate):
--   * capture takes a bounded area (center + radius) instead of every force
--     entity, and never embeds characters;
--   * place does NOT call research_all_technologies -- that side effect is
--     acceptable for admin debugging but would be a research-unlock cheat
--     vector through the agent action space.

local MAX_CAPTURE_RADIUS = 128

local function collect_area(player_index, x, y, radius)
    local character = storage.agent_characters[player_index]
    local force = character.force
    local surface = game.surfaces["nauvis"]
    local min_x, min_y, max_x, max_y
    local center_x, center_y
    local entities

    if radius and tonumber(radius) > 0 then
        radius = math.min(tonumber(radius), MAX_CAPTURE_RADIUS)
        center_x = x
        center_y = y
        local area = {
            left_top = {x = x - radius, y = y - radius},
            right_bottom = {x = x + radius, y = y + radius},
        }
        entities = surface.find_entities_filtered({
            force = force,
            area = area,
        })
        min_x = x - radius
        min_y = y - radius
        max_x = x + radius
        max_y = y + radius
    else
        entities = surface.find_entities_filtered({force = force})
        min_x, min_y = math.huge, math.huge
        max_x, max_y = -math.huge, -math.huge
    end

    local count = 0
    for _, entity in pairs(entities) do
        if entity.type ~= "character" and entity.valid then
            count = count + 1
            if not (radius and tonumber(radius) > 0) then
                local pos = entity.position
                min_x = math.min(min_x, pos.x)
                min_y = math.min(min_y, pos.y)
                max_x = math.max(max_x, pos.x)
                max_y = math.max(max_y, pos.y)
            end
        end
    end

    if count == 0 then
        return {error = "no capturable entities in area"}
    end

    if not (radius and tonumber(radius) > 0) then
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
    end

    local pad = 1
    local area = {
        left_top = {x = min_x - pad, y = min_y - pad},
        right_bottom = {x = max_x + pad, y = max_y + pad},
    }

    local bp = character.cursor_stack
    bp.set_stack({name = "blueprint"})
    bp.create_blueprint({
        surface = surface,
        force = force,
        area = area,
        include_entities = true,
        include_modules = true,
        include_station_names = true,
        include_trains = true,
        include_fuel = true,
    })
    local stack_string = bp.export_stack()
    bp.clear()

    return {
        -- Extra literal quotes mirror the admin save tool: without them the
        -- RCON dump parser reads the leading "0e" of exchange strings as
        -- scientific notation and shreds the payload.
        blueprint = '"' .. stack_string .. '"',
        center_x = center_x,
        center_y = center_y,
        entity_count = count,
    }
end

-- Construction-time charge per revived entity, debited against the task
-- clock so mass placement is not instantaneous infrastructure creation.
local CONSTRUCTION_TICKS_PER_ENTITY = 15

local function place(player_index, bp_string, x, y)
    local surface = game.surfaces["nauvis"]
    local character = storage.agent_characters[player_index]
    local force = character.force

    local bp_entity = surface.create_entity({
        name = "item-on-ground",
        position = {x = x, y = y},
        stack = "blueprint",
    })
    if not bp_entity then
        return {error = "could not create blueprint carrier"}
    end

    -- import_stack returns an error count (0 on success); validity is
    -- judged by whether the stack ends up holding a usable blueprint.
    local import_result = bp_entity.stack.import_stack(bp_string)
    if not bp_entity.stack.is_blueprint_setup() then
        bp_entity.destroy()
        return {
            error = "invalid blueprint string",
            import_result = import_result,
        }
    end

    local bp_ghost = bp_entity.stack.build_blueprint({
        surface = surface,
        force = force,
        position = {x = x, y = y},
        force_build = true,
    })
    bp_entity.destroy()

    -- Tile ghosts are out of scope for v1 placement economics: remove them
    -- rather than silently materializing terrain.
    local buildable = {}
    local tiles_skipped = 0
    for _, ghost in pairs(bp_ghost) do
        if ghost.valid and ghost.ghost_type == "tile" then
            ghost.destroy()
            tiles_skipped = tiles_skipped + 1
        else
            table.insert(buildable, ghost)
        end
    end

    -- Aggregate the full material bill before placing anything: placement is
    -- all-or-nothing and every entity is paid for out of character inventory.
    local inventory = character.get_main_inventory()
    if not inventory then
        for _, ghost in pairs(buildable) do
            if ghost.valid then ghost.destroy() end
        end
        return {error = "no accessible character inventory"}
    end

    local costs = {}
    for _, ghost in pairs(buildable) do
        local item_name = ghost.ghost_name
        -- Factorio 2.0 moved item prototypes to the global prototypes table.
        if item_name and prototypes.item[item_name] then
            costs[item_name] = (costs[item_name] or 0) + 1
        end
        local requests = ghost.item_requests
        if requests then
            for item, count in pairs(requests) do
                costs[item] = (costs[item] or 0) + tonumber(count) or count
            end
        end
    end

    local missing = {}
    local total_bill = 0
    for item, count in pairs(costs) do
        total_bill = total_bill + count
        local available = inventory.get_item_count(item)
        if available < count then
            missing[item] = count - available
        end
    end
    if next(missing) ~= nil then
        for _, ghost in pairs(buildable) do
            if ghost.valid then ghost.destroy() end
        end
        return {
            error = "missing_materials",
            missing = missing,
            requested_entities = #buildable,
        }
    end

    for item, count in pairs(costs) do
        inventory.remove({name = item, count = count})
    end

    -- Revive ghosts immediately except rolling stock, which must wait until
    -- rails exist. Mirrors the admin loader minus privileged side effects.
    local deferred = {}
    local placed = 0
    for _, ghost in ipairs(buildable) do
        if (
            ghost.ghost_name == "locomotive"
            or ghost.ghost_name == "cargo-wagon"
            or ghost.ghost_name == "fluid-wagon"
        ) then
            table.insert(deferred, ghost)
        else
            local p, ri = ghost.revive()
            if p ~= nil or ri ~= nil then
                placed = placed + 1
            end
        end
    end
    for _, ghost in pairs(deferred) do
        local p, ri = ghost.revive()
        if p ~= nil or ri ~= nil then
            placed = placed + 1
        end
    end

    storage.elapsed_ticks = (storage.elapsed_ticks or 0)
        + placed * CONSTRUCTION_TICKS_PER_ENTITY

    return {
        placed = placed,
        requested = #bp_ghost,
        items_consumed = costs,
        construction_ticks_charged = placed * CONSTRUCTION_TICKS_PER_ENTITY,
        tiles_skipped = tiles_skipped,
    }
end

storage.actions.blueprint = function(
    player_index, command, a, b, c
)
    command = command or "list"
    if command == "capture" then
        return collect_area(player_index, tonumber(a) or 0, tonumber(b) or 0, c)
    elseif command == "place" then
        return place(player_index, a, tonumber(b) or 0, tonumber(c) or 0)
    end
    return {error = "unknown command: " .. tostring(command)}
end
