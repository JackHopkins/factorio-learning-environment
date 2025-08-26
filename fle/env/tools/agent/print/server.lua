local M = {}

M.events = {}

M.actions = {}

M.actions.print = function(message)
    message = dump(message)
    return '"'..message..'"'
end

return M
