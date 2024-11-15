--- A double queue.
-- Taken from ***Programming in Lua*** [Queues and Double Queues](http://www.lua.org/pil/11.4.html)
-- and modified to not allow nil values, and returns nil if @{pop_first} or @{pop_last} is used when the queue is empty.
-- @module Misc.Queue
-- @usage local Queue = require('__stdlib__/stdlib/lists/queue')
-- local q = Queue() -- create a new empty queue
-- q('my value') -- push a value onto the queue
-- q() -- pop the last value off the queue
-- game.print(#q) -- print the number of items in the queue

local Queue = {
    __class = 'Queue',
    __index = require('__stdlib__/stdlib/core')
}
setmetatable(Queue, Queue)

local table = require('__stdlib__/stdlib/utils/table')
local t_size = table_size

local Inspect = require('__stdlib__/stdlib/vendor/inspect')

local meta = {}

function Queue.__call(_, ...)
    local queue = {first = 1, last = 0, objects = {}}
    setmetatable(queue, meta)
    for _, push in pairs({...}) do
        queue(push)
    end
    return queue
end

--- Constructs a new Queue object.
-- @param ... mixed, values to push into the queue
-- @treturn @{Queue} a new queue
function Queue.new(...)
    return Queue.__call(nil, ...)
end

--- Load global.queue or queues during on_load, as metatables are not persisted.
-- <p>This is only needed if you are using the queue as an object and storing it in global.
-- @tparam table queue (<span class="types">@{Queue}</span>,...)
-- @usage global.myqueue1 = Queue.new()
-- script.on_load(function() Queue.load(global.myqueue))
function Queue.load(queue)
    if type(queue) == 'table' and queue.first then
        return setmetatable(queue, meta)
    end
end

--- Push a new element to the front of the queue.
-- @tparam Queue queue the queue to push an element to
-- @tparam Mixed value the element to push
function Queue.push_first(queue, ...)
    for _, value in pairs({...}) do
        queue.first = queue.first - 1
        queue.objects[queue.first] = value
    end
    return queue
end

--- Push a new element to the back of the queue.
-- @tparam Queue queue the queue to push an element to
-- @tparam Mixed ... the element(s) to push
function Queue.push_last(queue, ...)
    for _, value in pairs({...}) do
        queue.last = queue.last + 1
        queue.objects[queue.last] = value
    end
    return queue
end

--- Shortcut for @{Queue.push_last}
-- @function Queue.push
Queue.push = Queue.push_last

--- Push a new element to a specific location of the queue.
-- @tparam Queue queue the queue to push an element to
-- @tparam number index the index to push to.
-- @tparam Mixed value the element to push.
function Queue.push_at(queue, index, value)
    if index < queue.first then
        return Queue.push_first(queue, value)
    elseif index > queue.last then
        return Queue.push_last(queue, value)
    else
        table.insert(queue.objects, index, value)
        queue.last = queue.last + 1
    end
    return queue
end

function Queue.wrapper(self, func_name, ...)
    if Queue[func_name] then
        Queue[func_name](self, ...)
    end
    return self
end

--- Retrieve the element at the front of the queue and remove it from the queue.
-- @tparam Queue queue the queue to retrieve the element from
-- @treturn Mixed value the element at the front of the queue
function Queue.pop_first(queue)
    if Queue.is_empty(queue) then
        return nil
    end
    local first = queue.first
    local value = queue.objects[first]
    queue.objects[first] = nil -- to allow garbage collection
    queue.first = first + 1
    return value
end

--- Shortcut for @{Queue.pop_first}
-- @function Queue.pop
Queue.pop = Queue.pop_first

local function remove(queue, index)
    local ret = queue.objects[index]
    if ret ~= nil then
        for i = index + 1, queue.last do
            queue.objects[i - 1] = queue.objects[i]
        end
        queue.objects[queue.last] = nil
        queue.last = queue.last - 1
    end
    return ret
end

--- Pop an element at a specific location of the queue.
-- @tparam Queue queue the queue to push an element to
-- @tparam number index the index to push to.
-- @treturn Mixed value the popped element.
function Queue.pop_at(queue, index)
    return remove(queue, index)
end

--- Peek at an element in the queue without disturbing the queue.
-- @tparam Queue queue the queue to peek at
-- @tparam number index the index in the queue to peek at
-- @treturn Mixed the value of the peeked element
function Queue.peek_at(queue, index)
    return queue.objects[index]
end

--- Return the element at the front of the queue and remove it from the queue.
-- @tparam Queue queue the queue to retrieve the element from
-- @treturn Mixed the element at the front of the queue
function Queue.peek_first(queue)
    return queue.objects[queue.first]
end

--- Shortcut for @{Queue.peek_first}
-- @function Queue.peek
Queue.peek = Queue.peek_first

--- Retrieve the element at the back of the queue and remove it from the queue.
-- @tparam Queue queue the queue to retrieve the element from
-- @treturn Mixed the element at the back of the queue
function Queue.pop_last(queue)
    if queue.is_empty(queue) then
        return nil
    end

    local last = queue.last
    local value = queue.objects[last]
    queue.objects[last] = nil -- to allow garbage collection
    queue.last = last - 1
    return value
end

--- Return the element at the back of the queue.
-- @tparam Queue queue the queue to retrieve the element from
-- @treturn Mixed the element at the back of the queue
function Queue.peek_last(queue)
    return queue.objects[queue.last]
end

--- Returns the popped value and pushes back into the queue.
-- @tparam Queue queue the queue
-- @return Mixed the value that was popped.
function Queue.pop_and_push(queue)
    local ret = queue.pop(queue)
    queue.push(queue, ret)
    return ret
end

--- Returns the queue after popping the last element and pushing it to the top.
-- @tparam Queue queue the queue
-- @treturn @{Queue} the queue
function Queue.cycle(queue)
    return queue.push(queue, queue.pop(queue))
end

--- Gets the first index which matches the stored data. does not compare inside tables.
function Queue.find(queue, find)
    for i, v in pairs(queue) do
        if v == find then
            return i
        end
    end
end

local function _sort_func(a, b)
    local lhs = type(a) == 'table' and '{' or tostring(a)
    local rhs = type(b) == 'table' and '{' or tostring(b)
    return lhs < rhs
end

--- sort and reorder the queue
function Queue.sort(queue, func)
    local sorted = {}
    for _, v in pairs(queue) do
        if v ~= nil then
            sorted[#sorted + 1] = v
        end
    end
    table.sort(sorted, func or _sort_func)
    queue.objects = sorted
    queue.first, queue.last = 1, #queue.objects
    return queue
end

--- Returns true if the given queue is empty.
-- @tparam Queue queue the queue to check
-- @treturn boolean true if empty, false otherwise
function Queue.is_empty(queue)
    return queue.first > queue.last
end

--- Returns the number of items in the queue.
-- @tparam Queue queue the queue to check
-- @treturn number the number of items in the queue
function Queue.size(queue)
    return t_size(queue.objects)
end

--- Shortcut for @{Queue.size}
-- @function Queue.count
Queue.count = Queue.size

--- Return the next element in the queue
-- @tparam Queue queue the queue to check
-- @tparam number|nil index if nil return the first value, else return the next index value
-- @tparam boolean pop pop the value off the queue
-- @treturn number|nil the index
-- @treturn Mixed|nil the value at queue index
function Queue.next(queue, index, pop)
    index = not index and queue.first or index + (pop and 0 or 1)
    for i = index, queue.last do
        local v = queue.objects[i]
        if v ~= nil then
            return i, pop and Queue.pop_at(queue, i) or v
        end
    end
    return nil, nil
end

--- Return the previous element in the queue
-- @tparam Queue queue the queue to check
-- @tparam number|nil index if nil return the last value, else return the previous index value
-- @tparam boolean pop pop the value off the queue
-- @treturn number|nil the index
-- @treturn Mixed|nil the value at queue index
function Queue.rnext(queue, index, pop)
    -- next returns index of next or nil and data,
    index = not index and queue.last or (index < queue.first and queue.first or index) - 1
    for i = index, queue.first, -1 do
        local v = queue.objects[i]
        if v ~= nil then
            return i, pop and Queue.pop_at(queue, i) or v
        end
    end
    return nil, nil
end

local function next_pop(queue, index)
    return Queue.next(queue, index, true)
end

local function rnext_pop(queue, index)
    return Queue.rnext(queue, index, true)
end

--- Iterate the queue forward
function Queue.pairs(queue, pop)
    return pop and next_pop or Queue.next, queue, nil
end

--- Iterate the queue backwards
function Queue.rpairs(queue, pop)
    return pop and rnext_pop or Queue.rnext, queue, nil
end

do
    meta.__class = 'queue'
    meta.__len = Queue.size
    meta.__unm = Queue.pop
    meta.__parent = Queue
    meta.__debugline = [[<Queue>{[}first={first},last={last}{]}]]

    -- Allows queue[3] to return the item at queue.objects[3]
    meta.__index = function(self, k)
        if type(k) == 'number' then
            return self:peek_at(k)
        else
            local v = rawget(self, k)
            if v == nil then
                return Queue[k]
            end
            return v
        end
    end

    meta.__newindex = function(self, k, v)
        if type(k) == 'number' then
            if v ~= nil then
                self:push_at(k, v)
            else
                error('Attempt to modify Queue structure')
            end
        else
            rawset(self, k, v)
        end
    end

    -- Allows queue() to pop_first and queue(data) to push_last
    meta.__call = function(self, ...)
        if ... then
            return self:push(...)
        else
            return self:pop()
        end
    end

    meta.__tostring = function(self)
        return Inspect({first = self.first, last = self.last, objects = self.objects}, {arraykeys = true})
    end

    meta.__add = function(queue1, queue2)
        local new = Queue.new()
        local lhs = getmetatable(queue1) == meta and true
        local rhs = getmetatable(queue2) == meta and true
        if lhs then
            for _, v in pairs(queue1.objects) do
                new:push(v)
            end
        else
            new:push(queue1)
        end
        if rhs then
            for _, v in pairs(queue2.objects) do
                new:push(v)
            end
        else
            new:push(queue2)
        end
        return new
    end
end

return Queue
