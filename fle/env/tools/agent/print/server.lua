local M = {}
M.events = {}

function M.initialize()
global.actions.print = function(message)
    message = dump(message)
    return '"'..message..'"'
end
end

M.initialize()
