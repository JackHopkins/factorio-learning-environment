-- beholder.lua - v2.1.1 (2011-11)

-- Copyright (c) 2011 Enrique García Cota
-- Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
-- The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
-- THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN callback OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

local function copy(t)
  local c={}
  for i=1,#t do c[i]=t[i] end
  return c
end

local function hash2array(t)
  local arr, i = {}, 0
  for _,v in pairs(t) do
    i = i+1
    arr[i] = v
  end
  return arr, i
end
-- private Node class

local nodesById = nil
local root = nil

local function newNode()
  return { callbacks = {}, children = setmetatable({}, {__mode="k"}) }
end


local function findNodeById(id)
  return nodesById[id]
end

local function findOrCreateChildNode(self, key)
  self.children[key] = self.children[key] or newNode()
  return self.children[key]
end

local function findOrCreateDescendantNode(self, keys)
  local node = self
  for i=1, #keys do
    node = findOrCreateChildNode(node, keys[i])
  end
  return node
end

local function invokeNodeCallbacks(self, params)
  -- copy the hash into an array, for safety (self-erasures)
  local callbacks, count = hash2array(self.callbacks)
  for i=1,#callbacks do
    callbacks[i](unpack(params))
  end
  return count
end

local function invokeAllNodeCallbacksInSubTree(self, params)
  local counter = invokeNodeCallbacks(self, params)
  for _,child in pairs(self.children) do
    counter = counter + invokeAllNodeCallbacksInSubTree(child, params)
  end
  return counter
end

local function invokeNodeCallbacksFromPath(self, path)
  local node = self
  local params = copy(path)
  local counter = invokeNodeCallbacks(node, params)

  for i=1, #path do
    node = node.children[path[i]]
    if not node then break end
    table.remove(params, 1)
    counter = counter + invokeNodeCallbacks(node, params)
  end

  return counter
end

local function addCallbackToNode(self, callback)
  local id = {}
  self.callbacks[id] = callback
  nodesById[id] = self
  return id
end

local function removeCallbackFromNode(self, id)
  self.callbacks[id] = nil
  nodesById[id] = nil
end


-- beholder table

local beholder = {}


-- beholder private functions/vars

local groups = nil
local currentGroupId = nil

local function addIdToCurrentGroup(id)
  if currentGroupId then
    groups[currentGroupId] = groups[currentGroupId] or setmetatable({}, {__mode="k"})
    local group = groups[currentGroupId]
    group[#group + 1] = id
  end
  return id
end

local function stopObservingGroup(group)
  local count = #group
  for i=1,count do
    beholder.stopObserving(group[i])
  end
  return count
end

local function falseIfZero(n)
  return n > 0 and n
end

local function extractEventAndCallbackFromParams(params)
  assert(#params > 0, "beholder.observe requires at least one parameter - the callback. You usually want to use two, i.e.: beholder.observe('EVENT', callback)")
  local callback = table.remove(params, #params)
  return params, callback
end


-- Public interface

function beholder.observe(...)
  local event, callback = extractEventAndCallbackFromParams({...})
  local node = findOrCreateDescendantNode(root, event)
  return addIdToCurrentGroup(addCallbackToNode(node, callback))
end

function beholder.stopObserving(id)
  local node = findNodeById(id)
  if node then removeCallbackFromNode(node, id) end

  local group, count = groups[id], 0
  if group then count = stopObservingGroup(group) end

  return (node or count > 0) and true or false
end

function beholder.group(groupId, f)
  assert(not currentGroupId, "beholder.group can not be nested!")
  currentGroupId = groupId
  f()
  currentGroupId = nil
end

function beholder.trigger(...)
  return falseIfZero( invokeNodeCallbacksFromPath(root, {...}) )
end

function beholder.triggerAll(...)
  return falseIfZero( invokeAllNodeCallbacksInSubTree(root, {...}) )
end

function beholder.reset()
  root = newNode()
  nodesById = setmetatable({}, {__mode="k"})
  groups = {}
  currentGroupId = nil
end

beholder.reset()

return beholder
