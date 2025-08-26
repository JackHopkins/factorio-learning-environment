local M = {}

M.events = {}

M.actions = {}

M.actions.sleep = function(ticks_elapsed)
    if ticks_elapsed > 0 then
        global.elapsed_ticks = global.elapsed_ticks + ticks_elapsed
    end
    return game.tick
end

return M
