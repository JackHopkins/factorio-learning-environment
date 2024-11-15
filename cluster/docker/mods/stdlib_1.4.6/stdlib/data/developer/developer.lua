--- Developer
-- @script Developer

local Data = require('__stdlib__/stdlib/data/data')

local Developer = {
    __index = Data
}
setmetatable(Developer, Developer)

local function make_no_controls()
    local controls = {}
    for name in pairs(data.raw['autoplace-control']) do
        if name == 'grass' then
            controls[name] = {size = 'very-high', frequency = 'very-high', richness = 'very-low'}
        else
            controls[name] = {size = 'none', frequency = 'very-low', richness = 'very-low'}
        end
    end
    return controls
end

--- Make entities for easier mod testing.
-- @tparam string name The name of your mod
-- @usage
-- --data.lua
-- local Developer = require('__stdlib__/stdlib/data/develper/developer')
-- Developer.make_test_entities()
function Developer.make_test_entities()
    log('Making developer debug entities')
    if not data.raw['electric-energy-interface']['debug-energy-interface'] then
        Data('electric-energy-interface', 'electric-energy-interface'):copy('debug-energy-interface'):set_fields {
            flags = {'placeable-off-grid'},
            localised_name = 'Debug source',
            icon = data.raw['item']['electric-energy-interface'].icon,
            collision_mask = {},
            selection_box = {{0.0, -0.5}, {0.5, 0.5}},
            picture = Developer.Sprites.empty_picture()
        }:remove_fields {'minable', 'collision_box', 'vehicle_impact_sound', 'working_sound'}
    end

    if not data.raw['electric-pole']['debug-substation'] then
        Data('substation', 'electric-pole'):copy('debug-substation'):set_fields {
            localised_name = 'Debug power substation',
            flags = {'placeable-off-grid'},
            icon = data.raw['item']['substation'].icon,
            selection_box = {{-0.5, -0.5}, {0.0, 0.5}},
            collision_mask = {},
            pictures = Developer.Sprites.empty_pictures(),
            maximum_wire_distance = 64,
            supply_area_distance = 64,
            connection_points = Developer.Sprites.empty_connection_points(1)
        }:remove_fields {'minable', 'collision_box', 'vehicle_impact_sound', 'working_sound'}
    end

    local gen = data.raw['map-gen-presets']
    gen['default']['debug'] = {
        type = 'map-gen-presets',
        name = 'debug',
        localised_name = 'Debug',
        localised_description = 'Default settings for a debug world',
        order = 'z',
        basic_settings = {
            terrain_segmentation = 'very-low',
            water = 'none',
            autoplace_controls = make_no_controls(),
            height = 128,
            width = 128
        },
    }
end

return Developer
