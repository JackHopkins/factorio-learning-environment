-- Initialise.lua

-- If the global actions table doesn't exist, create it
if not global.actions then
    global.actions = {}
end
if not global.utils then
    global.utils = {}
end

-- Initialize debug flags
if global.debug == nil then
    global.debug = {
        rendering = false -- Flag to toggle debug rendering of polygons and shapes
    }
end


-- Note: The debug_rendering.lua library will be loaded separately by the LuaScriptManager
--local player = game.players[arg1]
player.surface.always_day=true
--game.players[1].character_collision_mask = "not-colliding-with-itself"
player.force.character_build_distance_bonus = 100
player.force.research_all_technologies()


local beam_duration = 9
local surface=player.surface
local pp = player.position
local cnt = 0
local directions = {'north', 'northeast', 'east', 'southeast', 'south', 'southwest', 'west', 'northwest'}

--Initialise.lua
--local position = player.position

--player.game_view_settings.show_controller_gui = false
--player.game_view_settings.show_minimap = false
--player.game_view_settings.show_side_menu = false
--player.game_view_settings.show_quickbar = false
--player.game_view_settings.show_shortcut_bar = false
--player.game_view_settings.show_map_view_options = false
--player.game_view_settings.show_shortcut_bar = false

global.points_of_interest = {}
global.distances_to_nearest = {}
global.relative_points_of_interest = {}
global.interesting_entities = {
    ['enemy']=true,
    ['trees']=true,
    ['iron-ore']=true,
    ['stone']=true,
    ['copper-ore']=true,
    ['uranium-ore']=true,
    ['crude-oil']=true,
    ['water']=true,
    ['coal']=true
}
global.initial_score = {}

-- Check if a player's inventory is empty
local function check_player_inventory_empty(player)
    local inventory = player.get_main_inventory()
    return inventory.is_empty()
end

global.utils.get_direction = function(from_position, to_position)
    local dx = to_position.x - from_position.x
    local dy = to_position.y - from_position.y
    local adx = math.abs(dx)
    local ady = math.abs(dy)
    local diagonal_threshold = 0.5

    if adx > ady then
        if dx > 0 then
            return (ady / adx > diagonal_threshold) and (dy > 0 and 3 or 1) or 2
        else
            return (ady / adx > diagonal_threshold) and (dy > 0 and 5 or 7) or 6
        end
    else
        if dy > 0 then
            return (adx / ady > diagonal_threshold) and (dx > 0 and 3 or 5) or 4
        else
            return (adx / ady > diagonal_threshold) and (dx > 0 and 1 or 7) or 0
        end
    end
end

global.utils.get_direction_with_diagonals = function(from_pos, to_pos)
    local dx = to_pos.x - from_pos.x
    local dy = to_pos.y - from_pos.y

    if dx == 0 and dy == 0 then
        return nil
    end

    -- Check for cardinal directions first
    local cardinal_margin = 0.20 --0.25
    if math.abs(dx) < cardinal_margin then
        return dy > 0 and defines.direction.south or defines.direction.north
    elseif math.abs(dy) < cardinal_margin then
        return dx > 0 and defines.direction.east or defines.direction.west
    end

    -- Handle diagonal directions
    if dx > 0 then
        return dy > 0 and defines.direction.southeast or defines.direction.northeast
    else
        return dy > 0 and defines.direction.southwest or defines.direction.northwest
    end
end


global.utils.get_closest_entity = function(player, position)
    local closest_distance = math.huge
    local closest_entity = nil
    local entities = player.surface.find_entities_filtered{
        position = position,
        force = "player",
        radius = 3
    }

    for _, entity in ipairs(entities) do
        if entity.name ~= 'character' and entity.name ~= 'laser-beam' then
            local distance = ((position.x - entity.position.x) ^ 2 + (position.y - entity.position.y) ^ 2) ^ 0.5
            if distance < closest_distance then
                closest_distance = distance
                closest_entity = entity
            end
        end
    end

    return closest_entity
end

global.utils.is_position_blocked = function(player, position)
    rendering.draw_circle{only_in_alt_mode=true, width = 0.5, color = {r = 1, g = 0, b = 1}, surface = player.surface, radius = 0.5, filled = false, target = position, time_to_live = 60000}

    local can_place = player.surface.can_place_entity{
        name = "simple-entity-with-owner",
        position = position,
    }
    return not can_place
end


global.utils.calculate_movement_ticks = function(player, from_pos, to_pos)
    -- Calculate distance between points
    local dx = to_pos.x - from_pos.x
    local dy = to_pos.y - from_pos.y
    local distance = math.sqrt(dx * dx + dy * dy)

    -- Get player's walking speed (tiles per tick)
    -- Character base speed is 0.15 tiles/tick
    local walking_speed = player.character_running_speed
    if not walking_speed or walking_speed == 0 then
        walking_speed = 0.15  -- Default walking speed
    end

    -- Calculate ticks needed for movement
    return math.ceil(distance / walking_speed)
end

-- Wrapper around LuaSurface.can_place_entity that replicates all checks LuaPlayer.can_place_entity performs.
-- This allows our code to validate placement without relying on an actual LuaPlayer instance.
-- extra_params can be provided by callers to pass additional flags (e.g. fast_replace) if needed.
global.utils.can_place_entity = function(player, entity_name, position, direction, extra_params)
    local params = extra_params or {}
    params.name = entity_name
    params.position = position
    params.direction = direction
    params.force = player.force
    -- Use the manual build-check path so the engine applies the same rules as when a human player builds.
    params.build_check_type = defines.build_check_type.manual
    return player.surface.can_place_entity(params)
end

global.actions.can_reach = function(player, x, y)
    local dx = player.position.x - x
    local dy = player.position.y - y
    local distance = math.sqrt(dx * dx + dy * dy)

    if distance > player.reach_distance then
        return false
    end
    return true
end

global.utils.get_placement_issues = function(player, entity_name, position, direction)
    local reasons = {}

    -- Check if entity prototype exists
    local prototype = game.entity_prototypes[entity_name]
    if not prototype then
        table.insert(reasons, "invalid entity name " .. entity_name)
        return reasons
    end

    -- Check if player has required technology
    if not player.force.recipes[entity_name] then
        table.insert(reasons, "required technology not researched")
    end

    -- Get rotated collision box
    local collision_box = prototype.collision_box
    local box_width = collision_box.right_bottom.x - collision_box.left_top.x
    local box_height = collision_box.right_bottom.y - collision_box.left_top.y

    local rotated_box
    if direction and (direction == defines.direction.east or direction == defines.direction.west) then
        -- Swap width and height for east/west orientations
        rotated_box = {
            left_top = {x = position.x - box_height/2, y = position.y - box_width/2},
            right_bottom = {x = position.x + box_height/2, y = position.y + box_width/2}
        }
    else
        rotated_box = {
            left_top = {x = position.x - box_width/2, y = position.y - box_height/2},
            right_bottom = {x = position.x + box_width/2, y = position.y + box_height/2}
        }
    end

    -- Check for collisions with existing entities using rotated box
    local entities = player.surface.find_entities_filtered{area = rotated_box}
    if #entities > 0 then
        local colliding = {}
        for _, entity in pairs(entities) do
            if entity.valid and entity.name ~= 'character' then
                local entity_prototype = game.entity_prototypes[entity.name]
                if entity_prototype and entity_prototype.collision_mask and prototype.collision_mask then
                    -- Check if collision masks overlap
                    for mask_type in pairs(prototype.collision_mask) do
                        if entity_prototype.collision_mask[mask_type] then
                            table.insert(colliding, entity.name)
                            break
                        end
                    end
                end
            end
        end
        if #colliding > 0 then
            table.insert(reasons, "colliding with " .. table.concat(colliding, ", "))
        end
    end

    -- Check all tiles in the rotated area for collision and water
    local left = math.floor(rotated_box.left_top.x)
    local right = math.ceil(rotated_box.right_bottom.x)
    local top = math.floor(rotated_box.left_top.y)
    local bottom = math.ceil(rotated_box.right_bottom.y)

    local water_tiles = 0
    local total_tiles = 0
    local problematic_tiles = {}

    for x = left, right do
        for y = top, bottom do
            local tile = player.surface.get_tile(x, y)
            if tile then
                total_tiles = total_tiles + 1

                -- Water checks
                if tile.prototype.collision_mask["water-tile"] then
                    water_tiles = water_tiles + 1
                end

                -- General tile collision check
                if prototype.collision_mask then
                    for mask_type in pairs(prototype.collision_mask) do
                        if mask_type ~= "water-tile" and tile.prototype.collision_mask[mask_type] then
                            if not problematic_tiles[tile.name] then
                                problematic_tiles[tile.name] = true
                            end
                            break
                        end
                    end
                end
            end
        end
    end

    -- Water placement logic
    if not prototype.collision_mask["water-tile"] and water_tiles == 0 then
        table.insert(reasons, "must be placed on water")
    elseif prototype.collision_mask["water-tile"] and water_tiles > 0 then
        table.insert(reasons, "cannot build on water")
    end

    -- Add problematic tiles to reasons
    for tile_name, _ in pairs(problematic_tiles) do
        table.insert(reasons, "cannot build on " .. tile_name)
    end

    -- Check if outside map bounds
    local map_bounds = {{-1000000, -1000000}, {1000000, 1000000}} -- Adjust as needed
    if rotated_box.left_top.x < map_bounds[1][1] or rotated_box.right_bottom.x > map_bounds[2][1] or
            rotated_box.left_top.y < map_bounds[1][2] or rotated_box.right_bottom.y > map_bounds[2][2] then
        table.insert(reasons, "position outside map bounds")
    end

    -- Check if player has required items in inventory
    if prototype.items_to_place_this then
        for _, stack in ipairs(prototype.items_to_place_this) do
            local count = stack.count or 1
            local inventory_count = player.get_item_count(stack.name)
            if inventory_count < count then
                table.insert(reasons, string.format("missing %d %s", count - inventory_count, stack.name))
            end
        end
    end

    return reasons
end

global.utils.describe_placement_issues = function(player, entity_name, position, direction)
    local issues = global.utils.get_placement_issues(player, entity_name, position, direction)
    if #issues > 0 then
        return "Cannot build because: " .. table.concat(issues, "; ")
    end
    return ""
end

global.utils.avoid_entity = function(player_index, entity, position, direction)
    local player = global.agent_characters[player_index]
    local player_position = player.position
    for i=0, 10 do
        local can_place = player.surface.can_place_entity{
            name = entity,
            force = "player",
            position = position,
            direction = global.utils.get_entity_direction(entity, direction)
        }
        if can_place then
            return true
        end
        player.teleport({player_position.x + i, player_position.y + i})
    end
    player.teleport(player_position)
    return false
end



---- Define a function to be called every tick
--local function on_tick(event)
--    -- Run the check every 60 ticks (1 second)
--    if event.tick % 60 == 0 then
--        for _, player in pairs(game.connected_players) do
--            if check_player_inventory_empty(player) then
--                -- Perform an action or notify the player when their inventory is empty
--                player.print("Your inventory is empty!")
--            end
--        end
--    end
--end
--
---- Register the on_tick function to the on_tick event
--script.on_event(defines.events.on_tick, on_tick)

--script.on_nth_tick(3600, function(event)
--    game.take_screenshot{
--        surface=game.surfaces[1],
--        position={0,0},
--        resolution={2560, 1600},
--        zoom=0.2,
--        path="timelapse/" .. string.format("%06d", event.tick/event.nth_tick) .. ".jpg",
--        show_entity_info=true,
--        allow_in_replay=true,
--        daytime=1
--    }
--end)


for _, ent in pairs(surface.find_entities_filtered({force="player", position=pp, radius=50})) do
    if ent.name ~= "character" then
        ent.destroy()
    end
end

for key, entity in pairs(surface.find_entities_filtered({force="enemy", radius=250, position=pp })) do
	cnt = cnt+1
	entity.destroy()
 end

global.crafting_queue = {}

script.on_event(defines.events.on_tick, function(event)
  -- Iterate over the crafting queue and update the remaining ticks
  for i, task in ipairs(global.crafting_queue) do
    task.remaining_ticks = task.remaining_ticks - 1

    -- If the crafting is finished, consume the ingredients, insert the crafted entity, and remove the task from the queue
    if task.remaining_ticks <= 0 then
      for _, ingredient in pairs(task.recipe.ingredients) do
        task.player.remove_item({name = ingredient.name, count = ingredient.amount * task.count})
      end
      task.player.insert({name = task.entity_name, count = task.count})
      table.remove(global.crafting_queue, i)
    end
  end
end)

function abort(message)
    local msg = tostring(message):gsub(" ", "_")
    rcon.print(msg)
end

function create_beam_bounding_box (player, surface, direction, top_left, bottom_right)
    local bottom_left = {x=top_left.x, y=bottom_right.y}
    local top_right = {x=bottom_right.x, y=top_left.y}
    local direction = 0
    surface.create_entity{name='laser-beam', position=player.position, source_position=top_left, target_position=top_right, duration=beam_duration, direction=direction, force='neutral', player=player}
    surface.create_entity{name='laser-beam', position=player.position, source_position=top_right, target_position=bottom_right, duration=beam_duration, direction=direction, force='neutral', player=player}
    surface.create_entity{name='laser-beam', position=player.position, source_position=bottom_right, target_position=bottom_left, duration=beam_duration,  direction=direction, force='neutral', player=player}
    surface.create_entity{name='laser-beam', position=player.position, source_position=bottom_left, target_position=top_left, duration=beam_duration,  direction=direction, force='neutral', player=player}
    surface.create_entity{name='laser-beam', position=player.position, source_position=player.position, duration=beam_duration, target_position={x=player.position.x, y=player.position.y+0.1}, direction=direction, force='neutral', player=player}
end

function create_arrow_with_direction(player, direction, position)
    local beam_length = 0.75
    local arrow_width = 0.5

    -- Calculate the end position of the main beam
    local end_position = {x = position.x, y = position.y}
    local dx, dy = 0, 0

    if direction == 0 then  -- North
        dy = -beam_length
    elseif direction == 2 then  -- East
        dx = beam_length
    elseif direction == 4 then  -- South
        dy = beam_length
    elseif direction == 6 then  -- West
        dx = -beam_length
    elseif direction == 1 then  -- Northeast
        dx, dy = beam_length * 0.7071, -beam_length * 0.7071
    elseif direction == 3 then  -- Southeast
        dx, dy = beam_length * 0.7071, beam_length * 0.7071
    elseif direction == 5 then  -- Southwest
        dx, dy = -beam_length * 0.7071, beam_length * 0.7071
    elseif direction == 7 then  -- Northwest
        dx, dy = -beam_length * 0.7071, -beam_length * 0.7071
    end

    end_position.x = position.x + dx
    end_position.y = position.y + dy

    -- Create the main beam
    player.surface.create_entity{
        name = 'laser-beam',
        position = position,
        source_position = position,
        target_position = end_position,
        duration = 6000,
        force = 'neutral',
        player = player
    }

    -- Calculate and create the two side beams for the arrowhead
    local perpendicular_dx = -dy * arrow_width
    local perpendicular_dy = dx * arrow_width

    local arrow_left = {
        x = end_position.x + perpendicular_dx - dx * 0.3,
        y = end_position.y + perpendicular_dy - dy * 0.3
    }
    local arrow_right = {
        x = end_position.x - perpendicular_dx - dx * 0.3,
        y = end_position.y - perpendicular_dy - dy * 0.3
    }

    player.surface.create_entity{
        name = 'laser-beam',
        position = end_position,
        source_position = end_position,
        target_position = arrow_left,
        duration = 100000,
        force = 'neutral',
        player = player
    }

    player.surface.create_entity{
        name = 'laser-beam',
        position = end_position,
        source_position = end_position,
        target_position = arrow_right,
        duration = 100000,
        force = 'neutral',
        player = player
    }
end

function create_beam_point_with_direction (player, direction, position)
    -- Calculate the end position of the beam based on the direction.
    local end_position = {x=position.x, y=position.y}
    local length = 0.5
    if direction == defines.direction.north then
        end_position.y = end_position.y - length
    elseif direction == defines.direction.south then
        end_position.y = end_position.y + length
    elseif direction == defines.direction.west then
        end_position.x = end_position.x - length
    elseif direction == defines.direction.east then
        end_position.x = end_position.x + length
    elseif direction == defines.direction.northeast then
        end_position.x = end_position.x + length
        end_position.y = end_position.y - length
    elseif direction == defines.direction.southeast then
        end_position.x = end_position.x + length
        end_position.y = end_position.y + length
    elseif direction == defines.direction.southwest then
        end_position.x = end_position.x - length
        end_position.y = end_position.y + length
    elseif direction == defines.direction.northwest then
        end_position.x = end_position.x - length
        end_position.y = end_position.y - length
    end

    -- Create the beam entity.
    player.surface.create_entity{
        name='laser-beam',
        position=position,
        source_position=position,
        target_position=end_position,
        duration=60000,
        direction=direction,
        force='neutral',
        player=player
    }
end
function create_beam_point (player, position)
    -- Create beams in all four cardinal directions.
    create_beam_point_with_direction(player, defines.direction.north, position)
    create_beam_point_with_direction(player, defines.direction.south, position)
    create_beam_point_with_direction(player, defines.direction.west, position)
    create_beam_point_with_direction(player, defines.direction.east, position)
end


function observe_points_of_interest (surface, player, search_radius)
    local enemy = surface.find_nearest_enemy{position=player.position, max_distance=search_radius}
    if enemy ~= nil then
        global.points_of_interest['enemy'] = enemy.position
    end

    for k, v in pairs(global.points_of_interest) do
        global.relative_points_of_interest[k] = {
            x=v.x-player.position.x,
            y=v.y-player.position.y
        }
    end

    rcon.print(1)
    return dump(global.relative_points_of_interest)
end

function find_passable_tiles(player, localBoundingBox)
    -- Generate a 100x100 bounding box centered on the player
    local origin = player.position
    local offset = localBoundingBox / 2

    local left = origin.x - offset
    local right = origin.x + offset
    local top = origin.y - offset
    local bottom = origin.y + offset

    local bounding_box = {
        left_top = {x = left, y = top},
        right_bottom = {x = right, y = bottom}
    }
    local impassable_tiles = {}
    for x = left, right do
        for y = top, bottom do
            local tile = player.surface.get_tile(x, y)
            local is_impassable = tile.prototype.collision_mask["player-layer"]

            if is_impassable then
                --(x - xmin) * localBoundingBox + (y - ymin)
                local relative_x, relative_y = x + offset, y + offset
                --local index = coords_to_index(relative_x, relative_y)
                local index = relative_y * localBoundingBox + relative_x
                if not impassable_tiles[index] then
                    impassable_tiles[index] = 100
                end
            end
        end
    end

    -- Find all entities within the bounding box
    local entities = player.surface.find_entities_filtered{area = {{left, top}, {right, bottom}}, force = player.force}

    for _, entity in ipairs(entities) do
        local collision_box = entity.prototype.collision_box
        local is_passable = (collision_box.left_top.x == 0 and collision_box.left_top.y == 0 and
                             collision_box.right_bottom.x == 0 and collision_box.right_bottom.y == 0)
        if not is_passable then -- Change this condition to check for impassable entities
            local x, y = math.floor(entity.position.x), math.floor(entity.position.y)
            local relative_x, relative_y = x - left, y - top
            local index = relative_y * localBoundingBox + relative_x

            if not impassable_tiles[index] then
                impassable_tiles[index] = 99--{x = relative_x, y = relative_y, entity = entity}
            end
        end
  end

    -- Convert the X, Y coordinates of each entity into coordinates relative to the origin
    local relative_entities = {}
    for _, entity in ipairs(entities) do
        table.insert(relative_entities, {x = left, y = top, entity = entity})
    end

    -- Create a 1D sparse index of the x, y coordinate and entity, starting from the top left of the bounding box
    local sparse_index = {}
    for _, relative_entity in ipairs(relative_entities) do
        -- Ensure the coordinates are integers by rounding them
        local index_x = math.floor(relative_entity.x + offset)
        local index_y = math.floor(relative_entity.y + offset)

        local index = index_y * localBoundingBox + index_x
        --impassable_tiles[index] = 99
    end

    rcon.print(1)
    return impassable_tiles
end

function get_locality(position, surface, localBoundingBox)
    local origin = position
    local offset = localBoundingBox / 2

    local left = origin.x - offset
    local right = origin.x + offset
    local top = origin.y - offset
    local bottom = origin.y + offset

    local bounding_box = {
        left_top = {x = left, y = top},
        right_bottom = {x = right, y = bottom}
    }

    local entities = surface.find_entities(bounding_box)

    local relative_entities = {}
    for _, entity in ipairs(entities) do
        local relative_x = entity.position.x - origin.x
        local relative_y = entity.position.y - origin.y
        table.insert(relative_entities, {x = relative_x, y = relative_y, entity = entity})
    end

    local sparse_index = {}
    for _, relative_entity in ipairs(relative_entities) do
        local index_x = math.floor(relative_entity.x + offset)
        local index_y = math.floor(relative_entity.y + offset)

        local index = index_y * localBoundingBox + index_x
        local name = relative_entity.entity.name
        sparse_index[index] = name:gsub("-", "_")
    end

    -- Find water tiles
    local water_tiles = surface.find_tiles_filtered{area=bounding_box, name={"water", "deepwater"}}
    for _, tile in ipairs(water_tiles) do
        local relative_x = tile.position.x - origin.x
        local relative_y = tile.position.y - origin.y

        local index_x = math.floor(relative_x + offset)
        local index_y = math.floor(relative_y + offset)

        local index = index_y * localBoundingBox + index_x
        local name = "water"
        sparse_index[index] = name:gsub("-", "_")
    end

    rcon.print(1)
    return sparse_index
end


function has_value(tbl, val)
    for _, value in ipairs(tbl) do
        if value == val then
            return true
        end
    end
    return false
end

function get_local_environment (position, surface, localBoundingBox, field_x, field_y, debug)

    local top = position.y-localBoundingBox/2
    local left = position.x-localBoundingBox/2
    local bottom = position.y+localBoundingBox/2
    local right = position.x+localBoundingBox/2

    if field_x > 0 then
        right = right + field_x
        left = right - field_x
    elseif field_x < 0 then
        left = left + field_x
        right = left - field_x
    end

    if field_y < 0 then
        top = top + field_y
        bottom = top-field_y
    elseif field_y > 0 then
        bottom = bottom + field_y
        top = bottom-field_y
    end

    bounding_box_top_left = {x=left, y=top}
    bounding_box_bottom_right = {x=right, y=bottom}

    if debug then
        create_beam_bounding_box(player, surface, direction, bounding_box_top_left, bounding_box_bottom_right)
        entities = surface.find_entities_filtered{name="laser-beam", invert=true, area={bounding_box_top_left, bounding_box_bottom_right}}
    else
        entities = surface.find_entities({bounding_box_top_left, bounding_box_bottom_right})
    end

    mt = {}          -- create the matrix
    for i,entity in pairs(entities) do

            local x_pos = left-entity.position.x
            local y_pos = top-entity.position.y
            local name = entity.name

            mt[math.floor(x_pos*(top-bottom) + y_pos)] = name:gsub("-", "_")
            set_points_of_interest(player, name, 1, x_pos, y_pos)

    end

    rcon.print(1)
    return mt
end

function observe_statistics (player)
    performance = {
        item = {
            input_counts=player.force.item_production_statistics.input_counts,
            output_counts=player.force.item_production_statistics.output_counts
        },
        fluid = {
            input_counts=player.force.fluid_production_statistics.input_counts,
            output_counts=player.force.fluid_production_statistics.output_counts
        },
        kills = {
            input_counts=player.force.kill_count_statistics.input_counts,
            output_counts=player.force.kill_count_statistics.output_counts
        },
        built = {
            input_counts=player.force.entity_build_count_statistics.input_counts,
            output_counts=player.force.entity_build_count_statistics.output_counts
        }
    }
    return performance
end

function clean_nils(t)
  local ans = {}
  for _,v in pairs(t) do
    ans[ #ans+1 ] = v
  end
  return ans
end

function observe_chunk(player, surface, chunk_x, chunk_y)
    counts = {}
    key = chunk_x .. ", " ..chunk_y

    chunk_area = {{chunk_x*32, chunk_y*32}, {(chunk_x+1)*32, (chunk_y+1)*32}}

    counts['all'] = surface.count_entities_filtered{area=chunk_area}

    -- Environment
    counts['trees'] = surface.count_entities_filtered{area=chunk_area, type = "tree"}
    counts['water'] = surface.count_tiles_filtered{area=chunk_area, name = 'water'}
    counts['pollution'] = surface.get_pollution({chunk_x*32,chunk_y*32})

    -- Forces
    counts['factory'] = surface.count_entities_filtered{area=chunk_area, force = "player"}
    counts['enemy'] = surface.count_entities_filtered{area=chunk_area, force = "enemy"}

    -- Resources
    counts['iron-ore'] = surface.count_entities_filtered{area=chunk_area, name = "iron-ore"}
    counts['coal'] = surface.count_entities_filtered{area=chunk_area, name = "coal"}
    counts['copper-ore'] = surface.count_entities_filtered{area=chunk_area, name = "copper-ore"}
    counts['uranium-ore'] = surface.count_entities_filtered{area=chunk_area, name = "uranium-ore"}
    counts['stone'] = surface.count_entities_filtered{area=chunk_area, name = "stone"}
    counts['crude-oil'] = surface.count_entities_filtered{area=chunk_area, name = "crude-oil"}

    for field_name, count in pairs(counts) do
        --if count ~= 0 then
        set_points_of_interest(player, field_name, count, chunk_x, chunk_y)
        --else
            --table.remove(counts, field_name)
        --end
    end

    rcon.print(1)
    return counts
end

function observe_buildable (player, inventory)
    local recipes = {}
    for field_name, recipe in pairs(player.force.recipes) do
        local name = field_name:gsub("-", "_")
        local can_build = 0
        for i, ingredient in pairs(recipe.ingredients) do
            if inventory[ingredient.name] ~= nil then
                local max_build = inventory[ingredient.name] / ingredient.amount
                can_build = math.floor(max_build)
            else
                can_build = 0
                break
            end
        end
        if can_build ~= 0 then
            recipes[name] = can_build
        end
    end
    return serpent.line(recipes)
end

function dump(o)
   if type(o) == 'table' then
      local s = '{ '
      for k,v in pairs(o) do
         if type(k) ~= 'number' then k = '"'..k..'"' end
         s = s .. '['..k..'] = ' .. dump(v) .. ','
      end
      return s .. '} '
   else
      return tostring(o)
   end
end

function set_points_of_interest (player, field, count, chunk_x, chunk_y)
    if count > 0 and global.interesting_entities[field] then
        x_distance = (chunk_x*32 - player.position.x) * (chunk_x*32 - player.position.x)
        y_distance = (chunk_y*32 - player.position.y) * (chunk_y*32 - player.position.y)
        distance_square = x_distance + y_distance

        if global.distances_to_nearest[field] == nil then
            global.distances_to_nearest[field] = 100000
        end

        if global.distances_to_nearest[field] > distance_square then
            global.distances_to_nearest[field] = math.sqrt(distance_square) --only compute expensive sqrt when necessary
            global.points_of_interest[field] = {x=chunk_x*32, y=chunk_y*32}
        end
    end
end

-- Define a function to calculate the raw material value of an item
function raw_material_value(item_name)
    local values = {
        ["iron-ore"] = 1,
        ["copper-ore"] = 1,
        ["coal"] = 1,
        ["stone"] = 1,
        ["crude-oil"] = 1
    }
    -- Add more items and their raw material values here if needed

    return values[item_name] or 0
end

function get_productivity(player)
    local force = player.force
    local production_statistics = force.item_production_statistics

    -- Calculate production rates
    local production_rates = {}
    for _, prototype in pairs(game.item_prototypes) do
        local name = prototype.name
        local count = production_statistics.get_flow_count{name = name, input = true, precision_index = 5, count = true}
        if count > 0 then
            production_rates[name] = count
        end
    end

    -- Calculate consumption rates
    local consumption_rates = {}
    for _, prototype in pairs(game.item_prototypes) do
        local name = prototype.name
        local count = production_statistics.get_flow_count{name = name, input = false, precision_index = 5, count = true}
        if count > 0 then
            consumption_rates[name] = count
        end
    end

    -- Use the raw_material_value function to calculate the total value created
    local total_production_value = 0
    local total_consumption_value = 0

    for name, rate in pairs(production_rates) do
        local value = raw_material_value(name) * rate
        total_production_value = total_production_value + value
    end

    for name, rate in pairs(consumption_rates) do
        local value = raw_material_value(name) * rate
        total_consumption_value = total_consumption_value + value
    end

    local net_value_created = total_production_value - total_consumption_value


    return {
        production=production_rates,
        consumption=consumption_rates
    }
end

function craft_entity(player, entity_name, count)
      -- Ensure the player and entity_name are valid
    if not player or not player.valid or not entity_name then
        return "Entity not valid"
    end

  -- Get the recipe for the entity
  local recipe = player.force.recipes[entity_name]
  if not recipe then
      return "Recipe doesnt exist"
  end

  -- Check if the entity can be crafted by hand
  if recipe.category ~= "crafting" then
      return "It requires " .. entity_name:gsub("-", "_") .. " which cannot be crafted by hand"
  end


  -- Check if the player has enough items to craft the entity
  for _, ingredient in pairs(recipe.ingredients) do
      local has_count = player.get_item_count(ingredient.name)
      local need_count = ingredient.amount * count
      if has_count < need_count then
        return "Insufficient "..ingredient.name:gsub('-',"_"):gsub(' ',"_").." "..(need_count-has_count).." needed"
      end
  end

  -- Craft the entity, consuming the ingredients
  for _, ingredient in pairs(recipe.ingredients) do
    player.remove_item({name = ingredient.name, count = ingredient.amount * count})
  end

  -- Insert the crafted entity into the player's inventory
  player.insert({name = entity_name, count = count})

  return 1
end

function get_missing_ingredients(player, recipe, count, checked_recipes)
  local missing_ingredients = {}
  checked_recipes = checked_recipes or {}
  for _, ingredient in pairs(recipe.ingredients) do
    if game.item_prototypes[ingredient.name] then
      local count_that_player_has = player.get_item_count(ingredient.name)
      local needed = ingredient.amount * count
      if count_that_player_has < needed then
        local difference = needed - count_that_player_has


        -- Check if the ingredient can be crafted
        local ingredient_recipe = player.force.recipes[ingredient.name]
        if ingredient_recipe and not checked_recipes[ingredient.name] then
          checked_recipes[ingredient.name] = true
          local sub_missing_ingredients = get_missing_ingredients(player, ingredient_recipe, difference, checked_recipes)
          for sub_ingredient_name, sub_count in pairs(sub_missing_ingredients) do
            if missing_ingredients[sub_ingredient_name] then
              missing_ingredients[sub_ingredient_name] = missing_ingredients[sub_ingredient_name] + sub_count
            else
              missing_ingredients[sub_ingredient_name] = sub_count
            end
          end
            if sub_missing_ingredients ~= nil then
               missing_ingredients[ingredient.name] = difference
            end
        end
      end
    else
      if game.fluid_prototypes[ingredient.name] then
        abort("Crafting requires fluid ingredient " .. ingredient.name)
      else
        abort("Unknown ingredient " .. ingredient.name)
      end
    end
  end
  return missing_ingredients
end

function recursively_craft_missing_ingredients(player, missing_ingredients)
  local uncraftable_ingredients = {}
  for ingredient_name, count in pairs(missing_ingredients) do
    local success = craft_entity(player, ingredient_name, count)
    if not success then
      local recipe = player.force.recipes[ingredient_name]
      if recipe then
        local sub_missing_ingredients = get_missing_ingredients(player, recipe, count)
        recursively_craft_missing_ingredients(player, sub_missing_ingredients)
      else
        uncraftable_ingredients[ingredient_name] = count
      end
    end
  end
  return uncraftable_ingredients
end

function add_to_crafting_queue(player, entity_name, count)
    -- Ensure the player and entity_name are valid
    if not player or not player.valid or not entity_name then
        return "not_valid_entity"
    end

    -- Get the recipe for the entity
    local recipe = player.force.recipes[entity_name]
    if not recipe then
        return "no_valid_recipe"
    end

    -- Check if the player has enough items to craft the entity
    local missing_ingredients = get_missing_ingredients(player, recipe, count)
    if next(missing_ingredients) == nil then
        -- Craft the requested entity
        return craft_entity(player, entity_name, count)
    else
        local uncraftable_ingredients = recursively_craft_missing_ingredients(player, missing_ingredients)

        if next(uncraftable_ingredients) ~= nil then
            local uncraftable_message = "Cannot craft the following missing ingredients "
            for ingredient_name, count in pairs(uncraftable_ingredients) do
                uncraftable_message = uncraftable_message .. count .. "x " .. ingredient_name .. "___"
            end
            return uncraftable_message:sub(1, -3)

        else
            -- Craft the requested entity
            return craft_entity(player, entity_name, count)
        end

    end
end

function inspect(player, radius, position)
    local surface = player.surface
    local bounding_box = {
        left_top = {x = position.x - radius, y = position.y - radius},
        right_bottom = {x = position.x + radius, y = position.y + radius}
    }

    local entities = surface.find_entities_filtered({bounding_box, force = "player"})
    local entity_data = {}

    for _, entity in ipairs(entities) do
        if entity.name ~= 'character' then
            local data = {
                name = entity.name:gsub("-", "_"),
                position = entity.position,
                direction = entity.direction,--directions[entity.direction+1],
                health = entity.health,
                force = entity.force.name,
                energy = entity.energy,
                status = entity.status,
                --crafted_items = entity.crafted_items or nil
            }

            -- Get entity contents if it has an inventory
            if entity.get_inventory(defines.inventory.chest) then
                local inventory = entity.get_inventory(defines.inventory.chest).get_contents()
                data.contents = inventory
            end

            data.warnings = get_issues(entity)

            -- Get entity orientation if it has an orientation attribute
            if entity.type == "train-stop" or entity.type == "car" or entity.type == "locomotive" then
                data.orientation = entity.orientation
            end

            -- Get connected entities for pipes and transport belts
            if entity.type == "pipe" or entity.type == "transport-belt" then
                local path_ends = find_path_ends(entity)
                data.path_ends = {}
                for _, path_end in pairs(path_ends) do
                    local path_position = {x=path_end.position.x - player.position.x, y=path_end.position.y - player.position.y}
                    table.insert(data.path_ends, {name = path_end.name:gsub("-", "_"), position = path_position, unit_number = path_end.unit_number})
                end
            end

            table.insert(entity_data, data)
        else
            local data = {
                name = "player_character",
                position = entity.position,
                direction = directions[entity.direction+1],
            }
            table.insert(entity_data, data)
        end
    end

    -- Sort entities with path_ends by the length of path_ends in descending order
    table.sort(entity_data, function(a, b)
        if a.path_ends and b.path_ends then
            return #a.path_ends > #b.path_ends
        elseif a.path_ends then
            return true
        else
            return false
        end
    end)

    -- Remove entities that exist in the path_ends of other entities
    local visited_paths = {}
    local filtered_entity_data = {}
    for _, data in ipairs(entity_data) do
        if data.path_ends then
            local should_add = true
            for _, path_end in ipairs(data.path_ends) do
                if visited_paths[path_end.unit_number] then
                    should_add = false
                    break
                end
            end
            if should_add then
                for _, path_end in ipairs(data.path_ends) do
                    visited_paths[path_end.unit_number] = true
                end
                table.insert(filtered_entity_data, data)
            else
                data.path_ends = nil
                --table.insert(filtered_entity_data, data)
            end
        else
            table.insert(filtered_entity_data, data)
        end
    end
    entity_data = filtered_entity_data

    return entity_data
end

function required_resource_present(entity, position, surface)
    local prototype = game.entity_prototypes[entity]
    local entity_type = prototype.type

    if entity_type == "mining-drill" then
        local resources = surface.find_entities_filtered{position=position, type="resource"}
        for _, resource in ipairs(resources) do
            if resource.prototype.mineable_properties.minable then
                return true, nil
            end
        end
        return false, "minable resource"

    elseif entity_type == "offshore-pump" then
        local tile = surface.get_tile(position)
        if tile.prototype.name == "water" or tile.prototype.name == "deepwater" then
            return true, nil
        end
        return false, "water"

    else
        return true, nil
    end
end

rcon.print(1)