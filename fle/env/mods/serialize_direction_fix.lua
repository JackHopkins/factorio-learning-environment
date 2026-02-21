-- Factorio 2.0 direction serialization fix.
-- Patches storage.utils.serialize_entity to convert raw Factorio 2.0
-- direction values (0,4,8,12) to Python Direction enum values (0,2,4,6).
-- Loaded as a separate init script after serialize.lua to avoid RCON
-- packet size truncation issues with the large serialize.lua file.

-- Cache the original serialize_entity
local original_serialize_entity = storage.utils.serialize_entity

-- Inverse direction mapping for entities with non-standard direction semantics.
-- Normal entities: raw direction maps directly (N->N, E->E, S->S, W->W).
-- Inserters and offshore pumps: direction is reversed.
local function inverse_direction(entity_name, raw_dir)
    local prototype = prototypes.entity[entity_name]
    if not prototype then return raw_dir end

    if prototype.type == "inserter" or prototype.name == "offshore-pump" then
        -- These entities have reversed direction semantics
        if raw_dir == defines.direction.north then
            return defines.direction.south
        elseif raw_dir == defines.direction.south then
            return defines.direction.north
        elseif raw_dir == defines.direction.east then
            return defines.direction.west
        elseif raw_dir == defines.direction.west then
            return defines.direction.east
        end
    end

    -- Normal entities: pass through
    return raw_dir
end

-- Override serialize_entity with direction conversion
storage.utils.serialize_entity = function(entity)
    local result = original_serialize_entity(entity)

    -- Fix the main entity direction: convert from raw Factorio 2.0 values to Python enum
    if entity and entity.valid and entity.direction then
        local inversed = inverse_direction(entity.name, entity.direction)
        result.direction = inversed / 2
    end

    -- Fix neighbour directions: convert from raw Factorio 2.0 values to Python enum
    if result.neighbours then
        for _, neighbour in pairs(result.neighbours) do
            if neighbour.direction then
                neighbour.direction = neighbour.direction / 2
            end
        end
    end

    return result
end
