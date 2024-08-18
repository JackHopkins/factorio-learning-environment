--- A defines module for retrieving colors by name.
-- Extends the Factorio defines table.
-- @usage require('__stdlib__/stdlib/utils/defines/color')
-- @module defines.color
-- @see Concepts.Color

-- defines table is automatically required in all mod loading stages.

--- A table of colors allowing retrieval by color name.
-- @table color
-- @usage color = defines.color.red
-- @tfield Concepts.Color white
-- @tfield Concepts.Color black
-- @tfield Concepts.Color darkgrey
-- @tfield Concepts.Color grey
-- @tfield Concepts.Color lightgrey
-- @tfield Concepts.Color red
-- @tfield Concepts.Color darkred
-- @tfield Concepts.Color lightred
-- @tfield Concepts.Color green
-- @tfield Concepts.Color darkgreen
-- @tfield Concepts.Color lightgreen
-- @tfield Concepts.Color blue
-- @tfield Concepts.Color darkblue
-- @tfield Concepts.Color lightblue
-- @tfield Concepts.Color orange
-- @tfield Concepts.Color yellow
-- @tfield Concepts.Color pink
-- @tfield Concepts.Color purple
-- @tfield Concepts.Color brown
local color = {}
local colors = require('__stdlib__/stdlib/utils/defines/color_list')

local _mt = {
    __index = function(_, c)
        return colors[c] and {r = colors[c]['r'], g = colors[c]['g'], b = colors[c]['b'], a = colors[c]['a'] or 1} or {r = 1, g = 1, b = 1, a = 1}
    end,
    __pairs = function()
        local k = nil
        local c = colors
        return function()
            local v
            k, v = next(c, k)
            return k, (v and {r = v['r'], g = v['g'], b = v['b'], a = v['a'] or 1}) or nil
        end
    end
}
setmetatable(color, _mt)

_G.defines = _G.defines or {}
_G.defines.color = color

return color
