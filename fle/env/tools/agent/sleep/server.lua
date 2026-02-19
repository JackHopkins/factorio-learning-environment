storage.actions.sleep = function(seconds)
    -- Always add ticks as if running at standard 60 ticks/second
    local standard_ticks = seconds * 60
    
    if standard_ticks > 0 then
        storage.elapsed_ticks = storage.elapsed_ticks + standard_ticks
    end
    
    return game.tick
end