--- For working with surfaces.
-- Surfaces are the "domain" of the world.
-- @module Area.Surface
-- @usage local Surface = require('__stdlib__/stdlib/area/surface')
-- @see LuaSurface

local Surface = {
    __class = 'Surface',
    __index = require('__stdlib__/stdlib/core')
}
setmetatable(Surface, Surface)

local Is = require('__stdlib__/stdlib/utils/is')
local Area = require('__stdlib__/stdlib/area/area')

--- Flexible and safe lookup function for surfaces.
-- <ul>
-- <li>May be given a single surface name or an array of surface names in @{string}.
-- <li>May be given a single surface object or an array of surface objects in @{LuaSurface}.
-- <li>May also be given a @{nil}.
-- <li>Returns an array of surface objects of all valid and existing surfaces.
-- <li>Returns an empty array if no surfaces are given or if they are not found.
-- </ul>
-- @tparam ?|nil|string|{string,...}|LuaSurface|{LuaSurface,...} surface the surfaces to look up
-- @treturn {nil|LuaSurface,...} an array of all valid surfaces or nil otherwise
function Surface.lookup(surface)
    if not surface then
        return {}
    end
    if type(surface) == 'string' or type(surface) == 'number' then
        local lookup = game.surfaces[surface]
        if lookup then
            return {lookup}
        end
        return {}
    end
    if type(surface) == 'table' and surface['__self'] then
        return Surface.lookup(surface.name)
    end
    local results = {}
    for _, surface_item in pairs(surface) do
        if type(surface_item) == 'string' then
            if game.surfaces[surface_item] then
                table.insert(results, game.surfaces[surface_item])
            end
        elseif type(surface_item) == 'table' and surface_item['__self'] then
            table.insert(results, surface_item)
        end
    end
    return results
end

--- Given a @{search_criteria|search criteria}, find all entities that match the criteria.
-- <ul>
-- <li>If ***search\_criteria.name*** is not supplied, search for entities with any name.
-- <li>If ***search\_criteria.type*** is not supplied, search for entities of any type.
-- <li>If ***search\_criteria.force*** is not supplied, search for entities owned by any force.
-- <li>If ***search\_criteria.surface*** is not supplied, search for entities on all surfaces.
-- <li>If ***search\_criteria.area*** is not supplied, search the entire specified surface.
-- </ul>
-- @usage
-- surface.find_all_entities({ type = 'unit', surface = 'nauvis', area = {{-1000,20},{-153,2214}})
-- -- returns a list containing all unit entities on the nauvis surface in the given area
-- @param search_criteria (<span class="types">@{search_criteria}</span>) a table used to search for entities
-- @treturn {nil|LuaEntity,...} an array of all entities that matched the criteria **OR** *nil* if there were no matches
function Surface.find_all_entities(search_criteria)
    Is.Assert.Table(search_criteria, 'missing search_criteria argument')
    if search_criteria.name == nil and search_criteria.type == nil and search_criteria.force == nil and search_criteria.area == nil then
        error('Missing search criteria field: name or type or force or area of entity', 2)
    end

    local surface_list = Surface.lookup(search_criteria.surface)
    if search_criteria.surface == nil then
        surface_list = game.surfaces
    end

    local results = {}

    for _, surface in pairs(surface_list) do
        local entities =
            surface.find_entities_filtered(
            {
                area = search_criteria.area,
                name = search_criteria.name,
                type = search_criteria.type,
                force = search_criteria.force
            }
        )
        for _, entity in pairs(entities) do
            table.insert(results, entity)
        end
    end

    return results
end

---
-- This table should be passed into @{find_all_entities} function to find entities that match the criteria.
-- @tfield[opt] string name internal name of an entity &mdash; (example: "locomotive")
-- @tfield[opt] string type type of an entity &mdash; (example: "unit")
-- @tfield[opt] string|LuaForce force the force of an entity &mdash; (examples: "neutral", "enemy")
-- @tfield[opt] ?|nil|string|{string,...}|LuaSurface|{LuaSurface,...} surface the surface to search &mdash; (example: "nauvis")
-- @tfield[opt] Concepts.BoundingBox area the area to search
-- @table search_criteria

--- Gets the area which covers the entirety of a given surface.
-- This function is useful if you wish to compare the total number of chunks against the number of chunks within the entire area of a given surface.
-- @tparam LuaSurface surface the surface for which to get the area
-- @treturn Concepts.BoundingBox the area of a given surface
function Surface.get_surface_bounds(surface)
    Is.Assert(surface, 'missing surface value')
    local x1, y1, x2, y2 = 0, 0, 0, 0

    for chunk in surface.get_chunks() do
        if chunk.x < x1 then
            x1 = chunk.x
        elseif chunk.x > x2 then
            x2 = chunk.x
        end
        if chunk.y < y1 then
            y1 = chunk.y
        elseif chunk.y > y2 then
            y2 = chunk.y
        end
    end

    return Area.construct(x1 * 32, y1 * 32, x2 * 32, y2 * 32)
end

--- Sets the daytime transition thresholds on a given surface
-- @tparam LuaSurface surface the surface for which to set the thresholds
-- @tparam number morning daytime to begin transition from dark to light
-- @tparam number dawn daytime to finish transition from dark to light
-- @tparam number dusk daytime to begin transition from light to dark
-- @tparam number evening daytime to finish transition from light to dark
-- @treturn boolean true if the thresholds were set, false if there was an error
-- @return[opt] the raised error, if any
function Surface.set_daytime_thresholds(surface, morning, dawn, dusk, evening)
    Is.Assert.Valid(surface, 'missing surface value')
    Is.Assert(Is.Float(morning) and Is.Float(dawn) and Is.float(dusk) and Is.Float(evening), 'paramaters must be floats')

    return pcall(
        function()
            surface.dusk = 0
            surface.evening = .0000000001
            surface.morning = .0000000002
            surface.dawn = dawn
            surface.morning = morning
            surface.evening = evening
            surface.dusk = dusk
        end
    )
end

return Surface
