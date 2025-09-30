-- Admin tool to get elapsed ticks
-- This mirrors the get_elapsed_ticks method from FactorioInstance

local function get_elapsed_ticks()
    return global.elapsed_ticks or 0
end

-- Register the action
global.actions.get_elapsed_ticks = get_elapsed_ticks
