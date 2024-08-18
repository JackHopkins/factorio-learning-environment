--- Tools for working with tiles.
-- A tile represents a 1 unit<sup>2</sup> on a surface in Factorio.
-- @module Area.Tile
-- @usage local Tile = require('__stdlib__/stdlib/area/tile')
-- @see LuaTile

local Tile = {
    __class = 'Tile',
    __index = require('__stdlib__/stdlib/core')
}
setmetatable(Tile, Tile)

local Is = require('__stdlib__/stdlib/utils/is')
local Game = require('__stdlib__/stdlib/game')
local Position = require('__stdlib__/stdlib/area/position')

Tile.__call = Position.__call

--- Get the @{LuaTile.position|tile position} of a tile where the given position resides.
-- @function Tile.from_position
-- @see Area.Position.floor
Tile.from_position = Position.floor

--- Converts a tile position to the @{Concepts.BoundingBox|area} of the tile it is in.
-- @function Tile.to_area
-- @see Area.Position.to_tile_area
Tile.to_area = Position.to_tile_area

--- Creates an array of tile positions for all adjacent tiles (N, E, S, W) **OR** (N, NE, E, SE, S, SW, W, NW) if diagonal is set to true.
-- @tparam LuaSurface surface the surface to examine for adjacent tiles
-- @tparam LuaTile.position position the tile position of the origin tile
-- @tparam[opt=false] boolean diagonal whether to include diagonal tiles
-- @tparam[opt] string tile_name whether to restrict adjacent tiles to a particular tile name (example: "water-tile")
-- @treturn {LuaTile.position,...} an array of tile positions of the tiles that are adjacent to the origin tile
function Tile.adjacent(surface, position, diagonal, tile_name)
    Is.Assert(surface, 'missing surface argument')
    Is.Assert(position, 'missing position argument')

    local offsets = {{0, 1}, {1, 0}, {0, -1}, {-1, 0}}
    if diagonal then
        offsets = {{0, 1}, {1, 1}, {1, 0}, {-1, 1}, {-1, 0}, {-1, -1}, {0, -1}, {1, -1}}
    end
    local adjacent_tiles = {}
    for _, offset in pairs(offsets) do
        local adj_pos = Position.add(position, offset)
        if tile_name then
            local tile = surface.get_tile(adj_pos.x, adj_pos.y)
            if tile and tile.name == tile_name then
                table.insert(adjacent_tiles, adj_pos)
            end
        else
            table.insert(adjacent_tiles, adj_pos)
        end
    end
    return adjacent_tiles
end

--- Gets the user data that is associated with a tile.
-- The user data is stored in the global object and it persists between loads.
-- @tparam LuaSurface surface the surface on which the user data is looked up
-- @tparam LuaTile.position tile_pos the tile position on which the user data is looked up
-- @tparam[opt] Mixed default_value the user data to set for the tile and returned if it did not have user data
-- @treturn ?|nil|Mixed the user data **OR** *nil* if it does not exist for the tile and no default_value was set
function Tile.get_data(surface, tile_pos, default_value)
    surface = Game.get_surface(surface)
    Is.Assert(surface, 'invalid surface')

    local key = Position.to_key(Position.floor(tile_pos))

    return Game.get_or_set_data('_tile_data', surface.index, key, false, default_value)
end
Tile.get = Tile.get_data

--- Associates the user data to a tile.
-- The user data will be stored in the global object and it will persist between loads.
-- @tparam LuaSurface surface the surface on which the user data will reside
-- @tparam LuaTile.position tile_pos the tile position of a tile that will be associated with the user data
-- @tparam ?|nil|Mixed value the user data to set **OR** *nil* to erase the existing user data for the tile
-- @treturn ?|nil|Mixed the previous user data associated with the tile **OR** *nil* if the tile had no previous user data
function Tile.set_data(surface, tile_pos, value)
    surface = Game.get_surface(surface)
    Is.Assert.Valid(surface, 'invalid surface')

    local key = Position.to_key(Position.floor(tile_pos))

    return Game.get_or_set_data('_tile_data', surface.index, key, true, value)
end
Tile.set = Tile.set_data

return Tile
