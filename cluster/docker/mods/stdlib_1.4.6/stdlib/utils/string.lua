--- Extends Lua 5.2 string.
-- @module Utils.string
-- @see string
-- @usage local string = require('__stdlib__/stdlib/utils/string')
local String = {}
getmetatable('').__index = String -- Allow string syntatic sugar to work with this class

String.find = string.find
String.lower = string.lower
String.gmatch = string.gmatch
String.sub = string.sub
String.byte = string.byte
String.char = string.char
String.reverse = string.reverse
String.dump = string.dump
String.rep = string.rep
String.format = string.format
String.match = string.match
String.gsub = string.gsub
String.len = string.len
String.upper = string.upper

for k, v in pairs(string) do if not String[k] then String[k] = v end end

local concat = table.concat
local insert = table.insert
local ceil = math.ceil
local abs = math.abs

--- Returns a copy of the string with any leading or trailing whitespace from the string removed.
-- @tparam string s the string to remove leading or trailing whitespace from
-- @treturn string a copy of the string without leading or trailing whitespace
function String.trim(s)
    return (s:gsub([[^%s*(.-)%s*$]], '%1'))
end

--- Tests if a string starts with a given substring.
-- @tparam string s the string to check for the start substring
-- @tparam string start the substring to test for
-- @treturn boolean true if the start substring was found in the string
function String.starts_with(s, start)
    return s:find(start, 1, true) == 1
end

--- Tests if a string ends with a given substring.
-- @tparam string s the string to check for the end substring
-- @tparam string ends the substring to test for
-- @treturn boolean true if the end substring was found in the string
function String.ends_with(s, ends)
    return #s >= #ends and s:find(ends, #s - #ends + 1, true) and true or false
end

--- Tests if a string contains a given substring.
-- @tparam string s the string to check for the substring
-- @tparam string contains the substring to test for
-- @treturn boolean true if the substring was found in the string
function String.contains(s, contains)
    return s and s:find(contains) ~= nil
end

--- Tests whether a string is empty.
-- @tparam string s the string to test
-- @treturn boolean true if the string is empty
function String.is_empty(s)
    return s == nil or s == ''
end

--- does s only contain alphabetic characters?
-- @string s a string
function String.is_alpha(s)
    return s:find('^%a+$') == 1
end

--- does s only contain digits?
-- @string s a string
function String.is_digit(s)
    return s:find('^%d+$') == 1
end

--- does s only contain alphanumeric characters?
-- @string s a string
function String.is_alnum(s)
    return s:find('^%w+$') == 1
end

--- does s only contain spaces?
-- @string s a string
function String.is_space(s)
    return s:find('^%s+$') == 1
end

--- does s only contain lower case characters?
-- @string s a string
function String.is_lower(s)
    return s:find('^[%l%s]+$') == 1
end

--- does s only contain upper case characters?
-- @string s a string
function String.is_upper(s)
    return s:find('^[%u%s]+$') == 1
end

--- iniital word letters uppercase ('title case').
-- Here 'words' mean chunks of non-space characters.
-- @string s the string
-- @return a string with each word's first letter uppercase
function String.title(s)
    return (s:gsub([[(%S)(%S*)]], function(f, r)
        return f:upper() .. r:lower()
    end))
end

local ellipsis = '...'
local n_ellipsis = #ellipsis

--- Return a shortened version of a string.
-- Fits string within w characters. Removed characters are marked with ellipsis.
-- @string s the string
-- @int w the maxinum size allowed
-- @bool tail true if we want to show the end of the string (head otherwise)
-- @usage ('1234567890'):shorten(8) == '12345...'
-- @usage ('1234567890'):shorten(8, true) == '...67890'
-- @usage ('1234567890'):shorten(20) == '1234567890'
function String.shorten(s, w, tail)
    if #s > w then
        if w < n_ellipsis then return ellipsis:sub(1, w) end
        if tail then
            local i = #s - w + 1 + n_ellipsis
            return ellipsis .. s:sub(i)
        else
            return s:sub(1, w - n_ellipsis) .. ellipsis
        end
    end
    return s
end

--- concatenate the strings using this string as a delimiter.
-- @string s the string
-- @param seq a table of strings or numbers
-- @usage (' '):join {1,2,3} == '1 2 3'
function String.join(s, seq)
    return concat(seq, s)
end

local function _just(s, w, ch, left, right)
    local n = #s
    if w > n then
        if not ch then ch = ' ' end
        local f1, f2
        if left and right then
            local rn = ceil((w - n) / 2)
            local ln = w - n - rn
            f1 = ch:rep(ln)
            f2 = ch:rep(rn)
        elseif right then
            f1 = ch:rep(w - n)
            f2 = ''
        else
            f2 = ch:rep(w - n)
            f1 = ''
        end
        return f1 .. s .. f2
    else
        return s
    end
end

--- left-justify s with width w.
-- @string s the string
-- @int w width of justification
-- @string[opt=' '] ch padding character
function String.ljust(s, w, ch)
    return _just(s, w, ch, true, false)
end

--- right-justify s with width w.
-- @string s the string
-- @int w width of justification
-- @string[opt=' '] ch padding character
function String.rjust(s, w, ch)
    return _just(s, w, ch, false, true)
end

--- center-justify s with width w.
-- @string s the string
-- @int w width of justification
-- @string[opt=' '] ch padding character
function String.center(s, w, ch)
    return _just(s, w, ch, true, true)
end

local noop = function(...)
    return ...
end

--- Splits a string into an array.
-- Note: Empty split substrings are not included in the resulting table.
-- <p>For example, `string.split("foo.bar...", ".", false)` results in the table `{"foo", "bar"}`.
-- @tparam string s the string to split
-- @tparam[opt="."] string sep the separator to use.
-- @tparam[opt=false] boolean pattern whether to interpret the separator as a lua pattern or plaintext for the string split
-- @tparam[opt] function func pass each split string through this function.
-- @treturn {string,...} an array of strings
function String.split(s, sep, pattern, func)
    sep = sep or '.'
    sep = sep ~= '' and sep or '.'
    sep = not pattern and sep:gsub('([^%w])', '%%%1') or sep
    func = func or noop

    local fields = {}
    local start_idx, end_idx = s:find(sep)
    local last_find = 1
    while start_idx do
        local substr = s:sub(last_find, start_idx - 1)
        if substr:len() > 0 then table.insert(fields, func(s:sub(last_find, start_idx - 1))) end
        last_find = end_idx + 1
        start_idx, end_idx = s:find(sep, end_idx + 1)
    end
    local substr = s:sub(last_find)
    if substr:len() > 0 then insert(fields, func(s:sub(last_find))) end
    return fields
end

--- Return the ordinal suffix for a number.
-- @tparam number n
-- @tparam boolean prepend_number if the passed number should be pre-pended
-- @treturn string the ordinal suffix
function String.ordinal_suffix(n, prepend_number)
    if tonumber(n) then
        n = abs(n) % 100
        local d = n % 10
        if d == 1 and n ~= 11 then
            return (prepend_number and n or '') .. 'st'
        elseif d == 2 and n ~= 12 then
            return (prepend_number and n or '') .. 'nd'
        elseif d == 3 and n ~= 13 then
            return (prepend_number and n or '') .. 'rd'
        else
            return (prepend_number and n or '') .. 'th'
        end
    end
    return prepend_number and n
end

local exponent_multipliers = {
    ['y'] = 0.000000000000000000000001,
    ['z'] = 0.000000000000000000001,
    ['a'] = 0.000000000000000001,
    ['f'] = 0.000000000000001,
    ['p'] = 0.000000000001,
    ['n'] = 0.000000001,
    ['u'] = 0.000001,
    ['m'] = 0.001,
    ['c'] = 0.01,
    ['d'] = 0.1,
    [' '] = 1,
    ['h'] = 100,
    ['k'] = 1000,
    ['M'] = 1000000,
    ['G'] = 1000000000,
    ['T'] = 1000000000000,
    ['P'] = 1000000000000000,
    ['E'] = 1000000000000000000,
    ['Z'] = 1000000000000000000000,
    ['Y'] = 1000000000000000000000000
}

--- Convert a metric string prefix to a number value.
-- @tparam string str
-- @treturn float
function String.exponent_number(str)
    if type(str) == 'string' then
        local value, exp = str:match('([%-+]?[0-9]*%.?[0-9]+)([yzafpnumcdhkMGTPEZY]?)')
        exp = exp or ' '
        value = (value or 0) * (exponent_multipliers[exp] or 1)
        return value
    elseif type(str) == 'number' then
        return str
    end
    return 0
end

return String
