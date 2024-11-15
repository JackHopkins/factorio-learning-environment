--- A collection library to simplify sequential table operations
--
--    local Enumerable = require('__stdlib__/stdlib/vendor/enumerable')
--    Enumerable.create({1,2,3})
-- @classmod Vendor.Enumerable
-- @author Billiam
local Enumerable = {}
Enumerable.mt = {
  __index = function(self, key)
    return Enumerable[key] or self._data[key]
  end
}

--- Tests tables for numeric keys with no gaps
-- @tparam table t Table to check
-- @treturn boolean True if table is sequence-like, false otherwise
local function isSequence(t)
  local i = 0
  for _ in pairs(t) do
     i = i + 1
     if t[i] == nil then return false end
  end
  return true
end

--- Whether the item passed in may be called as a function
-- @param f Item to test for callability
-- @treturn boolean True if passed in item may be called, false otherwise
local function isCallable(f)
  local t = type(f)

  if t == 'function' then
    return true
  end

  if t == 'table' then
    local meta = getmetatable(f)

    return meta and type(meta.__call) == 'function'
  end

  return false
end

--- Enumerable constructor.
-- If no collection is provided, a new empty table will be generated.
--
-- @usage
--  collection = Enumerable.create({123})
-- @tparam ?table collection Sequential table to wrap
-- @treturn enumerable A new collection instance
-- @raise 'Enumerable data must be a sequence' if given a non-sequential table
function Enumerable.create(collection)
  if collection and not (type(collection) == 'table' and isSequence(collection)) then
    error('Enumerable data must be a sequence')
  end

  local instance = {
    --- Internal collection data
    -- @table _data
    _data = collection or {}
  }

  setmetatable(instance, Enumerable.mt)

  return instance
end

--- Return the unwrapped collection data.
-- @usage
--  collectionData = collection:to_table()
-- @treturn table
function Enumerable:data()
  return self._data
end

--- Create a shallow copy of the unwrapped collection data.
-- @usage
--  clonedData = collection:to_table()
-- @treturn table
function Enumerable:to_table()
  local meta = getmetatable(self._data)
  local target = {}

  for k, v in pairs(self._data) do target[k] = v end
  setmetatable(target, meta)
  return target
end

--- Pass all elements in the collection to a callback.
-- @usage
--  collection:each(function(value, index) ... end)
-- @tparam callable callback
-- @treturn enumerable The collection instance
function Enumerable:each(callback)
  for i,v in ipairs(self._data) do
    callback(v, i)
  end

  return self
end

--- Pass all elements in collection to a callback.
-- returns a new enumerable instance containing values
-- returned by the callback.
-- @usage
--  collection = Enumerable.create({1, 2, 3})
--  collection:map(function(value, index) return value* 2 end)
-- -> Enumerable containing {2, 4, 6}
-- @tparam callable callback
-- @treturn enumerable New enumerable instance
function Enumerable:map(callback)
  local map = {}

  for i,v in ipairs(self._data) do
    local result = callback(v, i)
    if result ~= nil then
      table.insert(map, result)
    end
  end
  return Enumerable.create(map)
end

--- Find the position of the first item in collection for which
-- the callback returns true.
-- @usage
--  collection = Collection.create({0, 1, 2, 3, 4})
--  collection:findIndex(function(value, index) return value > 2 end)
--  -> 4
-- @tparam callable callback
-- @treturn int the position of the matched element
function Enumerable:find_index(callback)
  for i,v in ipairs(self._data) do
    if callback(v, i) then
      return i
    end
  end
end

--- Whether the collection has no elements.
-- @usage collection = Enumerable.create()
--  if collection:empty() then
--    print('Collection is empty')
--  end
--  -> Collection is empty
-- @treturn bool
function Enumerable:empty()
  return #self._data == 0
end

--- Return the first element or elements in the collection.
-- @see Enumerable:last
-- @usage
--  collection = Enumerable.create({1,2,3,4})
--  collection:first()
--  -> 1
--  collection:first(3)
--  -> {1,2,3}
-- @tparam ?int n Number of elements to return. If absent, the first item will be returned.
-- @treturn table|*
function Enumerable:first(n)
  if not n or n == 1 then
    return self._data[1]
  end

  local list = {}

  n = math.min(n, #self._data)
  for i=1,n do
    table.insert(list, self._data[i])
  end

  return list
end

--- Return the last element or elements in the collection.
-- @see Enumerable:first
-- @usage
--  collection = Enumerable.create({1,2,3,4})
--  collection:last()
--  -> 4
--  collection:last(3)
--  -> {2, 3, 4}
-- @tparam ?int n Number of elements to return. If absent, the last item will be returned.
-- @treturn table
function Enumerable:last(n)
  if not n or n == 1 then
    return self._data[#self._data]
  end

  local list = {}

  n = math.max(1, #self._data - (n - 1))
  for i=n,#self._data do
    table.insert(list, self._data[i])
  end

  return list
end

--- Return the number of items in the collection.
-- If a callback is given, count will return the
-- number of elements for which the callback returns true
-- @usage
--  collection = Enumerable.create({1,2,3})
--  collection:count()
--  -> 3
--  collection:count(function(value, index) return value % 2 == 0 end)
--  -> 1
-- @tparam callable callback Callback used to determine whether element should be counted
-- @treturn int
function Enumerable:count(callback)
  if not callback then
    return #self._data
  end

  local count = 0

  for i,v in ipairs(self._data) do
    if callback(v, i) then
      count = count + 1
    end
  end

  return count
end

--- Append the contents of one table onto the end of the existing enumerable.
-- @usage
--  pets = Enumerable:create({'dog', 'cat'})
--  pets:concat({'turtle', 'wizard'})
--  -> pets now contains {'dog', 'cat', 'turtle', 'wizard'}
-- @tparam table other Table with content to append to enumerable
-- @treturn enumerable The enumerable instance
function Enumerable:concat(other)
  return self:push(unpack(other))
end

--- Combine elements of enumerable by passing all items to a callback.
-- Values returned by the callback will be used as the accumulator value
-- for subsequent callbacks.
-- @usage
--  numbers = Enumerable.create({1,2,3})
--  numbers:reduce(function(accumulator, value) return (accumulator or 0) + value end)
--  -> 6
--  numbers:reduce(20, function(accumulator, value) return accumulator + value end)
--  -> 26
-- @tparam ?int initial Initial value for accumulator
-- @tparam callable callback
-- @return Accumulator value
function Enumerable:reduce(initial, callback)
  if not callback then
    if isCallable(initial) then
      callback = initial
      initial = nil
    else
      error('Callback must be a function or table with a __call metamethod')
    end
  end

  local reduce = initial

  for i,v in ipairs(self._data) do
    reduce = callback(reduce, v, i)
  end

  return reduce
end

--- Find the lowest value in the enumerable instance.
-- If a callback is provided, the return value will be used
-- to determine the lowest value.
-- @usage
--  strings = Enumerable.create({'aaaaaa', 'bbb', 'c'})
--  strings:min()
-- -> 'aaaaa'
--  strings:min(function(value) return #value end)
-- -> 'c'
-- @tparam ?callable callback
-- @return Lowest value
function Enumerable:min(callback)
  callback = callback or function(v) return v end

  local lowestValue

  return self:reduce(function(output, v)
    local result = callback(v)

    if not output or (result and result < lowestValue) then
      lowestValue = result
      return v
    end

    return output
  end)
end

--- Find the highest value in the enumerable instance.
-- If a callback is provided, the return value will be used
-- to determine the highest value.
-- @usage
--  strings = Enumerable.create({'aaaaaa', 'bbb', 'c'})
--  strings:max()
-- -> 'c'
--  strings:max(function(value) return #value end)
-- -> 'aaaaa'
-- @tparam ?callable callback
-- @return Highest value
function Enumerable:max(callback)
  callback = callback or function(v) return v end

  local highestValue

  return self:reduce(function(output, v)
    local result = callback(v)

    if not output or (result and result > highestValue) then
      highestValue = result
      return v
    end

    return output
  end)
end

--- Find the highest and lowest values in the enumerable.
-- If a callback is provided, the return value will be used
-- to determine the highest and lowest values.
-- @usage
--  numbers = Enumerable.create({6,3,1,5,2,4})
--  lowest, highest = numbers:minmax()
-- -> (1,6)
--  strings:max(function(value) return 10 - value end)
-- -> (6, 1)
-- @tparam ?callable callback
-- @return Lowest value
-- @return Highest value
function Enumerable:minmax(callback)
  return self:min(callback), self:max(callback)
end

--- Sort the enumerable by optional callback in place.
-- If a callback is not provided, data will be sorted in ascending order.
-- If callback is provided, it will be passed two table elements, and should
-- return true if the first element should appear first, otherwise false.
-- See also: [table.sort documentation](http://www.lua.org/manual/5.1/manual.html#pdf-table.sort)
-- @usage
--  numbers = Enumerable.create({2,1,3})
--  numbers:sort()
--  -> numbers now contains {1,2,3}
--  numbers:sort(function(a, b) return b < a end)
--  -> numbers now contains {3,2,1}
-- @tparam ?callable callback sort method
-- @treturn enumerable The collection instance
function Enumerable:sort(callback)
  table.sort(self._data, callback)

  return self
end

--- Add one or more items to the enumerable.
-- @usage
--  items = Enumerable.create({1,2,3})
--  items:push(4, 5)
-- -> items contains {1,2,3,4,5}
-- @param ... Items to append
-- @treturn enumerable The collection instance
function Enumerable:push(...)
  for i,v in ipairs({...}) do
    table.insert(self._data, v)
  end

  return self
end

--- Remove and return the last item from the collection.
-- @usage
--  items = Enumerable.create({1,2,3})
--  items:pop()
-- -> returns 3
-- -> items now contains {1,2}
-- @treturn enumerable The collection instance
function Enumerable:pop()
  return table.remove(self._data, #self._data)
end

--- Remove and return the first item from the collection.
-- @usage
--  items = Enumerable.create({1,2,3})
--  items:shift()
-- -> returns 1
-- -> items now contains {2,3}
-- @treturn enumerable The collection instance
function Enumerable:shift()
  return table.remove(self._data, 1)
end

--- Insert one or more items into the beginning of the collection.
-- @usage
--  items = Enumerable.create({4,5,6})
--  items:unshift(1,2,3)
--  -> Items now contains {1,2,3,4,5,6}
-- @param ... Elements to insert
-- @treturn enumerable The collection instance
function Enumerable:unshift(...)
  for i,v in ipairs({...}) do
    table.insert(self._data, i, v)
  end

  return self
end

--- Returns the first element in the collection where the callback returns true.
-- @usage
--  numbers = Enumerable.create({20, 30, 40})
--  numbers:find(function(value, index) return value > 25 end)
--  -> 30
-- @tparam callable callback
-- @return Matching item
function Enumerable:find(callback)
  for i,v in ipairs(self._data) do
    if callback(v, i) then
      return v
    end
  end
end

--- Create a new collection with elements which the callback returns false.
-- @usage
--  items = Enumerable.create({1,2,3,4,5,6})
--  odd = Enumerable:reject(function(value, index) return value % 2 == 0 end)
--  -> Enumerable containing {1,3,5}
-- @tparam callable callback
-- @treturn enumerable New collection instance
function Enumerable:reject(callback)
  local reject = {}

  for i,v in ipairs(self._data) do
    if not callback(v, i) then
      table.insert(reject, v)
    end
  end

  return Enumerable.create(reject)
end

--- Create a new collection with elements which the callback returns true.
-- @usage
--  items = Enumerable.create({1,2,3,4,5,6})
--  even = Enumerable:select(function(value, index) return value % 2 == 0 end)
--  -> Enumerable containing {2,4,6}
-- @tparam callable callback
-- @treturn enumerable New collection instance
-- @alias find_all
function Enumerable:select(callback)
  local select = {}

  for i,v in ipairs(self._data) do
    if callback(v, i) then
      table.insert(select, v)
    end
  end

  return Enumerable.create(select)
end

--- Returns true if callback returns truthy for all elements in the collection.
-- @usage
--  items = Enumerable.create({10, 20, 30})
--  items:all(function(value, index) return value > 5 end)
--  -> true
--  items:all(function(value, index) return value < 25 end)
--  -> false
-- @tparam callable callback
-- @treturn bool
function Enumerable:all(callback)
  for i,v in ipairs(self._data) do
    if not callback(v, i) then
      return false
    end
  end

  return true
end


--- Returns true if callback returns truthy for any element in the collection.
-- @usage
--  items = Enumerable.create({10, 20, 30})
--  items:any(function(value, index) return value > 25 end)
--  -> true
--  items:any(function(value, index) return value > 30 end)
--  -> false
-- @tparam callable callback
-- @treturn bool
function Enumerable:any(callback)
  for i,v in ipairs(self._data) do
    if callback(v, i) then
      return true
    end
  end

  return false
end

--- Groups elements into collections based on the result of the provided callback.
-- Resulting table will have keys matching the returned value of the callback, and
-- values as a table of elements which returned that value.
-- @usage
--  numbers = Enumerable.create({1,2,3,4,5,6})
--  result = Enumerable.group_by(function(value, index) return value % 3 end)
--  result[0]
--  -> Enumerable containing {3, 6}
--  result[1]
--  -> Enumerable containing {2, 5}
--  result[2]
--  -> Enumerable containing {1, 4}
-- @tparam callable callback
-- @treturn table
function Enumerable:group_by(callback)
  local groups = {}

  for i,v in ipairs(self._data) do
    local criteria = callback(v, i)

    groups[criteria] = groups[criteria] or Enumerable.create()

    groups[criteria]:push(v)
  end

  return groups
end

--- Split enumerable into two groups, based on the true or false result of the callback.
--
-- Aliases: find_all, detect
--
-- @usage
--  numbers = Enumerable.create({1,2,3,4,5,6})
-- even, odd = Enumerable:partition(function(value, index) return value % 2 == 1 end)
-- -> even is a collection containing {2, 4, 6}
-- -> odd is a collection containing {1, 3, 5}
-- @tparam callable callback
-- @treturn enumerable Collection containing items which returned true
-- @treturn enumerable Collection containing items which returned false
function Enumerable:partition(callback)
  local truthyCallback = function(v, i)
    return callback(v, i) and true or false
  end

 local results = self:group_by(truthyCallback)

 return results[true] or Enumerable.create(), results[false] or Enumerable.create()
end

---
-- @function Enumerable:find_all
-- @see Enumerable:select
Enumerable.find_all = Enumerable.select

---
-- @function Enumerable:detect
-- @see Enumerable:select
Enumerable.detect = Enumerable.select

---
-- @function Enumerable:collect
-- @see Enumerable:map
Enumerable.collect = Enumerable.map

---
-- @function Enumerable:inject
-- @see Enumerable:reduce
Enumerable.inject = Enumerable.reduce

return Enumerable
