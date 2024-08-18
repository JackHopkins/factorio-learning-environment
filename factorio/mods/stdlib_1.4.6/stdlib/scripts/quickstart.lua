--- Quickstart script.
-- Creates a quickstart world for testing mods.
-- <p>config settings should be a created in a table retured from `config-quickstart.lua`
-- @script quickstart
-- @usage
-- -- For use with STDLIB Events
-- if DEBUG then
--   require('__stdlib__/stdlib/scripts/quickstart').register_events()
-- end
-- @usage
-- --If not using stdlibs event system
-- local quickstart = require('__stdlib__/stdlib/scripts/quickstart')
-- script.on_event(defines.events.on_player_created, function()
--  quickstart.on_player_created() -- can be wrapped in an if DEBUG type check
-- end)

local Event = require('__stdlib__/stdlib/event/event')
local Area = require('__stdlib__/stdlib/area/area')
local QS = require('__stdlib__/stdlib/misc/config').new(prequire('config-quickstart') or {})

if not remote.interfaces['quickstart_script'] then
    local qs_interface = {}
    qs_interface.registered_to = function()
        if game then
            game.print(script.mod_name)
        end
        return script.mod_name
    end
    remote.add_interface('quickstart-script', qs_interface)
else
    return
end

local quickstart = {}

local rolling_stock = {
    ['locomotive'] = true,
    ['cargo-wagon'] = true,
    ['artillery-wagon'] = true,
    ['fluid-wagon'] = true
}

function quickstart.on_init()
    if not game.is_multiplayer() then
        if remote.interfaces['freeplay'] then
            remote.call('freeplay', 'set_skip_intro', true)
            remote.call('freeplay', 'set_disable_crashsite', true)
            local items = QS.get('items', {})
            remote.call('freeplay', 'set_created_items', items)
            remote.call('freeplay', 'set_respawn_items', items)
        elseif remote.interfaces['sandbox'] then
            remote.call('sandbox', 'set_skip_intro', true)
            remote.call('sandbox', 'set_skip_cheat_menu', true)
        end
    end
end

function quickstart.on_player_created(event)
    if not game.is_multiplayer() then
        local player = game.players[event.player_index]
        local surface = player.surface
        local force = player.force

        local area = Area(QS.get('area_box', {{-100, -100}, {100, 100}})):shrink_to_surface_size(surface)

        local chart_size_multiplier = QS.get('chart_size_multiplier', 0)
        if chart_size_multiplier > 0 then
            player.force.chart(surface, Area(area, true) * chart_size_multiplier)
        end

        player.surface.always_day = QS.get('always_day', false)

        if QS.get('cheat_mode', false) then
            player.cheat_mode = true
            player.force.research_all_technologies()
            if player.character then
                player.character_running_speed_modifier = 2
                player.character_reach_distance_bonus = 200
                player.character_build_distance_bonus = 200
            end
        end

        local power_armor = QS.get('power_armor', 'fake')
        if player.character and game.item_prototypes[power_armor] then
            --Put on power armor, install equipment
            player.get_inventory(defines.inventory.character_armor).insert(power_armor)
            local grid = player.character.grid
            if grid then
                for _, eq in pairs(QS.get('equipment', {'fusion-reactor-equipment'})) do
                    if game.equipment_prototypes[eq] then
                        grid.put {name = eq}
                    end
                end
            end
        end

        if remote.interfaces['RSO'] then
            if QS.get('disable_rso_starting', false) and remote.interfaces['RSO']['disableStartingArea'] then
                remote.call('RSO', 'disableStartingArea')
            end
            if QS.get('disable_rso_chunk', false) and remote.interfaces['RSO']['disableChunkHandler'] then
                remote.call('RSO', 'disableChunkHandler')
            end
        end

        if QS.get('destroy_everything', false) then
            for _, entity in pairs(surface.find_entities(area)) do
                -- destroying cliffs can invalidate other cliffs so .valid is needed here
                if entity.valid and entity.name ~= 'character' then
                    entity.destroy()
                end
            end
        end

        if QS.get('floor_tile', false) then
            local tiles = {}
            local floor_tile = QS.get('floor_tile')
            local floor_tile_alt = QS.get('floor_tile_alt', floor_tile)
            for x, y in Area(area):spiral_iterate() do
                if y % 2 == 0 then
                    if x % 2 == 0 then
                        tiles[#tiles + 1] = {name = floor_tile, position = {x = x, y = y}}
                    else
                        tiles[#tiles + 1] = {name = floor_tile_alt, position = {x = x, y = y}}
                    end
                else
                    if x % 2 ~= 0 then
                        tiles[#tiles + 1] = {name = floor_tile, position = {x = x, y = y}}
                    else
                        tiles[#tiles + 1] = {name = floor_tile_alt, position = {x = x, y = y}}
                    end
                end
            end
            surface.set_tiles(tiles, true)
            surface.destroy_decoratives(area)
        end

        if QS.get('ore_patches', false) then
            --Top left
            for x, y in Area {{-37.5, -27.5}, {-33.5, -3.5}}:iterate() do
                surface.create_entity {name = 'coal', position = {x, y}, amount = 2500}
            end
            --Top Right
            for x, y in Area {{33.5, -27.5}, {37.5, -3.5}}:iterate() do
                surface.create_entity {name = 'iron-ore', position = {x, y}, amount = 2500}
            end
            --Bottom Right
            for x, y in Area {{33.5, 3.5}, {37.5, 27.5}}:iterate() do
                surface.create_entity {name = 'copper-ore', position = {x, y}, amount = 2500}
            end
            --Bottom Left
            for x, y in Area {{-37.5, 3.5}, {-33.5, 27.5}}:iterate() do
                surface.create_entity {name = 'stone', position = {x, y}, amount = 2500}
            end
            surface.create_entity {name = 'crude-oil', position = {-35.5, 1.5}, amount = 32000}
            surface.create_entity {name = 'crude-oil', position = {-35.5, -1.5}, amount = 32000}
            surface.create_entity {name = 'crude-oil', position = {35.5, 1.5}, amount = 32000}
            surface.create_entity {name = 'crude-oil', position = {35.5, -1.5}, amount = 32000}
        end

        if QS.get('water_tiles', false) then
            local water_tiles = {}
            for x = 27.5, -27.5, -1 do
                for y = 45.5, 50.5, 1 do
                    if x < -4 or x > 4 then
                        water_tiles[#water_tiles + 1] = {
                            name = 'water',
                            position = {x = x, y = y}
                        }
                    end
                end
            end
            surface.set_tiles(water_tiles, false)
        end

        if QS.get('chunk_bounds', false) then
            local black = {r = 0, g = 0, b = 0}
            -- Horizontal
            rendering.draw_line{width = 2, color = black, from = {x = 32, y = 0}, to = {x = -32, y = 0}, surface = surface}
            rendering.draw_line{width = 2, color = black, from = {x = 32, y = 32}, to = {x = -32, y = 32}, surface = surface}
            rendering.draw_line{width = 2, color = black, from = {x = 32, y = -32}, to = {x = -32, y = -32}, surface = surface}
            -- Vertical
            rendering.draw_line{width = 2, color = black, from = {x = 0, y = 32}, to = {x = 0, y = -32}, surface = surface}
            rendering.draw_line{width = 2, color = black, from = {x = 32, y = 32}, to = {x = 32, y = -32}, surface = surface}
            rendering.draw_line{width = 2, color = black, from = {x = -32, y = 32}, to = {x = -32, y = -32}, surface = surface}
            -- Center
            rendering.draw_circle{width = 2, color = black, surface = surface, radius = 1, filled = false, target = {x = 0, y = 0}}
        end

        -- Create proxy blueprint from string, read in the entities and remove it.
        local bpstring
        local custom_string = QS.get('custom_bp_string', false)
        if custom_string then
            bpstring = custom_string
        elseif QS.get('default_bp_string', false) then
            bpstring = quickstart.bpstring
        end
        if bpstring then
            local bp = surface.create_entity {name = 'item-on-ground', position = {0, 0}, force = force, stack = 'blueprint'}
            bp.stack.import_stack(bpstring)
            local revive = bp.stack.build_blueprint {surface = player.surface, force = player.force, position = {0, 2}, force_build = true, skip_fog_of_war = false, by_player = player}
            local count = #revive
            for i, ent in ipairs(revive) do
                -- put rolling stock at the end.
                if i < count and rolling_stock[ent.ghost_type] then
                    revive[#revive + 1] = ent
                else
                    if ent.ghost_type == 'locomotive' then
                        local _, loco = ent.revive()
                        loco.burner.currently_burning = 'rocket-fuel'
                        loco.burner.remaining_burning_fuel = 222222222
                    else
                        ent.revive()
                    end
                end
            end
            bp.destroy()
        end

        if QS.get('setup_power', false) then
            if game.entity_prototypes['debug-energy-interface'] then
                local es = surface.create_entity {name = 'debug-energy-interface', position = {0, 0}, force = force, raise_built = true}
                es.destructible = false
            end
            if game.entity_prototypes['debug-substation'] then
                local sb = surface.create_entity {name = 'debug-substation', position = {0, 0}, force = force, raise_built = true}
                sb.destructible = false
            end
        end
    end
end

quickstart.bpstring =
    [[
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
]]

function quickstart.register_events()
    Event.register(Event.core_events.on_init, quickstart.on_init)
    Event.register(defines.events.on_player_created, quickstart.on_player_created)
    return quickstart
end
return quickstart
