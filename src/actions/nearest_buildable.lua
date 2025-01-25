-- Cache math functions
local floor = math.floor
local ceil = math.ceil
local max = math.max
local abs = math.abs

global.actions.nearest_buildable = function(player_index, entity_name, bounding_box, center_position)
    local player = game.get_player(player_index)
    local surface = player.surface
    local entity_prototype = game.entity_prototypes[entity_name]
    local needs_resources = entity_prototype.resource_categories ~= nil
    local start_pos = center_position or player.position

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
                        surface = surface,
                        left_top = left_top,
                        right_bottom = right_bottom,
                        filled = false,
                        color = {r=0, g=1, b=0, a=0.5},
                        time_to_live = 6000
                    }
                    return current_pos
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

global.actions.nearest_buildable2 = function(player_index, entity_name, bounding_box)
    local player = game.get_player(player_index)

    local surface = player.surface
    local entity_prototype = game.entity_prototypes[entity_name]
    local needs_resources = entity_prototype.resource_categories ~= nil

    -- Cache frequently accessed values
    local start_pos = player.position
    local MAX_RADIUS = 50

    -- Pre-calculate collision masks once
    local collision_masks = {"object-layer"}
    if needs_resources then
        table.insert(collision_masks, "resource-layer")
    end

    -- Optimized buildable box check function
    local function is_buildable_box(origin, box_dimensions)
        -- Calculate actual positions once
        local left_top = {
            x = origin.x + box_dimensions.left_top.x,
            y = origin.y + box_dimensions.left_top.y
        }
        local right_bottom = {
            x = origin.x + box_dimensions.right_bottom.x,
            y = origin.y + box_dimensions.right_bottom.y
        }
        local area = {left_top, right_bottom}

        -- Quick initial checks first (fail fast)
        -- Water check
        if surface.count_tiles_filtered{
            area = area,
            collision_mask = "water-tile"
        } > 0 then
            return false
        end

        -- Collision check
        if surface.count_entities_filtered{
            area = area,
            collision_mask = "object-layer"
        } > 0 then
            return false
        end

        -- Resource check (only if needed)
        if needs_resources then
            -- Get dimensions of the area we need to check
            local min_x = math.floor(left_top.x)
            local min_y = math.floor(left_top.y)
            local max_x = math.ceil(right_bottom.x) - 1
            local max_y = math.ceil(right_bottom.y) - 1

            -- Get all resources in chunks that overlap our area
            local chunk_min_x = math.floor(min_x / 32)
            local chunk_min_y = math.floor(min_y / 32)
            local chunk_max_x = math.floor(max_x / 32)
            local chunk_max_y = math.floor(max_y / 32)

            -- Create a lookup table for quick position checks
            local resource_positions = {}

            -- Get resources chunk by chunk
            for chunk_x = chunk_min_x, chunk_max_x do
                for chunk_y = chunk_min_y, chunk_max_y do
                    local chunk_area = {
                        {chunk_x * 32, chunk_y * 32},
                        {(chunk_x + 1) * 32, (chunk_y + 1) * 32}
                    }

                    local resources = surface.find_entities_filtered{
                        area = chunk_area,
                        collision_mask = "resource-layer"
                    }

                    for _, resource in pairs(resources) do
                        local x = math.floor(resource.position.x)
                        local y = math.floor(resource.position.y)
                        -- Only add if within our actual area of interest
                        if x >= min_x and x <= max_x and
                           y >= min_y and y <= max_y then
                            resource_positions[x .. "," .. y] = true
                        end
                    end
                end
            end

            -- Check coverage using our lookup table
            for x = min_x, max_x do
                for y = min_y, max_y do
                    if not resource_positions[x .. "," .. y] then
                        return false
                    end
                end
            end
        end

        return true, left_top, right_bottom
    end

    -- Optimized spiral search pattern
    local function spiral_search()
        local dx, dy = 0, 0
        local segment_length = 1
        local segment_passed = 0
        local direction = 0  -- 0: right, 1: down, 2: left, 3: up

        while math.max(math.abs(dx), math.abs(dy)) <= MAX_RADIUS do
            local current_pos = {
                x = start_pos.x + dx,
                y = start_pos.y + dy
            }

            -- Check buildability
            if bounding_box then
                local is_buildable, left_top, right_bottom = is_buildable_box(current_pos, bounding_box)
                -- Draw success indicator
                rendering.clear()
                rendering.draw_rectangle{
                    surface = surface,
                    left_top = left_top,
                    right_bottom = right_bottom,
                    filled = false,
                    color = {r=0, g=1, b=0, a=0.5}
                }
                if is_buildable then
                    return current_pos
                end
            else
                -- Simple position check for entities without bounding box
                if surface.count_entities_filtered{
                    area = {{current_pos.x, current_pos.y},
                           {current_pos.x + 1, current_pos.y + 1}},
                    collision_mask = collision_masks
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

global.actions.nearest_buildable_brute_force = function(player_index, entity_name, bounding_box)
    local player = game.get_player(player_index)
    rendering.clear()

    -- Get entity prototype once
    local entity_prototype = game.entity_prototypes[entity_name]

    -- Check if entity needs resources (has resource_categories)
    local needs_resources = entity_prototype.resource_categories ~= nil

    -- Function to check if all positions within a bounding box are buildable
    local function is_buildable_box(surface, origin, force, box_dimensions)
        -- Calculate actual corner positions relative to origin
        local actual_left_top = {
            x = origin.x + box_dimensions.left_top.x,
            y = origin.y + box_dimensions.left_top.y
        }
        local actual_right_bottom = {
            x = origin.x + box_dimensions.right_bottom.x,
            y = origin.y + box_dimensions.right_bottom.y
        }

        -- Basic water collision check
        local water_tiles = surface.count_tiles_filtered{
            area = {actual_left_top, actual_right_bottom},
            collision_mask = "water-tile"
        }

        if water_tiles > 0 then
            return false
        end


        -- Basic collision check
        local colliding_entities = surface.count_entities_filtered{
            area = {actual_left_top, actual_right_bottom},
            collision_mask = "object-layer"
        }

        if colliding_entities > 0 then
            return false
        end

        -- For miners, check if there are enough resources
        if needs_resources then
            local resource_count = surface.count_entities_filtered{
                area = {actual_left_top, actual_right_bottom},
                collision_mask = "resource-layer"
            }

            -- Area of the bounding box
            local width = actual_right_bottom.x - actual_left_top.x + 1
            local height = actual_right_bottom.y - actual_left_top.y + 1
            local area = width * height

            -- Check if resources cover the entire area
            if resource_count < area then
                return false
            end
        end

        return true, actual_left_top, actual_right_bottom
    end

    -- Function to find nearest position where the entire bounding box is buildable
    local function find_nearest_buildable_position(player, box_dimensions)
        local surface = player.surface
        local force = player.force
        local position = player.position
        local search_radius = 1
        local max_search_radius = 50
        local search_increment = 1

        -- If no bounding box provided, use single position check
        if not box_dimensions then
            while search_radius <= max_search_radius do
                for dx = -search_radius, search_radius, search_increment do
                    for dy = -search_radius, search_radius, search_increment do
                        local search_position = {x = position.x + dx, y = position.y + dy}

                        -- Check single position
                        local colliding = surface.count_entities_filtered{
                            area = {{search_position.x, search_position.y},
                                   {search_position.x + 1, search_position.y + 1}},
                            collision_mask = "object-layer"
                        }

                        if colliding == 0 and (not needs_resources or
                            surface.count_entities_filtered{
                                area = {{search_position.x, search_position.y},
                                       {search_position.x + 1, search_position.y + 1}},
                                collision_mask = "resource-layer"
                            } > 0) then
                            return search_position
                        end
                    end
                end
                search_radius = search_radius + search_increment
            end
        else
            -- Search with bounding box validation
            while search_radius <= max_search_radius do
                for dx = -search_radius, search_radius, search_increment do
                    for dy = -search_radius, search_radius, search_increment do
                        local search_position = {x = position.x + dx, y = position.y + dy}
                        local is_buildable, actual_left_top, actual_right_bottom =
                            is_buildable_box(surface, search_position, force, box_dimensions)

                        if is_buildable then
                            -- Draw the actual buildable area
                            rendering.draw_rectangle{
                                surface = player.surface,
                                left_top = actual_left_top,
                                right_bottom = actual_right_bottom,
                                filled = false,
                                color = {r=0, g=1, b=0, a=0.5}
                            }
                            return search_position
                        end
                    end
                end
                search_radius = search_radius + search_increment
            end
        end
        error("\"Could not find a buildable position for the entity: " .. entity_name.."\"")
    end

    return find_nearest_buildable_position(player, bounding_box)
end