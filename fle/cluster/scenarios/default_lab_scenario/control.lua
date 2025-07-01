require "util"
--local intro_screen = require("intro_screen")
require "story"

global.paths = global.paths or {}

local think = function(thought)
  game.players[1].print({"","[img=entity/character][color=orange]",{"engineer-title"},": [/color]",{"think-"..thought}})
end

function check_for_player_death(event)
  if event.name == defines.events.on_player_died then
    game.set_game_state({game_finished=true, player_won=false, can_continue=false})
  end
end

local function on_configuration_changed()
	game.reload_script()
end 

local on_player_created = function(event)

  local player = game.players[1]

  player.force.enable_research()
  game.forces.player.disable_all_prototypes()
  game.forces.player.reset_technology_effects()
  -- game.forces.player.reset()
  game.forces.player.research_queue_enabled = true
  game.map_settings.enemy_expansion.enabled = false
  game.forces.enemy.evolution_factor = 0
  game.map_settings.enemy_evolution.enabled = false
  --game.disable_tips_and_tricks()
  -- game.players[1].force.disable_all_prototypes()
  global.storage_tank = game.get_entity_by_tag("storage-tank")
  local entities =
  {
    global.storage_tank
  }
  for index, entity in pairs(entities) do
    entity.minable = false
    entity.destructible = false
  end
  global.intro_entities = entities
  

  global.car1 = game.get_entity_by_tag("car1")
  local entities2 =
  {
	global.car1
  }
  for index, entity in pairs(entities2) do
    entity.minable = false
  end
  global.intro_entities2 = entities2

  
  local recipe_list = player.force.recipes
  -- game.players[1].clear_recipe_notifications()
  recipe_list["chemical-plant"].enabled = false

  local technology_list = game.forces.player.technologies  
  technology_list["automation"].researched = true
  technology_list["stone-wall"].researched = true
  
  technology_list["optics"].enabled = true
  technology_list["gun-turret"].researched = true
  technology_list["logistics"].enabled = true
  technology_list["military"].enabled = true
  technology_list["logistic-science-pack"].researched = true
  technology_list["steel-processing"].enabled = true
  technology_list["electronics"].researched = true 
  technology_list["fast-inserter"].enabled = true 
  technology_list["automation-2"].enabled = true
  technology_list["electric-energy-distribution-1"].enabled = true 
  technology_list["engine"].enabled = true 
  technology_list["fluid-handling"].enabled = true 
  technology_list["oil-processing"].researched = true
  technology_list["logistics"].enabled = true
  technology_list["heavy-armor"].enabled = true
  technology_list["steel-axe"].enabled = true 
  technology_list["military-2"].enabled = true
  technology_list["chemical-science-pack"].enabled = true
  technology_list["military-science-pack"].enabled = true 
  technology_list["logistics-2"].enabled = true
  technology_list["advanced-material-processing"].enabled = true
  technology_list["solar-energy"].enabled = true
  technology_list["laser"].enabled = false
  technology_list["flamethrower"].enabled = true
  technology_list["flammables"].researched = true
  technology_list["modules"].enabled = false
  technology_list["speed-module"].enabled = false
  technology_list["effectivity-module"].enabled = false
  technology_list["productivity-module"].enabled = false
  technology_list["sulfur-processing"].researched = true
  technology_list["toolbelt"].enabled = true
  technology_list["advanced-electronics"].researched = true
  technology_list["explosives"].enabled = true
  technology_list["land-mine"].enabled = true
  technology_list["electric-energy-accumulators"].enabled = true
  technology_list["laser-turret"].enabled = false
  technology_list["tank"].enabled = false
  technology_list["circuit-network"].enabled = true
  technology_list["night-vision-equipment"].enabled = false
  technology_list["solar-panel-equipment"].enabled = false
  technology_list["energy-shield-equipment"].enabled = false
  technology_list["battery-equipment"].enabled = false
  technology_list["modular-armor"].enabled = false
  technology_list["military-3"].enabled = true
  technology_list["railway"].enabled = true
  technology_list["automated-rail-transportation"].enabled = false
  technology_list["rail-signals"].enabled = true
  technology_list["gate"].enabled = true
  technology_list["rocketry"].enabled = false
  technology_list["battery"].researched = true
  technology_list["plastics"].researched = true
  technology_list["fluid-wagon"].enabled = true
  technology_list["stack-inserter"].enabled = true


  --blocked tech
  technology_list["automation-3"].enabled = false
  technology_list["automobilism"].enabled = false -- only from start
  technology_list["explosive-rocketry"].enabled = false
  technology_list["braking-force-2"].enabled = false
  technology_list["cliff-explosives"].enabled = false
  technology_list["construction-robotics"].enabled = false
  technology_list["energy-weapons-damage-3"].enabled = false
  technology_list["exoskeleton-equipment"].enabled = false
  technology_list["landfill"].enabled = false
  technology_list["utility-science-pack"].enabled = false
  technology_list["production-science-pack"].enabled = false
  technology_list["advanced-material-processing-2"].enabled = false
  technology_list["personal-roboport-equipment"].enabled = false
  technology_list["personal-laser-defense-equipment"].enabled = false
  technology_list["nuclear-fuel-reprocessing"].enabled = false
  technology_list["nuclear-power"].enabled = false
  technology_list["military-4"].enabled = false
  technology_list["destroyer"].enabled = false
  technology_list["defender"].enabled = false
  technology_list["discharge-defense-equipment"].enabled = false
  technology_list["distractor"].enabled = false
  technology_list["artillery"].enabled = false
  technology_list["atomic-bomb"].enabled = false
  technology_list["robotics"].enabled = false
  technology_list["automation-3"].enabled = false
  technology_list["rocket-control-unit"].enabled = false
  technology_list["logistic-system"].enabled = false
  technology_list["logistic-robotics"].enabled = false
  technology_list["electric-engine"].enabled = false
  technology_list["uranium-processing"].enabled = false
  technology_list["spidertron"].enabled = false
  technology_list["kovarex-enrichment-process"].enabled = false
  technology_list["lubricant"].enabled = false
  technology_list["low-density-structure"].enabled = false
  technology_list["rocket-fuel"].enabled = false


  
  --blocked tech upgrades
  technology_list["braking-force-1"].enabled = true
  technology_list["energy-weapons-damage-1"].enabled = false
  technology_list["energy-weapons-damage-2"].enabled = false
  technology_list["energy-weapons-damage-3"].enabled = false
  technology_list["inserter-capacity-bonus-1"].enabled = true
  technology_list["inserter-capacity-bonus-2"].enabled = true
  technology_list["inserter-capacity-bonus-3"].enabled = true
  technology_list["laser-shooting-speed-1"].enabled = false
  technology_list["laser-shooting-speed-2"].enabled = false
  technology_list["laser-shooting-speed-3"].enabled = false
  technology_list["stronger-explosives-1"].enabled = true
  technology_list["stronger-explosives-2"].enabled = false
  technology_list["stronger-explosives-3"].enabled = false
  technology_list["physical-projectile-damage-1"].enabled = true
  technology_list["physical-projectile-damage-2"].enabled = true
  technology_list["physical-projectile-damage-3"].enabled = true
  technology_list["physical-projectile-damage-4"].enabled = true
  technology_list["physical-projectile-damage-5"].enabled = false
  technology_list["refined-flammables-1"].enabled = true
  technology_list["refined-flammables-2"].enabled = true
  technology_list["refined-flammables-3"].enabled = false
  technology_list["research-speed-1"].enabled = true
  technology_list["research-speed-2"].enabled = true
  technology_list["research-speed-3"].enabled = true
  technology_list["research-speed-4"].enabled = false
  technology_list["mining-productivity-1"].enabled = true
  technology_list["mining-productivity-2"].enabled = false
  technology_list["weapon-shooting-speed-1"].enabled = true
  technology_list["weapon-shooting-speed-2"].enabled = true
  technology_list["weapon-shooting-speed-3"].enabled = true
  technology_list["weapon-shooting-speed-4"].enabled = false
  technology_list["worker-robots-speed-1"].enabled = false
  technology_list["worker-robots-speed-2"].enabled = false
  technology_list["worker-robots-storage-1"].enabled = false
  technology_list["worker-robots-storage-2"].enabled = false
  technology_list["artillery-shell-range-1"].enabled = false
  technology_list["artillery-shell-speed-1"].enabled = false
  technology_list["follower-robot-count-1"].enabled = false
  technology_list["follower-robot-count-2"].enabled = false

  

end


script.on_event(defines.events.on_script_path_request_finished, function(event)
    local request_data = global.path_requests[event.id]
    if not request_data then
        log("No request data found for ID: " .. event.id)
        return
    end

    local player = game.get_player(request_data)
    if not player then
        log("Player not found for request ID: " .. event.id)
        return
    end

    if event.path then
        -- Path found successfully
        player.print("Path found with " .. #event.path .. " waypoints")
        global.paths[event.id] = event.path
        log("Path found for request ID: " .. event.id)
    elseif event.try_again_later then
        player.print("Pathfinder is busy, try again later")
        global.paths[event.id] = "busy"
        log("Pathfinder busy for request ID: " .. event.id)
    else
        player.print("Path not found" .. serpent.block(event))
        global.paths[event.id] = "not_found"
        log("Path not found for request ID: " .. event.id)

    end
end)


local story_table =
{
  {
    {
      init = function(event, story)
        game.players[1].teleport({0, 0})
        game.print("Welcome players")
        set_goal({"Enjoy the scenery for 5 seconds"})
      end,
      condition = story_elapsed_check(5)
    },
    {
      action = function()
        local character = game.players[1]
        character.insert{name = "iron-gear-wheel", count = 47}
        character.insert{name = "pistol", count = 1}
        character.insert{name = "firearm-magazine", count = 1}
        character.insert{name = "electronic-circuit", count = 90}
        character.insert{name = "copper-cable", count = 38}
        character.insert{name = "iron-plate", count = 10}
        character.insert{name = "steam-engine", count = 1}
        set_info()
      end
    },
    {
      init = function(event, story)
        game.print("Collect 10 iron ore")
        set_goal({"goal-iron-ore"})
      end,
      condition = function(event, story)
        return game.players[1].get_item_count("iron-ore") >= 10
      end,
      action = function(event, story)
        game.print("Well done")
        set_goal({"completed-iron-ore"})
      end
    },
    {
      init = function(event, story)
        game.print("Build a stone furnace")
        set_goal({"goal-build-furnace"})
      end,
      condition = function(event, story)
        local has_furnace = game.players[1].get_item_count("stone-furnace") >= 1
        local furnace_on_ground = game.players[1].surface.count_entities_filtered{position = game.players[1].position, radius=100, name = "stone-furnace"} >= 1
        return has_furnace or furnace_on_ground
      end,
      action = function(event, story)
        game.print("Great! Now place the furnace on the ground.")
        set_goal({"goal-place-furnace"})
      end
    },
    {
      init = function(event, story)
        game.print("Smelt the iron ore in the furnace and collect 10 iron plates")
        set_goal({"goal-smelt-and-collect-10-iron-plates"})
      end,
      condition = function(event, story)
          return game.players[1].get_item_count("iron-plate") >= 10
      end,
      action = function(event, story)
          game.print("Well done")
          set_goal({"completed-iron-plate"})
      end
    },
    {
      init = function(event, story)
        game.print("Collect 10 copper ore")
        set_goal({"goal-copper-ore"})
      end,
      condition = function(event, story)
        return game.players[1].get_item_count("copper-ore") >= 10
      end,
      action = function(event, story)
        game.print("Well done")
        set_goal({"completed-copper-ore"})
      end
    },
    {
      init = function(event, story)
        game.print("Smelt the copper ore in the furnace and collect 10 copper plates")
        set_goal({"goal-smelt-and-collect-10-copper-plates"})
      end,
      condition = function(event, story)
          return game.players[1].get_item_count("copper-plate") >= 10
      end,
        action = function(event, story)
            game.print("Well done")
            set_goal({"completed-smelt-and-collect-10-copper-plates"})
        end
    },
    {
      init = function(event, story)
        game.print("Craft a burner mining drill")
        set_goal({"goal-craft-burner-mining-drill"})
      end,
      condition = function(event, story)
          return game.players[1].get_item_count("burner-mining-drill") >= 1
      end,
      action = function(event, story)
          game.print("Great! Now place the burner mining drill on the iron ore.")
          set_goal({"completed-craft-burner-mining-drill"})
      end
    },
    {
      init = function(event, story)
        game.print("Place the burner mining drill on the iron ore")
        set_goal({"goal-place-burner-mining-drill"})
      end,
      condition = function(event, story)
        return game.players[1].get_item_count("burner-mining-drill") == 0
      end,
      action = function(event, story)
          game.print("Well done")
          set_goal({"completed-place-burner-mining-drill"})
      end
    },
    {
      init = function(event, story)
        game.print("Build an assembling machine")
        set_goal({"goal-build-assembling-machine"})
      end,
      condition = function(event, story)
        return game.players[1].get_item_count("assembling-machine-1") >= 1
      end,
      action = function(event, story)
        game.print("Great! Now place the assembling machine on the ground.")
        set_goal({"completed-place-assembling-machine"})
      end
    },
    {
      init = function(event, story)
        game.print("Automate the production of iron gears")
        set_goal({"goal-automate-iron-gears"})
      end,
      condition = function(event, story)
        return game.players[1].get_item_count("iron-gear-wheel") >= 100
      end,
      action = function(event, story)
        game.print("Well done")
        set_goal({"completed-iron-gears"})
      end
    },
    {
      init = function(event, story)
        game.print("Build a transport belt")
        set_goal({ "goal-build-transport-belt" })
      end,
      condition = function(event, story)
        return game.players[1].get_item_count("transport-belt") >= 1
      end,
      action = function(event, story)
        game.print("Great! Now place the transport belt on the ground.")
        set_goal({ "goal-place-transport-belt" })
      end
    }
  }
}
story_init_helpers(story_table)


local init = function()
  global.story = story_init()

  game.map_settings.enemy_expansion.enabled = false
  game.forces.enemy.evolution_factor = 0
  game.map_settings.enemy_evolution.enabled = false
  --game.disable_tips_and_tricks()
  -- game.players[1].force.disable_all_prototypes()
end


local story_events =
{
  defines.events.on_tick,
  defines.events.on_entity_died,
  defines.events.on_built_entity,
  defines.events.on_player_mined_item,
  defines.events.on_player_mined_entity,
  defines.events.on_sector_scanned,
  defines.events.on_entity_died,
  defines.events.on_entity_damaged,
  defines.events.on_player_died
} 

local function on_configuration_changed()
	--game.reload_script()
    init()
end 

script.on_event(story_events, function(event)
   if #game.players > 0 and game.players[1].character then
     check_for_player_death(event)
     story_update(global.story, event)
   end
end)

script.on_event(defines.events.on_player_created, function(event)
  on_player_created(event)
end)

script.on_event(defines.events.on_player_crafted_item, check_automate_science_packs_advice)
script.on_event(defines.events.on_player_created, on_player_created)
script.on_event(defines.events.on_unit_group_finished_gathering, on_unit_group_finished_gathering)
--script.on_event(defines.events.on_gui_click, intro_screen.on_gui_click)
script.on_init(on_configuration_changed)
script.on_configuration_changed(on_configuration_changed)



