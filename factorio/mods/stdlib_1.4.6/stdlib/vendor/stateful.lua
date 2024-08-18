local Stateful = {
  _VERSION     = 'Stateful 1.0.5 (2017-08)',
  _DESCRIPTION = 'Stateful classes for middleclass',
  _URL         = 'https://github.com/kikito/stateful.lua',
  _LICENSE     = [[
    MIT LICENSE

    Copyright (c) 2017 Enrique García Cota

    Permission is hereby granted, free of charge, to any person obtaining a
    copy of this software and associated documentation files (the
    "Software"), to deal in the Software without restriction, including
    without limitation the rights to use, copy, modify, merge, publish,
    distribute, sublicense, and/or sell copies of the Software, and to
    permit persons to whom the Software is furnished to do so, subject to
    the following conditions:

    The above copyright notice and this permission notice shall be included
    in all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
    OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
    MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
    IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
    CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
    TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
    SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
  ]]
}

-- requires middleclass >2.0
Stateful.static = {}

local _callbacks = {
  enteredState = 1,
  exitedState = 1,
  pushedState = 1,
  poppedState = 1,
  pausedState = 1,
  continuedState = 1
}

local _BaseState = {}

local function _addStatesToClass(klass, superStates)
  klass.static.states = {}
  for stateName, state in pairs(superStates or {}) do
    klass:addState(stateName,state)
  end
end

local function _getStatefulMethod(instance, name)
  if not _callbacks[name] then
    local stack = rawget(instance, '__stateStack')
    if not stack then return end
    for i = #stack, 1, -1 do
      if stack[i][name] then return stack[i][name] end
    end
  end
end

local function _getNewInstanceIndex(prevIndex)
  if type(prevIndex) == 'function' then
    return function(instance, name) return _getStatefulMethod(instance, name) or prevIndex(instance, name) end
  end
  return function(instance, name) return _getStatefulMethod(instance, name) or prevIndex[name] end
end

local function _getNewAllocateMethod(oldAllocateMethod)
  return function(klass, ...)
    local instance = oldAllocateMethod(klass, ...)
    instance.__stateStack = {}
    return instance
  end
end

local function _modifyInstanceIndex(klass)
  klass.__instanceDict.__index = _getNewInstanceIndex(klass.__instanceDict.__index)
end

local function _getNewSubclassMethod(prevSubclass)
  return function(klass, name)
    local subclass = prevSubclass(klass, name)
    _addStatesToClass(subclass, klass.states)
    _modifyInstanceIndex(subclass)
    return subclass
  end
end

local function _modifySubclassMethod(klass)
  klass.static.subclass = _getNewSubclassMethod(klass.static.subclass)
end

local function _modifyAllocateMethod(klass)
  klass.static.allocate = _getNewAllocateMethod(klass.static.allocate)
end

local function _assertType(val, name, expected_type, type_to_s)
  if type(val) ~= expected_type then
    error("Expected " .. name .. " to be of type " ..
          (type_to_s or expected_type) .. ". Was " ..
          tostring(val) .. "(" .. type(val) .. ")")
  end
end

local function _assertInexistingState(klass, stateName)
  if klass.states[stateName] ~= nil then
    error("State " .. tostring(stateName) .. " already exists on " .. tostring(klass) )
  end
end

local function _assertExistingState(self, state, stateName)
  if not state then
    error("The state " .. stateName .. " was not found in " .. tostring(self.class))
  end
end

local function _invokeCallback(self, state, callbackName, ...)
  if state and state[callbackName] then state[callbackName](self, ...) end
end

local function _getCurrentState(self)
  return self.__stateStack[#self.__stateStack]
end

local function _getStateFromClassByName(self, stateName)
  local state = self.class.static.states[stateName]
  _assertExistingState(self, state, stateName)
  return state
end

local function _getStateIndexFromStackByName(self, stateName)
  if stateName == nil then return #self.__stateStack end
  local target = _getStateFromClassByName(self, stateName)
  for i = #self.__stateStack, 1, -1 do
    if self.__stateStack[i] == target then return i end
  end
end

local function _getStateName(self, target)
  for name,state in pairs(self.class.static.states) do
    if state == target then return name end
  end
end

function Stateful:included(klass) --luacheck: ignore 212
  _addStatesToClass(klass)
  _modifyInstanceIndex(klass)
  _modifySubclassMethod(klass)
  _modifyAllocateMethod(klass)
end

function Stateful.static:addState(stateName, superState)
  superState = superState or _BaseState
  _assertType(stateName, 'stateName', 'string')
  _assertInexistingState(self, stateName)
  self.static.states[stateName] = setmetatable({}, { __index = superState })
  return self.static.states[stateName]
end

function Stateful:gotoState(stateName, ...)

  self:popAllStates(...)

  if stateName == nil then
    self.__stateStack = { }
  else
    _assertType(stateName, 'stateName', 'string', 'string or nil')

    local newState = _getStateFromClassByName(self, stateName)
    self.__stateStack = { newState }
    _invokeCallback(self, newState, 'enteredState', ...)
  end

end

function Stateful:pushState(stateName,...)
  local oldState = _getCurrentState(self)
  _invokeCallback(self, oldState, 'pausedState')

  local newState = _getStateFromClassByName(self, stateName)
  table.insert(self.__stateStack, newState)

  _invokeCallback(self, newState, 'pushedState',...)
  _invokeCallback(self, newState, 'enteredState',...)
end

function Stateful:popState(stateName, ...)

  local oldStateIndex = _getStateIndexFromStackByName(self, stateName)
  local oldState
  if oldStateIndex then
    oldState = self.__stateStack[oldStateIndex]

    _invokeCallback(self, oldState, 'poppedState', ...)
    _invokeCallback(self, oldState, 'exitedState', ...)

    table.remove(self.__stateStack, oldStateIndex)
  end

  local newState = _getCurrentState(self)

  if oldState ~= newState then
    _invokeCallback(self, newState, 'continuedState', ...)
  end
end

function Stateful:popAllStates(...)
  local size = #self.__stateStack
  for _=1,size do self:popState(nil, ...) end
end

function Stateful:getStateStackDebugInfo()
  local info = {}
  local state
  for i=#self.__stateStack,1,-1 do
    state = self.__stateStack[i]
    table.insert(info, _getStateName(self, state))
  end
  return info
end

return Stateful
