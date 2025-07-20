global.actions.render = function(player_index, include_status, radius, compression_level)
    local player = global.agent_characters[player_index]
    if not player then
        return nil, "Player not found"
    end

    compression_level = compression_level or "standard"

    local surface = player.surface
    local player_position = player.position

    -- Define search area around player
    local area = {
        left_top = {
            x = player_position.x - radius,
            y = player_position.y - radius
        },
        right_bottom = {
            x = player_position.x + radius,
            y = player_position.y + radius
        }
    }

    -- ENTITIES - Keep as is, they're already relatively efficient
    local entities = surface.find_entities(area)
    local entity_data = {}

    for _, entity in pairs(entities) do
        if entity.valid then
            local data = {
                name = "\""..entity.name.."\"",
                position = {
                    x = entity.position.x,
                    y = entity.position.y
                },
                direction = entity.direction or 0
            }

            if entity.type == 'underground-belt' then
                if entity.belt_to_ground_type then
                    data.type = entity.belt_to_ground_type
                end
            end

            if include_status and entity.status then
                data.status = entity.status
            end

            table.insert(entity_data, data)
        end
    end

    -- WATER TILES - Optimized using run-length encoding
    local water_runs = {}
    local min_x = math.floor(area.left_top.x)
    local max_x = math.ceil(area.right_bottom.x)
    local min_y = math.floor(area.left_top.y)
    local max_y = math.ceil(area.right_bottom.y)

    -- Scan row by row for water runs
    for y = min_y, max_y do
        local current_type = nil
        local run_start = nil

        for x = min_x, max_x + 1 do  -- +1 to close final run
            local tile = (x <= max_x) and surface.get_tile(x, y) or nil
            local is_water = tile and tile.valid and (tile.name:find("water") or tile.name == "deepwater" or tile.name == "water")
            local tile_type = is_water and tile.name or nil

            if tile_type ~= current_type then
                -- Close previous run if it was water
                if current_type then
                    table.insert(water_runs, {
                        t = current_type,  -- Short key names
                        x = run_start,
                        y = y,
                        l = x - run_start  -- length
                    })
                end

                -- Start new run if water
                if tile_type then
                    current_type = tile_type
                    run_start = x
                else
                    current_type = nil
                end
            end
        end
    end

    -- RESOURCES - Optimized by grouping into patches
    local resource_types = {"iron-ore", "copper-ore", "coal", "stone", "uranium-ore", "crude-oil"}
    local resources = {}

    for _, resource_type in ipairs(resource_types) do
        local resource_entities = surface.find_entities_filtered{
            area = area,
            name = resource_type
        }

        if #resource_entities > 0 then
            -- For dense patches, store as relative positions
            local patches = {}
            local processed = {}

            -- Simple clustering - group resources within 3 tiles of each other
            for i, entity in ipairs(resource_entities) do
                if not processed[i] then
                    local patch = {
                        c = {  -- center
                            math.floor(entity.position.x),
                            math.floor(entity.position.y)
                        },
                        e = {{0, 0, entity.amount}}  -- entities as [dx, dy, amount]
                    }
                    processed[i] = true

                    -- Find nearby resources
                    for j = i + 1, #resource_entities do
                        if not processed[j] then
                            local other = resource_entities[j]
                            local dx = other.position.x - patch.c[1]
                            local dy = other.position.y - patch.c[2]

                            if math.abs(dx) <= 3 and math.abs(dy) <= 3 then
                                table.insert(patch.e, {dx, dy, other.amount})
                                processed[j] = true
                            end
                        end
                    end

                    table.insert(patches, patch)
                end
            end

            if #patches > 0 then
                resources[resource_type] = patches
            end
        end
    end

    -- Handle binary compression if requested
    if compression_level == "binary" or compression_level == "maximum" then
        -- Convert water runs to binary format
        local water_binary = encode_water_binary(water_runs)
        local resources_binary = encode_resources_binary(resources)

        return {
            entities = entity_data,
            water_binary = water_binary,  -- URL-safe Base64 encoded binary data
            resources_binary = resources_binary,  -- URL-safe Base64 encoded binary data
            -- Include metadata for decoding
            meta = {
                area = area,
                format = "\"v2-binary\""
            }
        }
    else
        -- Standard v2 format
        return {
            entities = entity_data,
            water = water_runs,
            resources = resources,
            -- Include metadata for decoding
            meta = {
                area = area,
                format = "v2"
            }
        }
    end
end

-- Binary packing functions (since string.pack isn't available in Factorio's Lua 5.2)
function pack_uint8(n)
    return string.char(bit32.band(n, 0xFF))
end

function pack_int16(n)
    -- Convert to signed representation if needed
    if n < 0 then
        n = 65536 + n
    end
    return string.char(
        bit32.band(bit32.rshift(n, 8), 0xFF),
        bit32.band(n, 0xFF)
    )
end

function pack_uint16(n)
    return string.char(
        bit32.band(bit32.rshift(n, 8), 0xFF),
        bit32.band(n, 0xFF)
    )
end

function pack_uint32(n)
    return string.char(
        bit32.band(bit32.rshift(n, 24), 0xFF),
        bit32.band(bit32.rshift(n, 16), 0xFF),
        bit32.band(bit32.rshift(n, 8), 0xFF),
        bit32.band(n, 0xFF)
    )
end

function pack_int8(n)
    -- Convert to unsigned representation
    if n < 0 then
        n = 256 + n
    end
    return string.char(bit32.band(n, 0xFF))
end

-- Binary encoding functions
function encode_water_binary(water_runs)
    local TILE_TYPES = {
        ['water'] = 1,
        ['deepwater'] = 2,
        ['water-green'] = 3,
        ['water-mud'] = 4,
        ['water-shallow'] = 5
    }

    local data = {}

    for _, run in ipairs(water_runs) do
        local tile_type = TILE_TYPES[run.t] or 1
        local x = run.x
        local y = run.y
        local length = math.min(run.l, 255)  -- Cap at 255 for single byte

        -- Pack as: type(u8), x(i16), y(i16), length(u8)
        table.insert(data, pack_uint8(tile_type))
        table.insert(data, pack_int16(x))
        table.insert(data, pack_int16(y))
        table.insert(data, pack_uint8(length))
    end

    -- Concatenate all binary data and base64 encode
    local binary_data = table.concat(data)
    return base64_encode(binary_data)
end

function encode_resources_binary(resource_patches)
    local RESOURCE_TYPES = {
        ['iron-ore'] = 1,
        ['copper-ore'] = 2,
        ['coal'] = 3,
        ['stone'] = 4,
        ['uranium-ore'] = 5,
        ['crude-oil'] = 6
    }

    local data = {}

    for resource_name, patches in pairs(resource_patches) do
        local resource_type = RESOURCE_TYPES[resource_name] or 0
        if resource_type > 0 then
            -- Write resource type and patch count
            table.insert(data, pack_uint8(resource_type))
            table.insert(data, pack_uint16(#patches))

            for _, patch in ipairs(patches) do
                local center = patch.c
                local entities = patch.e

                -- Write patch header: center_x(i16), center_y(i16), entity_count(u16)
                table.insert(data, pack_int16(center[1]))
                table.insert(data, pack_int16(center[2]))
                table.insert(data, pack_uint16(#entities))

                -- Write entities
                for _, entity in ipairs(entities) do
                    local dx = math.max(-128, math.min(127, entity[1]))  -- Clamp to signed byte range
                    local dy = math.max(-128, math.min(127, entity[2]))
                    local amount = entity[3]

                    -- Pack as: dx(i8), dy(i8), amount(u32)
                    table.insert(data, pack_int8(dx))
                    table.insert(data, pack_int8(dy))
                    table.insert(data, pack_uint32(amount))
                end
            end
        end
    end

    local binary_data = table.concat(data)
    return base64_encode(binary_data)
end

-- Base64 encoding function (URL-safe variant to avoid RCON issues)
function base64_encode(data)
    -- Use - and _ instead of + and / to avoid RCON command interpretation
    local b='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
    return ((data:gsub('.', function(x)
        local r,b='',x:byte()
        for i=8,1,-1 do r=r..(b%2^i-b%2^(i-1)>0 and '1' or '0') end
        return r;
    end)..'0000'):gsub('%d%d%d?%d?%d?%d?', function(x)
        if (#x < 6) then return '' end
        local c=0
        for i=1,6 do c=c+(x:sub(i,i)=='1' and 2^(6-i) or 0) end
        return b:sub(c+1,c+1)
    end)..({ '', '==', '=' })[#data%3+1])
end