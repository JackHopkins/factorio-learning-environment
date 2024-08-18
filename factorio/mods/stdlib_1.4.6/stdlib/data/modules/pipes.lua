--- Pipes
-- @module Data.Pipes

local Pipes = {}
local Sprites = require('__stdlib__/stdlib/data/modules/sprites')
--setmetatable(Pipes, {__index = Sprites})

--Define pipe connection pipe pictures, not all entities use these. This function needs some work though.
function Pipes.pictures(pictures, shift_north, shift_south, shift_west, shift_east, replacements)
    local new_pictures = {
        north = shift_north and
            {
                filename = '__base__/graphics/entity/' .. pictures .. '/' .. pictures .. '-pipe-N.png',
                priority = 'extra-high',
                width = 35,
                height = 18,
                shift = shift_north
            } or
            Sprites.empty_picture(),
        south = shift_south and
            {
                filename = '__base__/graphics/entity/' .. pictures .. '/' .. pictures .. '-pipe-S.png',
                priority = 'extra-high',
                width = 44,
                height = 31,
                shift = shift_south
            } or
            Sprites.empty_picture(),
        west = shift_west and
            {
                filename = '__base__/graphics/entity/' .. pictures .. '/' .. pictures .. '-pipe-W.png',
                priority = 'extra-high',
                width = 19,
                height = 37,
                shift = shift_west
            } or
            Sprites.empty_picture(),
        east = shift_east and
            {
                filename = '__base__/graphics/entity/' .. pictures .. '/' .. pictures .. '-pipe-E.png',
                priority = 'extra-high',
                width = 20,
                height = 38,
                shift = shift_east
            } or
            Sprites.empty_picture()
    }
    for direction, image in pairs(replacements or {}) do
        if not (new_pictures[direction].filename == '__core__/graphics/empty.png') then
            new_pictures[direction].filename = image.filename
            new_pictures[direction].width = image.width
            new_pictures[direction].height = image.height
            new_pictures[direction].priority = image.priority or new_pictures[direction].priority
        end
    end
    return new_pictures
end

--return pipe covers for true directions.
function Pipes.covers(n, s, w, e)
    if (n == nil and s == nil and w == nil and e == nil) then
        n, s, e, w = true, true, true, true
    end

    n =
        n and
        {
            layers = {
                {
                    filename = '__base__/graphics/entity/pipe-covers/pipe-cover-north.png',
                    priority = 'extra-high',
                    width = 64,
                    height = 64,
                    hr_version = {
                        filename = '__base__/graphics/entity/pipe-covers/hr-pipe-cover-north.png',
                        priority = 'extra-high',
                        width = 128,
                        height = 128,
                        scale = 0.5
                    }
                },
                {
                    filename = '__base__/graphics/entity/pipe-covers/pipe-cover-north-shadow.png',
                    priority = 'extra-high',
                    width = 64,
                    height = 64,
                    draw_as_shadow = true,
                    hr_version = {
                        filename = '__base__/graphics/entity/pipe-covers/hr-pipe-cover-north-shadow.png',
                        priority = 'extra-high',
                        width = 128,
                        height = 128,
                        scale = 0.5,
                        draw_as_shadow = true
                    }
                }
            }
        } or
        Sprites.empty_picture()
    e =
        e and
        {
            layers = {
                {
                    filename = '__base__/graphics/entity/pipe-covers/pipe-cover-east.png',
                    priority = 'extra-high',
                    width = 64,
                    height = 64,
                    hr_version = {
                        filename = '__base__/graphics/entity/pipe-covers/hr-pipe-cover-east.png',
                        priority = 'extra-high',
                        width = 128,
                        height = 128,
                        scale = 0.5
                    }
                },
                {
                    filename = '__base__/graphics/entity/pipe-covers/pipe-cover-east-shadow.png',
                    priority = 'extra-high',
                    width = 64,
                    height = 64,
                    draw_as_shadow = true,
                    hr_version = {
                        filename = '__base__/graphics/entity/pipe-covers/hr-pipe-cover-east-shadow.png',
                        priority = 'extra-high',
                        width = 128,
                        height = 128,
                        scale = 0.5,
                        draw_as_shadow = true
                    }
                }
            }
        } or
        Sprites.empty_picture()
    s =
        s and
        {
            layers = {
                {
                    filename = '__base__/graphics/entity/pipe-covers/pipe-cover-south.png',
                    priority = 'extra-high',
                    width = 64,
                    height = 64,
                    hr_version = {
                        filename = '__base__/graphics/entity/pipe-covers/hr-pipe-cover-south.png',
                        priority = 'extra-high',
                        width = 128,
                        height = 128,
                        scale = 0.5
                    }
                },
                {
                    filename = '__base__/graphics/entity/pipe-covers/pipe-cover-south-shadow.png',
                    priority = 'extra-high',
                    width = 64,
                    height = 64,
                    draw_as_shadow = true,
                    hr_version = {
                        filename = '__base__/graphics/entity/pipe-covers/hr-pipe-cover-south-shadow.png',
                        priority = 'extra-high',
                        width = 128,
                        height = 128,
                        scale = 0.5,
                        draw_as_shadow = true
                    }
                }
            }
        } or
        Sprites.empty_picture()
    w =
        w and
        {
            layers = {
                {
                    filename = '__base__/graphics/entity/pipe-covers/pipe-cover-west.png',
                    priority = 'extra-high',
                    width = 64,
                    height = 64,
                    hr_version = {
                        filename = '__base__/graphics/entity/pipe-covers/hr-pipe-cover-west.png',
                        priority = 'extra-high',
                        width = 128,
                        height = 128,
                        scale = 0.5
                    }
                },
                {
                    filename = '__base__/graphics/entity/pipe-covers/pipe-cover-west-shadow.png',
                    priority = 'extra-high',
                    width = 64,
                    height = 64,
                    draw_as_shadow = true,
                    hr_version = {
                        filename = '__base__/graphics/entity/pipe-covers/hr-pipe-cover-west-shadow.png',
                        priority = 'extra-high',
                        width = 128,
                        height = 128,
                        scale = 0.5,
                        draw_as_shadow = true
                    }
                }
            }
        } or
        Sprites.empty_picture()

    return {north = n, south = s, east = e, west = w}
end

return Pipes
