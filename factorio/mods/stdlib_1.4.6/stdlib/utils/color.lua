--- For playing with colors.
-- @module Utils.Color
-- @usage local Color = require('__stdlib__/stdlib/utils/color')

local Color = {
    __class = 'Color',
    __index = require('__stdlib__/stdlib/core')
}
setmetatable(Color, Color)
local metatable

local table = require('__stdlib__/stdlib/utils/table')
local math = require('__stdlib__/stdlib/utils/math')
local color_list = require('__stdlib__/stdlib/utils/defines/color_list')

--- @table color @{defines.color}
Color.color = require('__stdlib__/stdlib/utils/defines/color')
--- @table anticolor @{defines.anticolor}
Color.anticolor = require('__stdlib__/stdlib/utils/defines/anticolor')
--- @table lightcolor @{defines.lightcolor}
Color.lightcolor = require('__stdlib__/stdlib/utils/defines/lightcolor')

--- Color Constructors
-- @section Color Constructors

--- Create a new Color object.
-- it can be passed, A Color, a string color name, an array,
-- a list of float paramaters (RGB), a color dictionary, or hex
-- @param any
-- @treturn Color
function Color.new(...)
    if (...) == Color then
        return Color.new(select(2, ...))
    else
        local c_type = type((...) or nil)
        if not ... then
            -- from a hex code or word color string, "red"
            return Color.white()
        elseif c_type == 'string' then
            if (...):find('%x%x%x%x%x%x$') then
                return Color.from_hex(...)
            else
                return Color.from_string(...)
            end
        elseif c_type == 'number' then
            return Color.from_params(...)
        elseif c_type == 'table' then
            return Color.copy(...)
        end
    end
end
Color.__call = Color.new

--- Loads the color metatmethods into table without any checking.
-- @tparam Color color
-- @treturn color
function Color.load(color)
    return setmetatable(color, metatable)
end

--- Copies the color into a new Color.
-- @tparam Color color
-- @tparam[opt] float alpha Change the alpha of the copied color
-- @treturn Color
function Color.copy(color, alpha)
    if type(color) == 'table' then
        if color == Color then
            return Color.white()
        elseif getmetatable(color) == metatable then
            return setmetatable({r = color.r, g = color.g, b = color.b, a = alpha or color.a or 0.5}, metatable)
        elseif type((next(color))) == "number" then
            return Color.from_array(color, alpha)
        else
            return Color.from_table(color, alpha)
        end
    else
        Color.new(color, alpha)
    end
end

--- Returns a white Color.
-- @treturn Color
function Color.white()
    local color = {r = 1, g = 1, b = 1, a = 0.5}
    return setmetatable(color, metatable)
end

--- Returns a black color.
-- @treturn Color
function Color.black()
    local color = {r = 0, g = 0, b = 0, a = 0.5}
    return setmetatable(color, metatable)
end

--- Returns a color from a string name if known.
-- Returns white if color string is unknown
-- @tparam string string_name
-- @tparam[opt] float alpha
-- @treturn Color
function Color.from_string(string_name, alpha)
    local color = Color.color[string_name]
    if color then
        color.a = alpha or color.a or 0.5
        return setmetatable(color, metatable)
    end
    return Color.white()
end

--- Converts a color in the rgb format to a color table.
-- @tparam[opt=0] float r 0-255 red
-- @tparam[opt=0] float g 0-255 green
-- @tparam[opt=0] float b 0-255 blue
-- @tparam[opt=255] float a 0-255 alpha
-- @treturn Concepts.Color
function Color.from_params(r, g, b, a)
    local new = Color.normalize {r = r, g = g or r, b = b or r, a = a or 0.5}
    return setmetatable(new, metatable)
end
--- @see Color.from_params
Color.from_rgb = Color.from_params

--- Converts a color in the array format to a color in the table format.
-- @tparam array color the color to convert &mdash; { [1] = @{float}, [2] = @{float}, [3] = @{float}, [4] = @{float} }
-- @tparam[opt] float alpha
-- @treturn Concepts.Color a converted color &mdash; { r = c\_arr[1], g = c\_arr[2], b = c\_arr[3], a = c\_arr[4] }
function Color.from_array(color, alpha)
    return Color.from_params(color[1] or 0, color[2] or 0, color[3] or 0, alpha or color[4] or 0.5)
end

--- Converts a color in the dictionary format to a color in the Color format.
-- @tparam table color the color to convert
-- @tparam[opt] float alpha
-- @treturn Color
function Color.from_table(color, alpha)
    return Color.from_params(color.r or 0, color.g or 0, color.b or 0, alpha or color.a or 0.5)
end

--- Get a color table with a hexadecimal string.
-- Optionally provide the value for the alpha channel.
-- @tparam string color hexadecimal color string (#ffffff, not #fff)
-- @tparam[opt=1] float alpha the alpha value to set; such that *** 0 &#8924; value &#8924; 1 ***
-- @treturn Concepts.Color a color table with RGB converted from Hex and with alpha
function Color.from_hex(color, alpha)
    assert(type(color) == 'string', 'missing color hex value')
    local match = color:match('%x?%x?%x%x%x%x%x%x$')
    color = tonumber(match, 16)
    local new = {r = 0, g = 0, b = 0, a = 1}
    if #match == 8 then
        new.r = bit32.extract(color, 24, 8) / 255
        new.g = bit32.extract(color, 16, 8) / 255
        new.b = bit32.extract(color, 8, 8) / 255
        new.a = bit32.extract(color, 0, 8) / 255
    elseif #match == 6 then
        new.r = bit32.extract(color, 16, 8) / 255
        new.g = bit32.extract(color, 8, 8) / 255
        new.b = bit32.extract(color, 0, 8) / 255
        new.a = alpha and (alpha > 1 and math.min(alpha, 255) / 255) or alpha or 0.5
    end
    return setmetatable(new, metatable)
end

--- @section end

--- Color Methods
-- @section Color Methods

-- DEPRECATED
function Color.set(color, alpha)
    color = color or {r = 1, g = 1, b = 1}
    if #color > 0 then
        color = Color.from_array(color)
    end
    color.a = alpha or color.a or 1
    return color
end

--- Normalizes a color between 0 and 1
-- @tparam Color color
-- @return Color
function Color.normalize(color)
    color.a = color.a or 1
    if color.r > 1 or color.g > 1 or color.b > 1 or color.a > 1 then
        color.r = color.r > 1 and math.min(color.r, 255) / 255 or color.r
        color.g = color.g > 1 and math.min(color.g, 255) / 255 or color.g
        color.b = color.b > 1 and math.min(color.b, 255) / 255 or color.b
        color.a = color.a > 1 and math.min(color.a, 255) / 255 or color.a
    end
    return color
end

--- Set the alpha channel on a color
-- @tparam Color color
-- @tparam[opt = 1] float alpha
-- @treturn Color
function Color.alpha(color, alpha)
    alpha = alpha or 1
    alpha = alpha > 1 and alpha / 255 or alpha
    color.a = alpha
    return color
end

--- Premultiply alpha
-- @tparam Color color
-- @tparam float alpha
-- @return Color
function Color.premul_alpha(color, alpha)
    alpha = alpha > 1 and math.min(alpha, 255) / 255 or alpha
    local new = {}
    new.r = math.clamp(color.r * alpha)
    new.g = math.clamp(color.g * alpha)
    new.b = math.clamp(color.b * alpha)
    new.a = color.a or 1
    return setmetatable(new, metatable)
end

local function make_color(lhs, rhs)
    if not Color.is_color(rhs) then
        rhs = Color.new(rhs)
    elseif not Color.is_color(lhs) then
        lhs = Color.new(lhs)
    end
    return lhs, rhs
end

local function clamped(r, g, b, a)
    local new = {}
    new.r = math.clamp(r)
    new.g = math.clamp(g)
    new.b = math.clamp(b)
    new.a = math.clamp(a)

    return setmetatable(new, metatable)
end

--- Add 2 colors together.
-- @tparam Color lhs
-- @tparam Color rhs
-- @return Color
function Color.add(lhs, rhs)
    lhs, rhs = make_color(lhs, rhs)
    return clamped(lhs.r + rhs.r, lhs.g + rhs.g, lhs.b + rhs.b, math.max(lhs.a, rhs.a))
end

--- Subtract 2 colors together.
-- @tparam Color lhs
-- @tparam Color rhs
-- @return Color
function Color.subtract(lhs, rhs)
    lhs, rhs = make_color(lhs, rhs)
    return clamped(lhs.r - rhs.r, lhs.g - rhs.g, lhs.b - rhs.b, math.max(lhs.a, rhs.a))
end

--- Multiply 2 colors together.
-- @tparam Color lhs
-- @tparam Color rhs
-- @return Color
function Color.multiply(lhs, rhs)
    lhs, rhs = make_color(lhs, rhs)
    return clamped(lhs.r * rhs.r, lhs.g * rhs.g, lhs.b * rhs.b, math.max(lhs.a, rhs.a))
end

--- Add 2 colors together.
-- @tparam Color lhs
-- @tparam Color rhs
-- @return Color
function Color.divide(lhs, rhs)
    lhs, rhs = make_color(lhs, rhs)
    return clamped(lhs.r / rhs.r, lhs.g / rhs.g, lhs.b / rhs.b, math.max(lhs.a, rhs.a))
end

--- Modulo of 2 colors.
-- @tparam Color lhs
-- @tparam Color rhs
-- @treturn Color
function Color.modulo(lhs, rhs)
    lhs, rhs = make_color(lhs, rhs)
    return clamped(lhs.r % rhs.r, lhs.g % rhs.g, lhs.b % rhs.b, math.max(lhs.a, rhs.a))
end

--- Flip a color to white or black.
-- @tparam Color color
-- @treturn Color
function Color.unary(color)
    return Color.len(color) < 1.5 and Color.white() or Color.black()
end

--- @section end

--- Color Functions
-- @section Color Functions

--- Get the length of a color by adding all its values together
-- @tparam Color color
-- @treturn number
function Color.len(color)
    return color.r + color.g + color.b
end

--- Are both colors equal.
-- @tparam Color lhs
-- @tparam Color rhs
-- @treturn boolean
function Color.equals(lhs, rhs)
    return lhs.r == rhs.r and lhs.g == rhs.g and lhs.b == rhs.b and lhs.a == rhs.a
end

--- Is LHS less than RHS.
-- @tparam Color lhs
-- @tparam Color rhs
-- @treturn boolean
function Color.less_than(lhs, rhs)
    lhs, rhs = make_color(lhs, rhs)
    return Color.len(lhs) < Color.len(rhs)
end

--- Is LHS less than or equal to RHS.
-- @tparam Color lhs
-- @tparam Color rhs
-- @treturn boolean
function Color.less_than_eq(lhs, rhs)
    lhs, rhs = make_color(lhs, rhs)
    return Color.len(lhs) <= Color.len(rhs)
end

--- Return a hex formated string from a color.
-- @tparam Color color
-- @treturn string
function Color.to_hex(color)
    local str = {
        string.format('%x', color.r * 255),
        string.format('%x', color.g * 255),
        string.format('%x', color.b * 255),
        string.format('%x', (color.a or 1) * 255)
    }
    return '#' .. table.concat(str, '')
end

--- Return an array with 4 paramaters.
-- @tparam Color color
-- @treturn array
function Color.to_array(color)
    return {color.r, color.g, color.b, color.a}
end

--- @see Color.to_array
Color.pack = Color.to_array

--- Return the color as 4 paramaters.
-- @tparam Color color
-- @return float
-- @return float
-- @return float
-- @return float
function Color.to_params(color)
    return color.r, color.g, color.b, color.a
end

--- @see Color.to_params
Color.unpack = Color.to_params

--- Return the Color as a string.
-- @tparam Color color
-- @treturn string
function Color.to_string(color)
    local str = {
        'r = ' .. (color.r or 0),
        'g = ' .. (color.g or 0),
        'b = ' .. (color.b or 0),
        'a = ' .. (color.a or 1)
    }
    return '{' .. table.concat(str, ', ') .. '}'
end

--- Is this a correctly formatted color.
-- @tparam Color color
-- @treturn boolean
function Color.is_complex(color)
    local r, g, b, a
    if type(color) == 'table' then
        r = color.r and color.r <= 1
        g = color.g and color.g <= 1
        b = color.b and color.b <= 1
        a = color.b and color.a <= 1
    end
    return r and b and g and a
end

--- Is this a Color object.
-- @tparam Color color
-- @treturn boolean
function Color.is_Color(color)
    return getmetatable(color) == metatable
end

--- Is this a Color object or correctly formatted color table.
-- @tparam Color color
-- @treturn boolean
function Color.is_color(color)
    return Color.is_Color(color) or Color.is_complex(color)
end

local function get_color_distance(lhs, rhs)
    local disp = {r = lhs.r - rhs.r, g = lhs.g - rhs.g, b = lhs.b - rhs.b}
    return (disp.r * disp.r + disp.g * disp.g + disp.b * disp.b)
end

--Takes a color and table of colors, finds key of color in table that most closely matches given color
function Color.best_color_match(color)
    local closest
    local min = 1
    for color_name, compare in pairs(color_list) do
        local distance = get_color_distance(color, compare)
        min = (distance < min) and distance or min
        if distance == min then
            closest = color_name
        end
    end
    return closest
end

--- @section end

metatable = {
    __class = 'color',
    __index = Color,
    __call = Color.copy,
    __add = Color.add,
    __sub = Color.subtract,
    __mul = Color.multipy,
    __div = Color.divide,
    __mod = Color.modulo,
    __unm = Color.unary,
    __eq = Color.equals,
    __lt = Color.less_than,
    __le = Color.less_than_eq,
    __len = Color.len,
    __tostring = Color.to_string,
    __concat = concat
}

return Color
