--- initialise.lua
--- This file is used to initialise the global variables and functions.
--- Ensure this is loaded first. Any variables or functions defined here will be available to all other scripts.

if not storage.actions then
    --- @type table Actions table
    storage.actions = {}
end

if not storage.utils then
    --- @type table Utils table
    storage.utils = {}
end

if not storage.initial_score then
    --- @type table Initial score table
    storage.initial_score = {["player"] = 0}
end

if not storage.alerts then
    --- @type table Alerts table
    storage.alerts = {}
end

if not storage.elapsed_ticks then
    --- @type number The number of ticks elapsed since the game started
    storage.elapsed_ticks = 0
end

if not storage.fast then
    --- @type boolean Flag to use custom FLE fast mode
    storage.fast = false
end

if not storage.agent_characters then
    --- @type table<number, LuaEntity> Agent characters table mapping agent index to LuaEntity
    storage.agent_characters = {}
end

if not storage.paths then
    --- @type table<number, table<string, any>> Paths table mapping agent index to path data
    storage.paths = {}
end

if not storage.path_requests then
    storage.path_requests = {}
end

if not storage.harvested_items then
    storage.harvested_items = {}
end

if not storage.crafted_items then
    storage.crafted_items = {}
end

if not storage.walking_queues then
    storage.walking_queues = {}
end

if not storage.goal then
    storage.goal = nil
end

-- Initialize debug flags
if storage.debug == nil then
    storage.debug = {
        rendering = false -- Flag to toggle debug rendering of polygons and shapes
    }
end

-- Factorio 2.0 compatibility: get_contents() now returns array of {name, count, quality}
-- This wrapper converts to the old format {item_name = count, ...}
storage.utils.get_contents_compat = function(inventory)
    if not inventory then return {} end
    local contents = {}
    for _, item in pairs(inventory.get_contents()) do
        contents[item.name] = (contents[item.name] or 0) + item.count
    end
    return contents
end
