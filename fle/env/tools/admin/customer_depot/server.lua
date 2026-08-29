-- Customer-owned sink depots: immutable delivery boundary for contract
-- fulfillment.  Items inserted into a depot are counted per 60-tick bucket
-- and immediately destroyed, so credited deliveries can never be extracted
-- back out and reused.

storage.customer = storage.customer or {
    depots = {},           -- unit_number -> LuaEntity reference
    depot_specs = {},      -- unit_number -> {position = {x, y}, surface = name}
    delivered_total = {},  -- item -> cumulative count consumed by sinks
    manual_delivered_total = {}, -- item -> direct agent insertions (not credited)
    manual_pending = {},   -- unit_number -> item -> direct insertions awaiting drain
    delta_log = {},        -- array of {start_tick = t, items = {item = delta}}
    tamper_events = {},    -- array of {tick, unit_number, reason}
    tamper_reported = {},  -- unit_number -> true (dedupe)
    handlers_installed = false,
    epoch_tick = nil,      -- absolute game.tick at episode start
}

-- Populate fields added after an episode was created. Scenario tool files can
-- be reloaded without reconstructing the shared storage table.
storage.customer.delivered_total = storage.customer.delivered_total or {}
storage.customer.manual_delivered_total = storage.customer.manual_delivered_total or {}
storage.customer.manual_pending = storage.customer.manual_pending or {}

local BUCKET_TICKS = 60
local DRAIN_EVERY_TICKS = 6

-- The canonical episode clock: game.tick minus the episode epoch. Schedules,
-- buckets, and telemetry all use this so contract timing cannot drift against
-- the resettable task clock used by objectives.
local function episode_tick()
    local epoch = storage.customer.epoch_tick or game.tick
    return game.tick - epoch
end

local function ensure_bucket(tick)
    local start_tick = math.floor(tick / BUCKET_TICKS) * BUCKET_TICKS
    for _, bucket in ipairs(storage.customer.delta_log) do
        if bucket.start_tick == start_tick then
            return bucket
        end
    end
    local bucket = {start_tick = start_tick, items = {}}
    table.insert(storage.customer.delta_log, bucket)
    return bucket
end

local function make_depot(surface, position)
    local entity = surface.create_entity({
        name = "steel-chest",
        position = position,
        force = game.forces.player,
    })
    if not entity then
        return nil
    end
    entity.destructible = false
    entity.operable = false
    pcall(function()
        entity.minable_flag = false
    end)
    storage.customer.depots[entity.unit_number] = entity
    storage.customer.depot_specs[entity.unit_number] = {
        position = {x = entity.position.x, y = entity.position.y},
        surface = surface.name,
    }
    return entity
end

local function clear_depots()
    for _, entity in pairs(storage.customer.depots) do
        if entity and entity.valid then
            pcall(function() entity.destroy() end)
        end
    end
    storage.customer.depots = {}
    storage.customer.depot_specs = {}
    storage.customer.delivered_total = {}
    storage.customer.manual_delivered_total = {}
    storage.customer.manual_pending = {}
    storage.customer.delta_log = {}
    storage.customer.tamper_events = {}
    storage.customer.tamper_reported = {}
end

local function record_tamper(unit_number, tick, reason)
    if storage.customer.tamper_reported[unit_number] then
        return
    end
    storage.customer.tamper_reported[unit_number] = true
    table.insert(storage.customer.tamper_events, {
        tick = tick,
        unit_number = unit_number,
        reason = reason,
    })
end

local function sink_contents(inventory)
    -- Factorio 2.0 returns get_contents() as an array of {name, count,
    -- quality} entries; normalise to {item_name = count}.
    if not inventory then
        return {}
    end
    local contents = {}
    for _, item in pairs(inventory.get_contents()) do
        contents[item.name] = (contents[item.name] or 0) + item.count
    end
    return contents
end

local function drain_depots(tick)
    local active_bucket = nil
    local replacements = {}
    for unit_number, entity in pairs(storage.customer.depots) do
        if not entity.valid then
            record_tamper(unit_number, tick, "depot_entity_missing")
            local spec = storage.customer.depot_specs[unit_number]
            if spec and game.surfaces[spec.surface] then
                replacements[unit_number] = spec
            end
        else
            local inventory = entity.get_inventory(defines.inventory.chest)
            if inventory then
                local contents = sink_contents(inventory)
                local pending = storage.customer.manual_pending[unit_number] or {}
                local has_items = false
                for name, count in pairs(contents) do
                    has_items = true
                    active_bucket = active_bucket or ensure_bucket(tick)
                    active_bucket.manual_items = active_bucket.manual_items or {}
                    local manual_count = math.min(pending[name] or 0, count)
                    local automated_count = count - manual_count
                    if automated_count > 0 then
                        active_bucket.items[name] =
                            (active_bucket.items[name] or 0) + automated_count
                        storage.customer.delivered_total[name] =
                            (storage.customer.delivered_total[name] or 0) + automated_count
                    end
                    if manual_count > 0 then
                        active_bucket.manual_items[name] =
                            (active_bucket.manual_items[name] or 0) + manual_count
                        storage.customer.manual_delivered_total[name] =
                            (storage.customer.manual_delivered_total[name] or 0) + manual_count
                    end
                end
                if has_items then
                    inventory.clear()
                end
                storage.customer.manual_pending[unit_number] = nil
            end
        end
    end
    -- Rebuild destroyed depots only after iteration completes: inserting
    -- into a table during pairs() traversal is undefined behavior.
    for unit_number, spec in pairs(replacements) do
        local surface = game.surfaces[spec.surface]
        if surface and make_depot(surface, spec.position) then
            storage.customer.tamper_reported[unit_number] = nil
        end
    end
end

if not storage.customer.handlers_installed then
    script.on_nth_tick(DRAIN_EVERY_TICKS, function(event)
        -- A telemetry bug must degrade to missing data, never kill the
        -- simulation: an unhandled error inside a scenario event handler is
        -- fatal for the running multiplayer game.
        local ok, err = pcall(function()
            if storage.customer and storage.customer.depots then
                drain_depots(episode_tick())
            end
        end)
        if not ok and storage.customer then
            storage.customer.last_error = tostring(err)
        end
    end)
    storage.customer.handlers_installed = true
end

storage.actions.customer_depot = function(player_index, command, x, y, chest_count, relative)
    command = command or "telemetry"

    if command == "place" then
        clear_depots()
        -- Pin the episode epoch: all contract scheduling runs on
        -- game.tick - epoch_tick so buckets are episode-relative.
        storage.customer.epoch_tick = game.tick
        local character = storage.agent_characters
            and storage.agent_characters[player_index] or nil
        local surface = character and character.valid
            and character.surface or game.surfaces[1]
        chest_count = math.max(1, math.min(chest_count or 8, 64))
        local anchor_x = x or 0
        local anchor_y = y or 0
        if relative and character and character.valid then
            anchor_x = character.position.x + (x or 0)
            anchor_y = character.position.y + (y or 0)
        end
        local placed = 0
        local slot = 0
        while placed < chest_count and slot < chest_count * 8 do
            local position = {x = anchor_x + slot * 2, y = anchor_y}
            if surface.can_place_entity({name = "steel-chest", position = position}) then
                if make_depot(surface, position) then
                    placed = placed + 1
                end
            end
            slot = slot + 1
        end
        return {
            placed = placed,
            requested = chest_count,
            depots = storage.customer.depot_specs,
        }
    elseif command == "telemetry" then
        local buckets = storage.customer.delta_log
        storage.customer.delta_log = {}
        local depot_summary = {}
        for unit_number, entity in pairs(storage.customer.depots) do
            local spec = storage.customer.depot_specs[unit_number] or {}
            table.insert(depot_summary, {
                unit_number = unit_number,
                valid = entity.valid,
                entity_name = "steel-chest",
                position = spec.position,
                surface = spec.surface,
                customer_owned = true,
                consumes_deliveries = true,
            })
        end
        return {
            tick = episode_tick(),
            epoch_tick = storage.customer.epoch_tick,
            delivery_bucket_ticks = BUCKET_TICKS,
            -- Automated traffic is the crediting channel. Direct insertion is
            -- exposed separately for audit and cannot satisfy a contract.
            raw_delivery_totals = storage.customer.delivered_total,
            delivered_total = storage.customer.delivered_total,
            manual_delivery_totals = storage.customer.manual_delivered_total,
            buckets = buckets,
            depots = depot_summary,
            tamper_events = storage.customer.tamper_events,
            last_error = storage.customer.last_error,
        }
    elseif command == "adopt" then
        -- Reattach verifier state after GameState restores the physical world
        -- into an isolated audit instance. No new entities are created.
        local specs = x or {}
        storage.customer.depots = {}
        storage.customer.depot_specs = {}
        storage.customer.delivered_total = {}
        storage.customer.manual_delivered_total = {}
        storage.customer.manual_pending = {}
        storage.customer.delta_log = {}
        storage.customer.tamper_events = {}
        storage.customer.tamper_reported = {}
        storage.customer.epoch_tick = game.tick
        local adopted = 0
        for _, spec in pairs(specs) do
            local surface = game.surfaces[spec.surface or 1]
            local position = spec.position
            if surface and position then
                local entities = surface.find_entities_filtered({
                    position = position,
                    name = "steel-chest",
                    force = game.forces.player,
                })
                local entity = entities[1]
                if entity and entity.valid then
                    local inventory = entity.get_inventory(defines.inventory.chest)
                    if inventory then
                        -- Snapshot state cannot carry manual-delivery provenance.
                        -- Discard candidate-time contents conservatively so a
                        -- preloaded depot cannot become autonomous audit credit.
                        inventory.clear()
                    end
                    entity.destructible = false
                    entity.operable = false
                    pcall(function() entity.minable_flag = false end)
                    storage.customer.depots[entity.unit_number] = entity
                    storage.customer.depot_specs[entity.unit_number] = {
                        position = {x = entity.position.x, y = entity.position.y},
                        surface = surface.name,
                    }
                    adopted = adopted + 1
                end
            end
        end
        return {adopted = adopted, requested = #specs}
    elseif command == "clear" then
        clear_depots()
        return {cleared = true}
    end

    return {error = "unknown command: " .. tostring(command)}
end
