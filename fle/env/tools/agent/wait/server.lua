storage.actions.wait = function(ticks)
    if ticks > 0 then
        storage.elapsed_ticks = storage.elapsed_ticks + ticks
    end
    return game.tick
end
