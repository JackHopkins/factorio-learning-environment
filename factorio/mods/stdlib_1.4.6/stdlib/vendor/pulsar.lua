-- pulsar.lua - v1.0 (2011-11)
-- Copyright (c) 2011 Enrique García Cota
-- Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
-- The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
-- THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

local Path = {}

local pathmt = {

  __tostring = function(self)

    local buffer = {}
    for i=1,#self do
      buffer[#buffer+1] = tostring(self[i])
    end
    return ("{ %s }"):format(table.concat(buffer, ', '))

  end,

  __eq = function(self, other)

    local myLength, otherLength = #self, #other
    if myLength ~= otherLength then return false end

    for i=1, myLength do
      if self[i] ~= other[i] then return false end
    end

    return true
  end
}

function Path:new(...)
  return setmetatable({...}, pathmt)
end

----------------------------------------------------------------------------

local Node = {}

function Node:new(location, parent, g, h)
  local node = {
    parent = parent,
    location = location,
    g = g,
    h = h,
    f = g + h
  }
  return node
end

----------------------------------------------------------------------------

local Finder = {}
local findermt = { __index = Finder }

local function sortByf(a,b)
  return a.f < b.f
end

local function sortOpenIfNeeded(self)
  if not self.openIsSorted then
    table.sort(self.open, sortByf)
    self.openIsSorted = true
  end
end

local function createNode(self, location, parent, g, h)
  parent = parent or self.bestNode
  local parentLocation = parent and parent.location or self.origin
  g = g or self.cost(parentLocation, location)
  h = h or self.heuristic(parentLocation, location)

  local node = Node:new(location, parent, g, h)
  self.nodes[location] = node
  return node
end

local function checkAndSetParam(finder, value, name)
  assert(value, ("%s expected. Was (%s)"):format(name, tostring(value)))
  finder[name] = value
end

function Finder:findPath()
  local result = Path:new()

  while self.bestLocation ~= self.destination do
    self:findNext()
    table.insert(result, self.bestLocation)
  end

  return result
end

function Finder:findNext()
  local neighbors = self.neighbors(self.bestLocation)
  table.sort(neighbors, self.sort)
  self.bestLocation = neighbors[1]
end

function Finder:getOrCreateNode(location, parent, g, h)
  return self.nodes[location] or createNode(self, location, parent, g, h)
end

function Finder:new(origin, destination, neighbors, cost, heuristic)
  local finder = {}
  checkAndSetParam(finder, origin, "origin")
  checkAndSetParam(finder, destination, "destination")
  checkAndSetParam(finder, neighbors, "neighbors")
  checkAndSetParam(finder, cost, "cost")
  checkAndSetParam(finder, heuristic, "heuristic")

  finder.bestLocation = origin
  finder.sort = function(node1, node2) return heuristic(node1, destination) < heuristic(node2, destination) end

  finder.nodes = {}
  finder.open = {}

  setmetatable(finder, findermt)
  local initialNode = finder:getOrCreateNode(origin, nil, 0, heuristic(origin, destination))
  finder:openNode(initialNode)
  finder.bestNode=initialNode
  return finder
end


function Finder:openNode(node)
  node.open = true
  table.insert(self.open, node)
  self.openIsSorted = false
end

function Finder:closeNode(node)
  node.open = false
end

function Finder:pickNextBestNode()
  sortOpenIfNeeded(self)
  local node = self.open[1]
  if node then
    table.remove(self.open, 1)
    return node
  end
end

function Finder:openNeighbors()
  local neighbors = self.neighbors(self.bestLocation)
  for i=1, #neighbors do
    self:openNode(self:getOrCreateNode(neighbors[i]))
  end
end

----------------------------------------------------------------------------

local pulsar = {}

pulsar.Path = Path
pulsar.Node = Node
pulsar.Finder = Finder


return pulsar
