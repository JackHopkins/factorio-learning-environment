--- initialise.lua
--- This file is used to initialise the global variables and functions.
--- Ensure this is loaded first. Any variables or functions defined here will be available to all other scripts.

-- If the global actions table doesn't exist, create it
if not global.actions then
    --- @type table Actions table
    global.actions = {}
end

if not global.utils then
    --- @type table Utils table
    global.utils = {}
end

if not global.initial_score then
    --- @type table Initial score table
    global.initial_score = {["player"] = 0}
end

if not global.alerts then
    --- @type table Alerts table
    global.alerts = {}
end

if not global.elapsed_ticks then
    --- @type number The number of ticks elapsed since the game started
    global.elapsed_ticks = 0
end

if not global.fast then
    --- @type boolean Flag to use custom FLE fast mode
    global.fast = false
end

if not global.agent_characters then
    global.agent_characters = {}
end

-- Initialize debug flags
if global.debug == nil then
    global.debug = {
        rendering = false -- Flag to toggle debug rendering of polygons and shapes
    }
end
