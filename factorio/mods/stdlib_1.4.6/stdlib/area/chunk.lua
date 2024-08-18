--- For working with chunks.
-- A chunk represents a 32 tile<sup>2</sup> on a surface in Factorio.
-- @module Area.Chunk
-- @usage local Chunk = require('__stdlib__/stdlib/area/chunk')
-- @see Concepts.ChunkPosition

local Chunk = {
    __class = 'Chunk',
    __index = require('__stdlib__/stdlib/core')
}
setmetatable(Chunk, Chunk)

local Game = require('__stdlib__/stdlib/game')
local Position = require('__stdlib__/stdlib/area/position')

local AREA_PATH = '__stdlib__/stdlib/area/area'

Chunk.__call = Position.__call

--- Gets the chunk position of a chunk where the specified position resides.
-- @function Chunk.from_position
-- @see Area.Position.to_chunk_position
Chunk.from_position = Position.to_chunk_position

--- Gets the top_left position from a chunk position.
-- @function Chunk.to_position
-- @see Area.Position.from_chunk_position
Chunk.to_position = Position.from_chunk_position

--Chunk.to_center_position
--Chunk.to_center_tile_position

-- Hackish function, Factorio lua doesn't allow require inside functions because...
local function load_area(area)
    local Area = package.loaded[AREA_PATH]
    if not Area then
        local log = log or function() end
        log('WARNING: Area for Position not found in package.loaded')
    end
    return Area and Area.load(area) or area
end

--- Gets the area of a chunk from the specified chunk position.
-- @tparam Concepts.ChunkPosition pos the chunk position
-- @treturn Concepts.BoundingBox the chunk's area
function Chunk.to_area(pos)
    local left_top = Chunk.to_position(pos)
    local right_bottom = Position.add(left_top, 32, 32)

    return load_area {left_top = left_top, right_bottom = right_bottom}
end


--- Gets the user data that is associated with a chunk.
-- The user data is stored in the global object and it persists between loads.
-- @tparam LuaSurface surface the surface on which the user data is looked up
-- @tparam Concepts.ChunkPosition chunk_pos the chunk position on which the user data is looked up
-- @tparam[opt] Mixed default_value the user data to set for the chunk and returned if the chunk had no user data
-- @treturn ?|nil|Mixed the user data **OR** *nil* if it does not exist for the chunk and if no default_value was set
function Chunk.get_data(surface, chunk_pos, default_value)
    surface = Game.get_surface(surface)
    assert(surface, 'invalid surface')

    local key = Position(chunk_pos):to_key()

    return Game.get_or_set_data('_chunk_data', surface.index, key, false, default_value)
end
Chunk.get = Chunk.get_data

--- Associates the user data to a chunk.
-- The user data will be stored in the global object and it will persist between loads.
-- @tparam LuaSurface surface the surface on which the user data will reside
-- @tparam Concepts.ChunkPosition chunk_pos the chunk position to associate with the user data
-- @tparam ?|nil|Mixed value the user data to set **OR** *nil* to erase the existing user data for the chunk
-- @treturn ?|nil|Mixed the previous user data associated with the chunk **OR** *nil* if the chunk had no previous user data
function Chunk.set_data(surface, chunk_pos, value)
    surface = Game.get_surface(surface)
    assert(surface, 'invalid surface')

    local key = Position(chunk_pos):to_key()

    return Game.get_or_set_data('_chunk_data', surface.index, key, true, value)
end
Chunk.set = Chunk.set_data

return Chunk
