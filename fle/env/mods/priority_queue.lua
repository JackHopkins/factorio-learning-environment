local PriorityQueue = {}
PriorityQueue.__index = PriorityQueue

-- Create a new PriorityQueue.
function PriorityQueue.new(comparator)
    return setmetatable({queue = {}, comparator = comparator or function(a, b) return a < b end}, PriorityQueue)
end

-- Insert a new element into the queue.
function PriorityQueue:insert(element)
    -- Insert the element at the end of the queue.
    table.insert(self.queue, element)

    -- Bubble up the element to its correct place.
    local i = #self.queue
    while i > 1 do
        local parent = math.floor(i / 2)
        if not self.comparator(self.queue[i], self.queue[parent]) then break end
        self.queue[i], self.queue[parent] = self.queue[parent], self.queue[i]
        i = parent
    end
end

-- Remove and return the top element of the queue.
function PriorityQueue:pop()
    if #self.queue == 0 then error("Queue is empty") end

    local top = self.queue[1]

    -- Replace the root with the last element in the queue.
    self.queue[1] = self.queue[#self.queue]
    table.remove(self.queue)

    -- Bubble down the root element to its correct place.
    local i = 1
    while true do
        local left = 2 * i
        local right = left + 1
        local smallest = i

        if left <= #self.queue and self.comparator(self.queue[left], self.queue[smallest]) then
            smallest = left
        end
        if right <= #self.queue and self.comparator(self.queue[right], self.queue[smallest]) then
            smallest = right
        end
        if smallest == i then break end

        self.queue[i], self.queue[smallest] = self.queue[smallest], self.queue[i]
        i = smallest
    end

    return top
end

-- Check if the queue is empty.
function PriorityQueue:is_empty()
    return #self.queue == 0
end

return PriorityQueue
