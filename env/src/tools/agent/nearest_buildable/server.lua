-- Cache math functions
local floor = math.floor
local ceil = math.ceil
local max = math.max
local abs = math.abs

global.actions.nearest_buildable = function(player_index, entity_name, bounding_box, center_position)
    local player = global.agent_characters[player_index]
    local surface = player.surface
    local entity_prototype = game.entity_prototypes[entity_name]
    local needs_resources = entity_prototype.resource_categories ~= nil
    local start_pos = center_position or player.position
    local needs_oil = entity_name == "pumpjack"

    -- Cache for chunk resources
    local chunk_cache = {}

    local function get_chunk_resources(chunk_x, chunk_y)
        local cache_key = chunk_x .. "," .. chunk_y
        if not chunk_cache[cache_key] then
            chunk_cache[cache_key] = surface.find_entities_filtered{
                area = {
                    {chunk_x * 32, chunk_y * 32},
                    {(chunk_x + 1) * 32, (chunk_y + 1) * 32}
                },
                collision_mask = "resource-layer"
            }
        end
        return chunk_cache[cache_key]
    end

    local function check_resource_coverage(left_top, right_bottom)
        if not needs_resources then return true end

        if needs_oil then
            local oil_count = surface.count_entities_filtered{
                area = {left_top, right_bottom},
                name = "crude-oil"
            }
            return oil_count > 0
        end
        -- Quick initial resource count check
        local total_resources = surface.count_entities_filtered{
            area = {left_top, right_bottom},
            collision_mask = "resource-layer"
        }

        -- Calculate required coverage
        local min_x = floor(left_top.x)
        local min_y = floor(left_top.y)
        local max_x = ceil(right_bottom.x) - 1
        local max_y = ceil(right_bottom.y) - 1
        local required_coverage = (max_x - min_x + 1) * (max_y - min_y + 1)

        -- Early exit if not enough resources
        if total_resources < required_coverage then
            return false
        end

        -- Set up position tracking
        local positions = {}

        -- Get relevant chunks
        local chunk_min_x = floor(min_x / 32)
        local chunk_min_y = floor(min_y / 32)
        local chunk_max_x = floor(max_x / 32)
        local chunk_max_y = floor(max_y / 32)

        -- Collect resources from relevant chunks
        for chunk_x = chunk_min_x, chunk_max_x do
            for chunk_y = chunk_min_y, chunk_max_y do
                local resources = get_chunk_resources(chunk_x, chunk_y)
                for _, resource in pairs(resources) do
                    local x = floor(resource.position.x)
                    local y = floor(resource.position.y)
                    if x >= min_x and x <= max_x and
                       y >= min_y and y <= max_y then
                        positions[x] = positions[x] or {}
                        positions[x][y] = true
                    end
                end
            end
        end

        -- Verify complete coverage
        for x = min_x, max_x do
            if not positions[x] then return false end
            for y = min_y, max_y do
                if not positions[x][y] then return false end
            end
        end

        return true
    end

    local function is_buildable_box(origin, box_dimensions)
        -- Calculate actual positions
        local left_top = {
            x = origin.x + box_dimensions.left_top.x,
            y = origin.y + box_dimensions.left_top.y
        }
        local right_bottom = {
            x = origin.x + box_dimensions.right_bottom.x,
            y = origin.y + box_dimensions.right_bottom.y
        }

        -- Quick collision checks first
        if surface.count_tiles_filtered{
            area = {left_top, right_bottom},
            collision_mask = "water-tile"
        } > 0 then
            return false
        end

        if surface.count_entities_filtered{
            area = {left_top, right_bottom},
            collision_mask = "object-layer"
        } > 0 then
            return false
        end

        -- Resource coverage check
        if not check_resource_coverage(left_top, right_bottom) then
            return false
        end

        return true, left_top, right_bottom
    end

    local function spiral_search()
        local dx, dy = 0, 0
        local segment_length = 1
        local segment_passed = 0
        local direction = 0  -- 0: right, 1: down, 2: left, 3: up
        local MAX_RADIUS = 30

        while max(abs(dx), abs(dy)) <= MAX_RADIUS do
            local current_pos = {
                x = start_pos.x + dx,
                y = start_pos.y + dy
            }

            if bounding_box then
                local is_buildable, left_top, right_bottom = is_buildable_box(current_pos, bounding_box)
                if is_buildable then
                    --rendering.clear()
                    rendering.draw_rectangle{
                        only_in_alt_mode=true,
                        surface = surface,
                        left_top = left_top,
                        right_bottom = right_bottom,
                        filled = false,
                        color = {r=0, g=1, b=0, a=0.5},
                        time_to_live = 60000
                    }
                    return {position=current_pos, left_top=left_top, right_bottom=right_bottom}
                end
            else
                -- Simple position check for entities without bounding box
                if surface.count_entities_filtered{
                    area = {{current_pos.x, current_pos.y},
                           {current_pos.x + 1, current_pos.y + 1}},
                    collision_mask = needs_resources and "resource-layer" or "object-layer"
                } == (needs_resources and 1 or 0) then
                    return current_pos
                end
            end

            -- Spiral pattern movement
            segment_passed = segment_passed + 1
            if direction == 0 then dx = dx + 1
            elseif direction == 1 then dy = dy + 1
            elseif direction == 2 then dx = dx - 1
            else dy = dy - 1 end

            if segment_passed == segment_length then
                segment_passed = 0
                direction = (direction + 1) % 4
                if direction % 2 == 0 then
                    segment_length = segment_length + 1
                end
            end
        end

        error("\"Could not find a buildable position for the entity: " .. entity_name.."\"")
    end

    return spiral_search()
end
