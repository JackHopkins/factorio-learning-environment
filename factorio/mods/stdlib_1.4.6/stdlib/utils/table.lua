--- Extends Lua 5.2 table.
-- @module Utils.table
-- @see table
-- @usage local table = require('__stdlib__/stdlib/utils/table')
local Table = {}

Table.remove = table.remove
Table.sort = table.sort
Table.pack = table.pack
Table.unpack = table.unpack
Table.insert = table.insert
Table.concat = table.concat

-- Import base lua table into Table
for k, v in pairs(table) do if not Table[k] then Table[k] = v end end

--- Given a mapping function, creates a transformed copy of the table
-- by calling the function for each element in the table, and using
-- the result as the new value for the key. Passes the index as second argument to the function.
-- @usage a= { 1, 2, 3, 4, 5}
-- table.map(a, function(v) return v * 10 end) --produces: { 10, 20, 30, 40, 50 }
-- @usage a = {1, 2, 3, 4, 5}
-- table.map(a, function(v, k, x) return v * k + x end, 100) --produces { 101, 104, 109, 116, 125}
-- @tparam table tbl the table to be mapped to the transform
-- @tparam function func the function to transform values
-- @param[opt] ... additional arguments passed to the function
-- @treturn table a new table containing the keys and mapped values
function Table.map(tbl, func, ...)
    local newtbl = {}
    for k, v in pairs(tbl) do newtbl[k] = func(v, k, ...) end
    return newtbl
end

--- Given a filter function, creates a filtered copy of the table
-- by calling the function for each element in the table, and
-- filtering out any key-value pairs for non-true results. Passes the index as second argument to the function.
-- @usage a= { 1, 2, 3, 4, 5}
-- table.filter(a, function(v) return v % 2 == 0 end) --produces: { 2, 4 }
-- @usage a = {1, 2, 3, 4, 5}
-- table.filter(a, function(v, k, x) return k % 2 == 1 end) --produces: { 1, 3, 5 }
-- @tparam table tbl the table to be filtered
-- @tparam function func the function to filter values
-- @param[opt] ... additional arguments passed to the function
-- @treturn table a new table containing the filtered key-value pairs
function Table.filter(tbl, func, ...)
    local newtbl = {}
    local add = #tbl > 0
    for k, v in pairs(tbl) do
        if func(v, k, ...) then
            if add then
                Table.insert(newtbl, v)
            else
                newtbl[k] = v
            end
        end
    end
    return newtbl
end

--- Given a candidate search function, iterates over the table, calling the function
-- for each element in the table, and returns the first element the search function returned true.
-- Passes the index as second argument to the function.
-- @usage a= { 1, 2, 3, 4, 5}
-- table.find(a, function(v) return v % 2 == 0 end) --produces: 2
-- @usage a = {1, 2, 3, 4, 5}
-- table.find(a, function(v, k, x) return k % 2 == 1 end) --produces: 1
-- @tparam table tbl the table to be searched
-- @tparam function func the function to use to search for any matching element
-- @param[opt] ... additional arguments passed to the function
-- @treturn ?|nil|Mixed the first found value, or nil if none was found
function Table.find(tbl, func, ...)
    for k, v in pairs(tbl) do if func(v, k, ...) then return v, k end end
    return nil
end

--- Given a candidate search function, iterates over the table, calling the function
-- for each element in the table, and returns true if search function returned true.
-- Passes the index as second argument to the function.
-- @see table.find
-- @usage a= { 1, 2, 3, 4, 5}
-- table.any(a, function(v) return v % 2 == 0 end) --produces: true
-- @usage a = {1, 2, 3, 4, 5}
-- table.any(a, function(v, k, x) return k % 2 == 1 end) --produces: true
-- @tparam table tbl the table to be searched
-- @tparam function func the function to use to search for any matching element
-- @param[opt] ... additional arguments passed to the function
-- @treturn boolean true if an element was found, false if none was found
function Table.any(tbl, func, ...)
    return Table.find(tbl, func, ...) ~= nil
end

--- Given a candidate search function, iterates over the table, calling the function
-- for each element in the table, and returns true if search function returned true
-- for all items in the table.
-- Passes the index as second argument to the function.
-- @tparam table tbl the table to be searched
-- @tparam function func the function to used to search
-- @param[opt] ... additional arguments passed to the search function
-- @treturn boolean true if all elements in the table return truthy
function Table.all(tbl, func, ...)
    for k, v in pairs(tbl) do if not func(v, k, ...) then return false end end
    return true
end

--- Given a function, apply it to each element in the table.
-- Passes the index as the second argument to the function.
-- <p>Iteration is aborted if the applied function returns true for any element during iteration.
-- @usage
-- a = {10, 20, 30, 40}
-- table.each(a, function(v) game.print(v) end) --prints 10, 20, 30, 40, 50
-- @tparam table tbl the table to be iterated
-- @tparam function func the function to apply to elements
-- @param[opt] ... additional arguments passed to the function
-- @treturn table the table where the given function has been applied to its elements
function Table.each(tbl, func, ...)
    for k, v in pairs(tbl) do if func(v, k, ...) then break end end
    return tbl
end

--- Returns a new array that is a one-dimensional recursive flattening of the given array.
-- For every element that is an array, extract its elements into the new array.
-- <p>The optional level argument determines the level of recursion to flatten.
-- > This function flattens an integer-indexed array, but not an associative array.
-- @tparam array tbl the array to be flattened
-- @tparam[opt] uint level recursive levels, or no limit to recursion if not supplied
-- @treturn array a new array that represents the flattened contents of the given array
function Table.flatten(tbl, level)
    local flattened = {}
    Table.each(tbl, function(value)
        if type(value) == 'table' and #value > 0 then
            if level then
                if level > 0 then
                    Table.merge(flattened, Table.flatten(value, level - 1), true)
                else
                    Table.insert(flattened, value)
                end
            else
                Table.merge(flattened, Table.flatten(value), true)
            end
        else
            Table.insert(flattened, value)
        end
    end)
    return flattened
end

--- Given an array, returns the first element or nil if no element exists.
-- @tparam array tbl the array
-- @treturn ?|nil|Mixed the first element
function Table.first(tbl)
    return tbl[1]
end

--- Given an array, returns the last element or nil if no elements exist.
-- @tparam array tbl the array
-- @treturn ?|nil|Mixed the last element or nil
function Table.last(tbl)
    local size = #tbl
    if size == 0 then return nil end
    return tbl[size]
end

--- Given an array of only numeric values, returns the minimum or nil if no element exists.
-- @tparam {number,...} tbl the array with only numeric values
-- @treturn ?|nil|number the minimum value
function Table.min(tbl)
    if #tbl == 0 then return nil end

    local min = tbl[1]
    for _, num in pairs(tbl) do min = num < min and num or min end
    return min
end

---Given an array of only numeric values, returns the maximum or nil if no element exists.
-- @tparam {number,...} tbl the array with only numeric values
-- @treturn ?|nil|number the maximum value
function Table.max(tbl)
    if #tbl == 0 then return nil end

    local max = tbl[1]
    for _, num in pairs(tbl) do max = num > max and num or max end
    return max
end

--- Given an array of only numeric values, return the sum of all values, or 0 for empty arrays.
-- @tparam {number,...} tbl the array with only numeric values
-- @treturn number the sum of the numbers or zero if the given array was empty
function Table.sum(tbl)
    local sum = 0
    for _, num in pairs(tbl) do sum = sum + num end
    return sum
end

--- Given an array of only numeric values, returns the average or nil if no element exists.
-- @tparam {number,...} tbl the array with only numeric values
-- @treturn ?|nil|number the average value
function Table.avg(tbl)
    local cnt = #tbl
    return cnt ~= 0 and Table.sum(tbl) / cnt or nil
end

--- Return a new array slice.
-- @tparam array tbl the table to slice
-- @tparam[opt=1] number start
-- @tparam[opt=#tbl] number stop stop at this index, use negative to stop from end.
-- @usage local tab = { 10, 20, 30, 40, 50}
-- slice(tab, 2, -2) --returns { 20, 30, 40 }
function Table.slice(tbl, start, stop)
    local res = {}
    local n = #tbl

    start = start or 1
    stop = stop or n
    stop = stop < 0 and (n + stop + 1) or stop

    if start < 1 or start > n then return {} end

    local k = 1
    for i = start, stop do
        res[k] = tbl[i]
        k = k + 1
    end
    return res
end

--- Merges two tables, values from first get overwritten by the second.
-- @usage
-- function some_func(x, y, args)
--     args = table.merge({option1=false}, args)
--     if opts.option1 == true then return x else return y end
-- end
-- some_func(1,2) -- returns 2
-- some_func(1,2,{option1=true}) -- returns 1
-- @tparam table tblA first table
-- @tparam table tblB second table
-- @tparam[opt=false] boolean array_merge set to true to merge the tables as an array or false for an associative array
-- @tparam[opt=false] boolean raw use rawset for associated array
-- @treturn array|table an array or an associated array where tblA and tblB have been merged
function Table.merge(tblA, tblB, array_merge, raw)
    if not tblB then return tblA end
    if array_merge then
        for _, v in pairs(tblB) do Table.insert(tblA, v) end
    else
        for k, v in pairs(tblB) do
            if raw then
                rawset(tblA, k, v)
            else
                tblA[k] = v
            end
        end
    end
    return tblA
end

function Table.array_combine(...)
    local tables = {...}
    local new = {}
    for _, tab in pairs(tables) do for _, v in pairs(tab) do Table.insert(new, v) end end
    return new
end

function Table.dictionary_combine(...)
    local tables = {...}
    local new = {}
    for _, tab in pairs(tables) do for k, v in pairs(tab) do new[k] = v end end
    return new
end

--- Creates a new merged dictionary, if the values in tbl_b are in tbl_a they are not overwritten.
-- @usage
-- local a = {one = A}
-- local b = {one = Z, two = B}
-- local merged = table.dictionary_merge(tbl_a, tbl_b)
-- --merged = {one = A, two = B}
-- @tparam table tbl_a
-- @tparam table tbl_b
-- @treturn table with a and b merged together
function Table.dictionary_merge(tbl_a, tbl_b)
    local meta_a = getmetatable(tbl_a)
    local meta_b = getmetatable(tbl_b)
    setmetatable(tbl_a, nil)
    setmetatable(tbl_b, nil)

    local new_t = {}
    for k, v in pairs(tbl_a) do new_t[k] = v end
    for k, v in pairs(tbl_b or {}) do if not new_t[k] then new_t[k] = v end end
    setmetatable(tbl_a, meta_a)
    setmetatable(tbl_b, meta_b)
    return new_t
end

--- Compares 2 tables for inner equality.
-- Modified from factorio/data/core/lualib/util.lua
-- @tparam table t1
-- @tparam table t2
-- @tparam[opt=false] boolean ignore_mt ignore eq metamethod
-- @treturn boolean if the tables are the same
-- @author Sparr, Nexela, luacode.org
function Table.deep_compare(t1, t2, ignore_mt)
    local ty1, ty2 = type(t1), type(t2)
    if ty1 ~= ty2 then return false end
    -- non-table types can be directly compared
    if ty1 ~= 'table' and ty2 ~= 'table' then return t1 == t2 end
    -- as well as tables which have the metamethod __eq
    if not ignore_mt then
        local mt = getmetatable(t1)
        if mt and mt.__eq then return t1 == t2 end
    end
    for k1, v1 in pairs(t1) do
        local v2 = t2[k1]
        if v2 == nil or not Table.deep_compare(v1, v2) then return false end
    end
    for k in pairs(t2) do if t1[k] == nil then return false end end

    return true
end
Table.compare = Table.deep_compare

--- Creates a deep copy of table without copying Factorio objects.
-- copied from factorio/data/core/lualib/util.lua
-- @usage local copy = table.deep_copy[data.raw.["stone-furnace"]["stone-furnace"]]
-- -- returns a copy of the stone furnace entity
-- @tparam table object the table to copy
-- @treturn table a copy of the table
function Table.deep_copy(object)
    local lookup_table = {}

    local function _copy(inner)
        if type(inner) ~= 'table' then
            return inner
        elseif inner.__self then
            return inner
        elseif lookup_table[inner] then
            return lookup_table[inner]
        end
        local new_table = {}
        lookup_table[inner] = new_table
        for index, value in pairs(inner) do new_table[_copy(index)] = _copy(value) end
        return setmetatable(new_table, getmetatable(inner))
    end

    return _copy(object)
end
Table.deepcopy = Table.deep_copy

--- Creates a deep copy of a table without copying factorio objects
-- internal table refs are also deepcopy. The resulting table should
-- @usage local copy = table.fullcopy[data.raw.["stone-furnace"]["stone-furnace"]]
-- -- returns a deepcopy of the stone furnace entity with no internal table references.
-- @tparam table object the table to copy
-- @treturn table a copy of the table
function Table.full_copy(object)
    local lookup_table = {}

    local function _copy(inner)
        if type(inner) ~= 'table' then
            return inner
        elseif inner.__self then
            return inner
        elseif lookup_table[inner] then
            return _copy(lookup_table[inner])
        end
        local new_table = {}
        lookup_table[inner] = new_table
        for index, value in pairs(inner) do new_table[_copy(index)] = _copy(value) end
        return setmetatable(new_table, getmetatable(inner))
    end

    return _copy(object)
end
Table.fullcopy = Table.full_copy

--- Creates a flexible deep copy of an object, recursively copying sub-objects
-- @usage local copy = table.flexcopy(data.raw.["stone-furnace"]["stone-furnace"])
-- -- returns a copy of the stone furnace entity
-- @tparam table object the table to copy
-- @treturn table a copy of the table
function Table.flex_copy(object)
    local lookup_table = {}

    local function _copy(inner)
        if type(inner) ~= 'table' then
            return inner
        elseif inner.__self then
            return inner
        elseif lookup_table[inner] then
            return lookup_table[inner]
        elseif type(inner._copy_with) == 'function' then
            lookup_table[inner] = inner:_copy_with(_copy)
            return lookup_table[inner]
        end
        local new_table = {}
        lookup_table[inner] = new_table
        for index, value in pairs(inner) do new_table[_copy(index)] = _copy(value) end
        return setmetatable(new_table, getmetatable(inner))
    end

    return _copy(object)
end
Table.flexcopy = Table.flex_copy

--- Returns a copy of all of the values in the table.
-- @tparam table tbl the table to copy the keys from, or an empty table if tbl is nil
-- @tparam[opt] boolean sorted whether to sort the keys (slower) or keep the random order from pairs()
-- @tparam[opt] boolean as_string whether to try and parse the values as strings, or leave them as their existing type
-- @treturn array an array with a copy of all the values in the table
function Table.values(tbl, sorted, as_string)
    if not tbl then return {} end
    local valueset = {}
    local n = 0
    if as_string then -- checking as_string /before/ looping is faster
        for _, v in pairs(tbl) do
            n = n + 1
            valueset[n] = tostring(v)
        end
    else
        for _, v in pairs(tbl) do
            n = n + 1
            valueset[n] = v
        end
    end
    if sorted then
        table.sort(valueset, function(x, y) -- sorts tables with mixed index types.
            local tx = type(x) == 'number'
            local ty = type(y) == 'number'
            if tx == ty then
                return x < y and true or false -- similar type can be compared
            elseif tx == true then
                return true -- only x is a number and goes first
            else
                return false -- only y is a number and goes first
            end
        end)
    end
    return valueset
end

--- Returns a copy of all of the keys in the table.
-- @tparam table tbl the table to copy the keys from, or an empty table if tbl is nil
-- @tparam[opt] boolean sorted whether to sort the keys (slower) or keep the random order from pairs()
-- @tparam[opt] boolean as_string whether to try and parse the keys as strings, or leave them as their existing type
-- @treturn array an array with a copy of all the keys in the table
function Table.keys(tbl, sorted, as_string)
    if not tbl then return {} end
    local keyset = {}
    local n = 0
    if as_string then -- checking as_string /before/ looping is faster
        for k, _ in pairs(tbl) do
            n = n + 1
            keyset[n] = tostring(k)
        end
    else
        for k, _ in pairs(tbl) do
            n = n + 1
            keyset[n] = k
        end
    end
    if sorted then
        table.sort(keyset, function(x, y) -- sorts tables with mixed index types.
            local tx = type(x) == 'number'
            local ty = type(y) == 'number'
            if tx == ty then
                return x < y and true or false -- similar type can be compared
            elseif tx == true then
                return true -- only x is a number and goes first
            else
                return false -- only y is a number and goes first
            end
        end)
    end
    return keyset
end

--- Removes keys from a table by setting the values associated with the keys to nil.
-- @usage local a = {1, 2, 3, 4}
-- table.remove_keys(a, {1,3}) --returns {nil, 2, nil, 4}
-- @usage local b = {k1 = 1, k2 = 'foo', old_key = 'bar'}
-- table.remove_keys(b, {'old_key'}) --returns {k1 = 1, k2 = 'foo'}
-- @tparam table tbl the table to remove the keys from
-- @tparam {Mixed,...} keys an array of keys that exist in the given table
-- @treturn table tbl without the specified keys
function Table.remove_keys(tbl, keys)
    for i = 1, #keys do tbl[keys[i]] = nil end
    return tbl
end

--- Returns the number of keys in a table, if func is passed only count keys when the function is true.
-- @tparam table tbl to count keys
-- @tparam[opt] function func to increment counter
-- @param[optchain] ... additional arguments passed to the function
-- @treturn number The number of keys matching the function or the number of all keys if func isn't passed
-- @treturn number The total number of keys
-- @usage local a = { 1, 2, 3, 4, 5}
-- table.count_keys(a) -- produces: 5, 5
-- @usage local a = {1, 2, 3, 4, 5}
-- table.count_keys(a, function(v, k) return k % 2 == 1 end) -- produces: 3, 5
function Table.count_keys(tbl, func, ...)
    local count, total = 0, 0
    if type(tbl) == 'table' then
        for k, v in pairs(tbl) do
            total = total + 1
            if func then
                if func(v, k, ...) then count = count + 1 end
            else
                count = count + 1
            end
        end
    end
    return count, total
end

--- Returns an inverted (***{[value] = key,...}***) copy of the given table. If the values are not unique,
-- the assigned key depends on the order of pairs().
-- @usage local a = {k1 = 'foo', k2 = 'bar'}
-- table.invert(a) --returns {'foo' = k1, 'bar' = k2}
-- @usage local b = {k1 = 'foo', k2 = 'bar', k3 = 'bar'}
-- table.invert(b) --returns {'foo' = k1, 'bar' = ?}
-- @tparam table tbl the table to invert
-- @treturn table a new table with inverted mapping
function Table.invert(tbl)
    local inverted = {}
    for k, v in pairs(tbl) do inverted[v] = k end
    return inverted
end

local function _size(tbl)
    local count = 0
    for _ in pairs(tbl or {}) do count = count + 1 end
    return count
end

--- Return the size of a table using the factorio built in table_size function
-- @function size
-- @tparam table table to use
-- @treturn int size of the table
Table.size = _ENV.table_size or _size

--- For all string or number values in an array map them to a value = value table
-- @usage local a = {"v1", "v2"}
-- table.array_to_bool(a) -- return {["v1"] = "v1", ["v2"]= "v2"}
-- @tparam table tbl the table to convert
-- @tparam[opt=false] boolean as_bool map to true instead of value
-- @treturn table the converted table
function Table.array_to_dictionary(tbl, as_bool)
    local newtbl = {}
    for _, v in ipairs(tbl) do
        if type(v) == 'string' or type(v) == 'number' then newtbl[v] = as_bool and true or v end
    end
    return newtbl
end

-- Returns an array of unique values from tbl
-- @tparam table tbl
-- @treturn table an array of unique values.
function Table.unique_values(tbl)
    return Table.keys(Table.invert(tbl))
end

--- Does the table contain any elements
-- @tparam table tbl
-- @treturn boolean
function Table.is_empty(tbl)
    return _ENV.table_size and _ENV.table_size(tbl) == 0 or next(tbl) == nil
end

--- Clear all elements in a table
-- @tparam table tbl the table to clear
-- @treturn table the cleared table
function Table.clear(tbl)
    for k in pairs(tbl) do tbl[k] = nil end
    return tbl
end

return Table
