--- Sprites
-- @module Data.Sprites

local Sprites = {}

function Sprites.extract_monolith(filename, x, y, w, h)
    return {
        type = 'monolith',
        top_monolith_border = 0,
        right_monolith_border = 0,
        bottom_monolith_border = 0,
        left_monolith_border = 0,
        monolith_image = {
            filename = filename,
            priority = 'extra-high-no-scale',
            width = w,
            height = h,
            x = x,
            y = y
        }
    }
end

--- Quick to use empty picture.
-- @treturn table an empty pictures table
function Sprites.empty_picture()
    return {
        filename = '__core__/graphics/empty.png',
        priority = 'extra-high',
        width = 1,
        height = 1
    }
end
Sprites.empty_sprite = Sprites.empty_picture

--- Quick to use empty pictures.
-- @treturn table an empty pictures table
function Sprites.empty_pictures()
    local empty = Sprites.empty_picture()
    return {
        filename = empty.filename,
        width = empty.width,
        height = empty.height,
        line_length = 1,
        frame_count = 1,
        shift = {0, 0},
        animation_speed = 1,
        direction_count = 1
    }
end
Sprites.empty_animation = Sprites.empty_pictures

--- Quick to use empty animation.
-- @treturn table an empty animations table
function Sprites.empty_animations()
    return {
        Sprites.empty_pictures()
    }
end

--- Quick to use empty connections table.
-- @tparam int count how many connection points are needed
-- @treturn table an empty pictures table
function Sprites.empty_connection_points(count)
    local points = {}
    for i = 1, count or 1, 1 do
        points[i] = {
            shadow = {
                copper = {0, 0},
                green = {0, 0},
                red = {0, 0}
            },
            wire = {
                copper = {0, 0},
                green = {0, 0},
                red = {0, 0}
            }
        }
    end
    return points
end

return Sprites
