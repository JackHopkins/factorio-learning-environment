-- Hidden world disruptions: resource depletion, entity destruction, and
-- enemy waves.  Command-driven (fired by the worker sync loop), never
-- event-scheduled: an error here fails one RCON call, not the simulation.

local ENEMY_TIERS = {
    small = "small-biter",
    medium = "medium-biter",
    big = "big-biter",
    behemoth = "behemoth-biter",
}

local function factory_centroid(player_index)
    local ok, centroid = pcall(function()
        return storage.actions.get_factory_centroid(player_index)
    end)
    if ok and type(centroid) == "table" then
        -- Tool may return {x, y} directly or wrapped as {centroid = {x, y}}.
        local inner = centroid.centroid or centroid
        if inner and inner.x then
            return {x = inner.x, y = inner.y}
        end
    end
    local character = storage.agent_characters
        and storage.agent_characters[player_index] or nil
    if character and character.valid then
        return {x = character.position.x, y = character.position.y}
    end
    return {x = 0, y = 0}
end

local function resolve_target(player_index, parameters)
    if parameters.position and parameters.position.x then
        return {
            x = tonumber(parameters.position.x) or 0,
            y = tonumber(parameters.position.y) or 0,
        }
    end
    return factory_centroid(player_index)
end

local function is_protected(entity)
    if entity.type == "character" or entity.type == "player" then
        return true
    end
    -- Customer sink depots are benchmark property, never blast radius.
    if storage.customer and storage.customer.depots then
        for _, depot in pairs(storage.customer.depots) do
            if depot == entity then
                return true
            end
        end
    end
    return false
end

-- Products whose supply chain runs through an entity about to be destroyed,
-- so recovery can be measured on affected networks rather than global totals.
local function affected_products(entity)
    local ok, recipe = pcall(function()
        return entity.get_recipe()
    end)
    if ok and recipe and recipe.products then
        local names = {}
        for _, product in pairs(recipe.products) do
            if product.name then
                names[product.name] = true
            end
        end
        return names
    end
    return {}
end

local function merge_products(into, from)
    for name in pairs(from or {}) do
        into[name] = true
    end
end

storage.actions.perturbation = function(player_index, command, parameters)
    parameters = parameters or {}
    local character = storage.agent_characters
        and storage.agent_characters[player_index] or nil
    local surface = character and character.valid
        and character.surface or game.surfaces[1]

    if command == "deplete_area" then
        local target = resolve_target(player_index, parameters)
        local radius = math.max(tonumber(parameters.radius) or 24, 1)
        local filters = parameters.resources or {}
        local area = {
            {target.x - radius, target.y - radius},
            {target.x + radius, target.y + radius},
        }
        local found = surface.find_entities_filtered({
            type = "resource",
            area = area,
            name = (#filters > 0) and filters or nil,
        })
        local destroyed = {}
        local total = 0
        for _, entity in pairs(found) do
            if entity.valid and not is_protected(entity) then
                local name = entity.name
                if entity.destroy() then
                    destroyed[name] = (destroyed[name] or 0) + 1
                    total = total + 1
                end
            end
        end
        return {
            destroyed = destroyed,
            total = total,
            target = target,
            radius = radius,
            -- Depleted ores gate their own extraction-rate recovery; Python
            -- maps them to smelted outputs downstream.
            affected_products = (function()
                local names = {}
                for name in pairs(destroyed) do
                    names[name] = true
                end
                return names
            end)(),
        }

    elseif command == "destroy_entities" then
        local target = resolve_target(player_index, parameters)
        local count = math.max(tonumber(parameters.count) or 1, 1)
        local search_radius = math.max(
            tonumber(parameters.search_radius) or 200, 1
        )
        local types = parameters.entity_types or {}
        local names = parameters.entity_names or {}
        local area = {
            {target.x - search_radius, target.y - search_radius},
            {target.x + search_radius, target.y + search_radius},
        }
        local found = surface.find_entities_filtered({
            area = area,
            type = (#types > 0) and types or nil,
            name = (#names > 0) and names or nil,
        })
        local candidates = {}
        for _, entity in pairs(found) do
            if entity.valid and not is_protected(entity) then
                table.insert(candidates, entity)
            end
        end
        table.sort(candidates, function(a, b)
            local da = (a.position.x - target.x) ^ 2
                + (a.position.y - target.y) ^ 2
            local db = (b.position.x - target.x) ^ 2
                + (b.position.y - target.y) ^ 2
            return da < db
        end)
        local destroyed = {}
        local affected = {}
        local total = 0
        for index, entity in pairs(candidates) do
            if total >= count then
                break
            end
            local name = entity.name
            merge_products(affected, affected_products(entity))
            if entity.destroy() then
                destroyed[name] = (destroyed[name] or 0) + 1
                total = total + 1
            end
            candidates[index] = nil
        end
        local product_list = {}
        for name in pairs(affected) do
            table.insert(product_list, name)
        end
        table.sort(product_list)
        return {
            destroyed = destroyed,
            total = total,
            requested = count,
            available = #candidates + total,
            target = target,
            affected_products = product_list,
        }

    elseif command == "spawn_enemies" then
        local target = resolve_target(player_index, parameters)
        local count = math.max(tonumber(parameters.count) or 5, 1)
        local tier = ENEMY_TIERS[parameters.tier or "small"]
            or ENEMY_TIERS.small
        local spawned = 0
        local positions = {}
        for index = 1, count * 4 do
            if spawned >= count then
                break
            end
            local angle = (index * 2.399963) % (2 * math.pi)
            local distance = 25 + (index % 4) * 5
            local position = {
                x = target.x + math.cos(angle) * distance,
                y = target.y + math.sin(angle) * distance,
            }
            local safe = surface.find_non_colliding_position(
                tier, position, 8, 1
            )
            if safe then
                local created = surface.create_entity({
                    name = tier,
                    position = safe,
                    force = game.forces.enemy,
                })
                if created then
                    spawned = spawned + 1
                    table.insert(positions, {x = safe.x, y = safe.y})
                end
            end
        end
        return {
            spawned = spawned,
            requested = count,
            tier = tier,
            positions = positions,
        }
    end

    return {error = "unknown command: " .. tostring(command)}
end
