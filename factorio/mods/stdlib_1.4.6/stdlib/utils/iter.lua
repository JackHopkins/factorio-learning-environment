--- Iterator library.
-- @module Utils.Iter

local Iter = {}

local pairs = pairs
local ipairs = ipairs
Iter.pairs = pairs
Iter.ipairs = ipairs

function Iter.spairs(t, order)
    -- collect the keys
    local keys = {}
    for k in pairs(t) do
        keys[#keys + 1] = k
    end

    -- if order function given, sort by it by passing the table and keys a, b,
    -- otherwise just sort the keys
    if order then
        table.sort(
            keys,
            function(a, b)
                return order(t, a, b)
            end
        )
    else
        table.sort(keys)
    end

    -- return the iterator function
    local i = 0
    return function()
        i = i + 1
        if keys[i] then
            return keys[i], t[keys[i]]
        end
    end
end

function Iter.top(t, stop)
    local start = #t
    stop = stop or 1

    return function()
        if start >= stop and t[start] ~= nil then
            local cur = start
            start = start - 1
            return cur, t[cur]
        end
        return nil
    end
end

function Iter.wrap(t, start, reverse)
    --[[
    -- Returns an iterator that iterates over integer keys in table `t` from the specified start position, wrapping
    -- around and ending when it reaches `start` again.
    --
    -- `dir` specifies the direction to iterate (negative values for reverse, otherwise forward)
    -- `start` specifies the start location.  If `nil`, the first returned item will be at the at the start of the table
    -- (or the end of the table, if `dir` is negative)
    --
    -- Behavior if the table changes size during iteration is undefined.
     ]]
    local dir = (reverse and -1) or 1
    local len = #t
    local i = start
    start = start or (reverse and len) or 1

    return function()
        if i == nil then
            i = start
            return i, t[i]
        end

        i = i + dir
        if i < 1 then
            i = i + len
        elseif i > len then
            i = i - len
        end

        if i == start then
            return nil
        end
        return i, t[i]
    end
end

function Iter.tpairs(...)
    return ipairs(type(...) == 'table' and ... or {...})
end

return Iter
