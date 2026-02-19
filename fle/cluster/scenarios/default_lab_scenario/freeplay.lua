local util = require("util")
local crash_site = require("crash-site")
require('story')

local created_items = function()
  return
  {
    ["iron-plate"] = 8,
    ["wood"] = 1,
    ["pistol"] = 1,
    ["firearm-magazine"] = 10,
    ["burner-mining-drill"] = 1,
    ["stone-furnace"] = 1
  }
end

local respawn_items = function()
  return
  {
    ["pistol"] = 1,
    ["firearm-magazine"] = 10
  }
end

local ship_items = function()
  return
  {
    ["firearm-magazine"] = 8
  }
end

local debris_items = function()
  return
  {
    ["iron-plate"] = 8
  }
end

local ship_parts = function()
  return crash_site.default_ship_parts()
end

local chart_starting_area = function()
  local r = storage.chart_distance or 200
  local force = game.forces.player
  local surface = game.surfaces[1]
  local origin = force.get_spawn_position(surface)
  force.chart(surface, {{origin.x - r, origin.y - r}, {origin.x + r, origin.y + r}})
end


local on_player_created = function(event)
  local player = game.get_player(event.player_index)
  util.insert_safe(player, storage.created_items)

  if not storage.init_ran then

    --This is so that other mods and scripts have a chance to do remote calls before we do things like charting the starting area, creating the crash site, etc.
    storage.init_ran = true

    chart_starting_area()

    if not storage.disable_crashsite then
      local surface = player.surface
      surface.daytime = 0.7
      crash_site.create_crash_site(surface, {-5,-6}, util.copy(storage.crashed_ship_items), util.copy(storage.crashed_debris_items), util.copy(storage.crashed_ship_parts))
      util.remove_safe(player, storage.crashed_ship_items)
      util.remove_safe(player, storage.crashed_debris_items)
      player.get_main_inventory().sort_and_merge()
      if player.character then
        player.character.destructible = false
      end
      storage.crash_site_cutscene_active = true
      crash_site.create_cutscene(player, {-5, -4})
      return
    end

  end

  if not storage.skip_intro then
    if game.is_multiplayer() then
      player.print(storage.custom_intro_message or {"msg-intro"})
    else
      game.show_message_dialog{text = storage.custom_intro_message or {"msg-intro"}}
    end
  end

end

local on_player_respawned = function(event)
  local player = game.get_player(event.player_index)
  util.insert_safe(player, storage.respawn_items)
end

local on_tick = function(event)
  story_update(storage.story, event)
  game.print("tick!")
end

local on_cutscene_waypoint_reached = function(event)
  if not storage.crash_site_cutscene_active then return end
  if not crash_site.is_crash_site_cutscene(event) then return end

  local player = game.get_player(event.player_index)

  player.exit_cutscene()

  if not storage.skip_intro then
    if game.is_multiplayer() then
      player.print(storage.custom_intro_message or {"msg-intro"})
    else
      game.show_message_dialog{text = storage.custom_intro_message or {"msg-intro"}}
    end
  end
end

local skip_crash_site_cutscene = function(event)
  if not storage.crash_site_cutscene_active then return end
  if event.player_index ~= 1 then return end
  local player = game.get_player(event.player_index)
  if player.controller_type == defines.controllers.cutscene then
    player.exit_cutscene()
  end
end

local on_cutscene_cancelled = function(event)
  if not storage.crash_site_cutscene_active then return end
  if event.player_index ~= 1 then return end
  storage.crash_site_cutscene_active = nil
  local player = game.get_player(event.player_index)
  if player.gui.screen.skip_cutscene_label then
    player.gui.screen.skip_cutscene_label.destroy()
  end
  if player.character then
    player.character.destructible = true
  end
  player.zoom = 1.5
end

local on_player_display_refresh = function(event)
  crash_site.on_player_display_refresh(event)
end

local freeplay_interface =
{
  get_created_items = function()
    return storage.created_items
  end,
  set_created_items = function(map)
    storage.created_items = map or error("Remote call parameter to freeplay set created items can't be nil.")
  end,
  get_respawn_items = function()
    return storage.respawn_items
  end,
  set_respawn_items = function(map)
    storage.respawn_items = map or error("Remote call parameter to freeplay set respawn items can't be nil.")
  end,
  set_skip_intro = function(bool)
    storage.skip_intro = bool
  end,
  get_skip_intro = function()
    return storage.skip_intro
  end,
  set_custom_intro_message = function(message)
    storage.custom_intro_message = message
  end,
  get_custom_intro_message = function()
    return storage.custom_intro_message
  end,
  set_chart_distance = function(value)
    storage.chart_distance = tonumber(value) or error("Remote call parameter to freeplay set chart distance must be a number")
  end,
  get_disable_crashsite = function()
    return storage.disable_crashsite
  end,
  set_disable_crashsite = function(bool)
    storage.disable_crashsite = bool
  end,
  get_init_ran = function()
    return storage.init_ran
  end,
  get_ship_items = function()
    return storage.crashed_ship_items
  end,
  set_ship_items = function(map)
    storage.crashed_ship_items = map or error("Remote call parameter to freeplay set created items can't be nil.")
  end,
  get_debris_items = function()
    return storage.crashed_debris_items
  end,
  set_debris_items = function(map)
    storage.crashed_debris_items = map or error("Remote call parameter to freeplay set respawn items can't be nil.")
  end,
  get_ship_parts = function()
    return storage.crashed_ship_parts
  end,
  set_ship_parts = function(parts)
    storage.crashed_ship_parts = parts or error("Remote call parameter to freeplay set ship parts can't be nil.")
  end
}

if not remote.interfaces["freeplay"] then
  remote.add_interface("freeplay", freeplay_interface)
end

local is_debug = function()
  local surface = game.surfaces.nauvis
  local map_gen_settings = surface.map_gen_settings
  return map_gen_settings.width == 50 and map_gen_settings.height == 50
end

local freeplay = {}

freeplay.events =
{
  [defines.events.on_player_created] = on_player_created,
  [defines.events.on_player_respawned] = on_player_respawned,
  [defines.events.on_cutscene_waypoint_reached] = on_cutscene_waypoint_reached,
  ["crash-site-skip-cutscene"] = skip_crash_site_cutscene,
  [defines.events.on_player_display_resolution_changed] = on_player_display_refresh,
  [defines.events.on_player_display_scale_changed] = on_player_display_refresh,
  [defines.events.on_cutscene_cancelled] = on_cutscene_cancelled,
  [defines.events.on_tick] = on_tick
}

freeplay.on_configuration_changed = function()
  storage.created_items = storage.created_items or created_items()
  storage.respawn_items = storage.respawn_items or respawn_items()
  storage.crashed_ship_items = storage.crashed_ship_items or ship_items()
  storage.crashed_debris_items = storage.crashed_debris_items or debris_items()
  storage.crashed_ship_parts = storage.crashed_ship_parts or ship_parts()

  if not storage.init_ran then
    -- migrating old saves.
    storage.init_ran = #game.players > 0
  end
end

storage.story_table =
{
  {
    {
      init = function(event, story)
        game.print("Welcome players")
        set_goal({"Enjoy the scenery for 5 seconds"})
      end,
      condition = story_elapsed_check(5)
    },
    {
      init = function(event, story)
        game.print("Enough relaxation, time to automate!")
        set_goal("Automate it!")
        --game.players[1].set_goal_description("Automate!", true)
        set_info{text = "Automating things is a lot of fun, trust me"}
        for k, player in pairs (game.players) do
          player.insert("iron-plate")
        end
      end,
      update = function(event, story)
        if event.name == defines.events.on_player_crafted_item then
          game.players[event.player_index].print({"", "You crafted a ", prototypes.item[event.item_stack.name].localised_name})
        end
      end,
      condition = function(event)
        return event.name == defines.events.on_built_entity
      end,
      action = function(event)
        game.print({"", game.players[event.player_index].name, " built a ", event.entity.localised_name})
      end
    },
    {
      init = function()
        set_goal("Thats it guys!")
        set_info()
      end,
      condition = story_elapsed_check(5)
    }
  }
}
story_init_helpers(storage.story_table)

freeplay.on_init = function()
  storage.story = story_init()
  storage.created_items = created_items()
  storage.respawn_items = respawn_items()
  storage.crashed_ship_items = ship_items()
  storage.crashed_debris_items = debris_items()
  storage.crashed_ship_parts = ship_parts()

  if is_debug() then
    storage.skip_intro = true
    storage.disable_crashsite = true
  end

end

story_init_helpers(story_table)

return freeplay
