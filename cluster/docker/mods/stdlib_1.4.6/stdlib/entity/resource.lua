--- Resource utilities.
-- @module Entity.Resource
-- @usage local Resource = require('__stdlib__/stdlib/entity/resource')

local Resource = {__class = 'Resource',
__index = require('__stdlib__/stdlib/core')}
setmetatable(Resource, Resource)

local Is = require('__stdlib__/stdlib/utils/is')

local Surface = require('__stdlib__/stdlib/area/surface')
local Area = require('__stdlib__/stdlib/area/area')
local Tile = require('__stdlib__/stdlib/area/tile')
local Queue = require('__stdlib__/stdlib/misc/queue')
local table = require('__stdlib__/stdlib/utils/table')

--- Gets all resource entities at the specified position and surface.
-- Adapted from *YARM/resmon.lua &rarr; find\_resource\_at*
-- @tparam string|LuaSurface surface the surface to look up
-- @tparam Concepts.Position position the position to check
-- @treturn {nil|LuaEntity,...} an array of resource entities or nil if none found
function Resource.get_resources_at(surface, position)
    Is.Assert(surface, 'missing surface')
    Is.Assert(position, 'missing position')
    local surfaces = Surface.lookup(surface)
    Is.Assert(#surfaces == 1, 'invalid surface')

    local tile_at_position = Tile.from_position(Tile(position))
    local tile_area = Tile.to_area(tile_at_position)

    local resources_at_tile = table.first(surfaces).find_entities_filtered {area = tile_area, type = 'resource'} or {}

    return resources_at_tile
end

--- From the resources at the given surface and position, return all connected (horizontally, vertically and diagonally) resource entities.
-- <p>When the resource patches are found, the returned object will be an associative array where the key is the
-- resource-type string and the value is an array of entities that correspond to the resource-type.
-- <p>For now, this function gets just the ore patches, since problems arise when a single resource entity spans multiple tiles.
--> This implementation is unstable; if a resource entity reference changes during the search, *both the old and the new version* of the entity might be included.
-- @tparam LuaSurface surface the surface to look up
-- @tparam Concepts.Position position the position to check
-- @return (<span class="types">{@{nil}} or {[@{string} &lt;resource-type&gt;] = {@{LuaEntity},...},...}</span>) a map of resource types to resource entities or empty array if they don't exist
function Resource.get_resource_patches_at(surface, position)
    Is.Assert(surface, 'missing surface')
    Is.Assert(position, 'missing position')

    -- get the initial resource tile if there is one at the given position
    local all_resource_entities = Resource.get_resources_at(surface, position)
    local all_resource_types = Resource.get_resource_types(all_resource_entities)
    local resource_patches = {}

    for _, type in pairs(all_resource_types) do
        local resource_patch = Resource.get_resource_patch_at(surface, position, type)
        resource_patches[type] = resource_patch
    end

    return resource_patches
end

--- From the resources at the given surface and position, return all connected (horizontally, vertically and diagonally) resource entities of specified type.
-- <p>For now, this function gets just the ore patches, since problems arise when a single resource entity spans multiple tiles.
--> This implementation is unstable; if a resource entity reference changes during the search, *both the old and the new version* of the entity might be included.
-- @tparam LuaSurface surface the surface to look up
-- @tparam Concepts.Position position the position to check
-- @tparam string type the resource type (example: "iron-ore")
-- @treturn {nil|LuaEntity,...} an array containing all resources in the resource patch, or an empty array if there are no resources there
function Resource.get_resource_patch_at(surface, position, type)
    Is.Assert(surface, 'missing surface')
    Is.Assert(position, 'missing position')
    Is.Assert(position, 'missing ore name')
    local surfaces = Surface.lookup(surface)
    Is.Assert(#surfaces == 1, 'invalid surface')

    surface = table.first(surfaces)

    -- get the initial resource tile if there is one at the given position
    local all_resource_entities = Resource.get_resources_at(surface, position)
    local filtered_resource_entities = Resource.filter_resources(all_resource_entities, {type})

    if #filtered_resource_entities == 0 then
        return {}
    end

    -- for the search, keep track of the relevant entities and tiles visited
    -- we use the entities as keys to prevent having a single entity multiple times in the list
    local resource_patch = {}
    local visited_tiles = {}

    -- local cache of bitwise functions, because they are called in a tight loop
    local bitwise_or = bit32.bor
    local bitwise_and = bit32.band
    local bitwise_lshift = bit32.lshift

    local initial_tile = Tile.from_position(Tile(filtered_resource_entities[1].position))

    -- do a BFS starting from the initial tile
    local search_queue = Queue.new()
    Queue.push_last(search_queue, initial_tile)

    while not Queue.is_empty(search_queue) do
        local current_tile = Queue.pop_first(search_queue)
        local current_entities = surface.find_entities_filtered {area = Tile.to_area(current_tile), type = 'resource'}
        local current_tile_index = bitwise_or(bitwise_lshift(bitwise_and(current_tile.x, 0xFFFF), 16), bitwise_and(current_tile.y, 0xFFFF))
        visited_tiles[current_tile_index] = true

        local filtered_current_entities = Resource.filter_resources(current_entities, {type})

        if #filtered_current_entities ~= 0 then
            -- this tile belongs to the ore patch, add the resources
            table.merge(resource_patch, table.invert(filtered_current_entities))

            -- queue all tiles around this one that we did not visit yet
            for _, adjacent_tile in pairs(Tile.adjacent(surface, current_tile, true)) do
                local adj_tile_index = bitwise_or(bitwise_lshift(bitwise_and(adjacent_tile.x, 0xFFFF), 16), bitwise_and(adjacent_tile.y, 0xFFFF))

                if not visited_tiles[adj_tile_index] then
                    Queue.push_last(search_queue, adjacent_tile)
                    visited_tiles[adj_tile_index] = true
                end
            end
        end
    end

    -- map the resource entities back to an array
    resource_patch = table.keys(resource_patch)

    return resource_patch
end

--- Given an array of resource entities, get an array containing their names.
-- Every element within the new array is unique and is the name of a resource entity.
-- @tparam {LuaEntity,...} resources an array of resource entities
-- @treturn {nil|string,...} a new array with the names of the resources or nil if no resource entities are given
function Resource.get_resource_types(resources)
    local result = {}

    if resources then
        local resource_names = {}

        for _, resource in pairs(resources) do
            resource_names[resource.name] = true
        end

        result = table.keys(resource_names, false, true)
    end

    return result
end

--- Given an array of resource entities, return the ones that have the given resource names.
-- @tparam {LuaEntity,...} resources an array of resource entities
-- @tparam {string,...} resource_names the names of the resource entities
-- @treturn {nil|LuaEntity,...} a new array containing the entities matching the given resource names or nil if no matches were found
function Resource.filter_resources(resources, resource_names)
    Is.Assert(resources, 'missing resource entities list')

    if not resource_names or #resource_names == 0 then
        return resources
    end

    -- filter the resources that have the same name as one of the given names in resource_names
    local result =
        table.filter(
        resources,
        function(resource_entity)
            return table.any(
                resource_names,
                function(name)
                    return resource_entity.name == name
                end
            )
        end
    )

    return result
end

--- Given a resource patch, return its area.
-- @see Resource.get_resource_patch_at
-- @tparam {LuaEntity,...} resource_patch the resource patch
-- @treturn Concepts.BoundingBox the area of the resource patch
function Resource.get_resource_patch_bounds(resource_patch)
    Is.Assert(resource_patch, 'missing resource patch')
    local min_x = math.huge
    local min_y = math.huge
    local max_x = -math.huge
    local max_y = -math.huge

    for _, entity in pairs(resource_patch) do
        local pos = entity.position
        min_x = math.min(min_x, pos.x)
        min_y = math.min(min_y, pos.y)
        max_x = math.max(max_x, pos.x)
        max_y = math.max(max_y, pos.y)
    end

    return Area.construct(min_x, min_y, max_x, max_y)
end

return Resource
