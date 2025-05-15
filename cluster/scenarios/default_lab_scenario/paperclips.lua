require("story")

local paperclips = {}
--Init the story script
paperclips.on_init = function()
  global.story = story_init(player(1))
end

--Register the update to all events
local on_event = function(event)
  story_update(global.story, event)
end

--Can also register to specific events, if you want to do multiple things with that event
local on_tick = function(event)
  if global.story == nil then
    global.story = story_init(player(1))
  end
  story_update(global.story, event)
  game.print("tick")
  --Other things on tick can go here.
end

paperclips.events =
{
  [defines.events.on_player_created] = on_event,
  [defines.events.on_player_respawned] = on_event,
  [defines.events.on_cutscene_waypoint_reached] = on_event,
  ["crash-site-skip-cutscene"] = on_event,
  [defines.events.on_player_display_resolution_changed] = on_event,
  [defines.events.on_player_display_scale_changed] = on_event,
  [defines.events.on_cutscene_cancelled] = on_event,
  [defines.events.on_tick] = on_tick
}


story_table =
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
          game.players[event.player_index].print({"", "You crafted a ", game.item_prototypes[event.item_stack.name].localised_name})
        end
      end,
      condition = function(event)
        return event.name == defines.events.on_built_entity
      end,
      action = function(event)
        game.print({"", game.players[event.player_index].name, " built a ", event.created_entity.localised_name})
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

story_init_helpers(story_table)

return paperclips