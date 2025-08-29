local M = {}

function M.initialise()
    --- initialise.lua
    --- This file is used to initialise the global variables and functions.
    --- Ensure this is loaded first. Any variables or functions defined here will be available to all other scripts.

    if not actions then
        --- @type table Actions table
        actions = {}
    end

    if not utils then
        --- @type table Utils table
        utils = {}
    end

    if not global.initial_score then
        --- @type table Initial score table
        global.initial_score = { ["player"] = 0 }
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
        --- @type table<number, LuaEntity> Agent characters table mapping agent index to LuaEntity
        global.agent_characters = {}
    end

    if not global.paths then
        --- @type table<number, table<string, any>> Paths table mapping agent index to path data
        global.paths = {}
    end

    if not global.path_requests then
        global.path_requests = {}
    end

    if not global.harvested_items then
        global.harvested_items = {}
    end

    if not global.crafted_items then
        global.crafted_items = {}
    end

    if not global.walking_queues then
        global.walking_queues = {}
    end

    if not global.goal then
        global.goal = nil
    end

    -- initialise debug flags
    if global.debug == nil then
        global.debug = {
            rendering = false -- Flag to toggle debug rendering of polygons and shapes
        }
    end

    if not global.clearance_entities then
        global.clearance_entities = {}
    end
end

return M
