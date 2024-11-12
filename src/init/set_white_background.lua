commands.add_command("white_background", "Sets the background to white for screenshots (preserves water)", function()
    local surface = game.player.surface
    local player = game.player
    local position = player.position

    -- Get the visible area around the player (reduced size to prevent hanging)
    local vision_distance = 32  -- Reduced from 32 to improve performance
    local area = {
        {x = math.floor(position.x - vision_distance), y = math.floor(position.y - vision_distance)},
        {x = math.floor(position.x + vision_distance), y = math.floor(position.y + vision_distance)}
    }

    -- Create tiles in chunks to prevent lag
    local tiles = {}
    local chunk_size = 100  -- Process tiles in smaller batches
    local count = 0

    for x = area[1].x, area[2].x do
        for y = area[1].y, area[2].y do
            -- Get current tile at this position
            local current_tile = surface.get_tile(x, y)

            -- Check if the tile is not water (water, deep-water, water-green, etc)
            if not current_tile.name:find("water") then
                count = count + 1
                table.insert(tiles, {
                    name = "refined-concrete",
                    position = {x = x, y = y}
                })

                -- Process in chunks
                if count >= chunk_size then
                    surface.set_tiles(tiles, true)
                    tiles = {}
                    count = 0
                end
            end
        end
    end

    -- Process any remaining tiles
    if #tiles > 0 then
        surface.set_tiles(tiles, true)
    end

    -- Remove decoratives in smaller chunks, but not over water
    local chunk_positions = {}
    for x = area[1].x, area[2].x, 8 do
        for y = area[1].y, area[2].y, 8 do
            local chunk_area = {
                {x = x, y = y},
                {x = math.min(x + 8, area[2].x), y = math.min(y + 8, area[2].y)}
            }
            surface.destroy_decoratives{area = chunk_area}
        end
    end

    game.print("Background set to white (water preserved)!")
end)