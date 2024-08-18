local handler = require("event_handler")
handler.add_lib(require("freeplay"))
handler.add_lib(require("silo-script"))


--Initialize the story info
script.on_init(function()
  global.story = story_init()
end)

--Register to update the story on events
script.on_event(defines.events, function(event)
  story_update(global.story, event)
end)

--Story table is where the 'story' is all defined.
story_table =
{
  {
    --branch 1
    {
      --First story event

      --Initialise this event
      init = function(event, story)
        game.print("First init of first story event")
      end,

      --Update function that will run on all events
      update = function(event, story)
        log("updating")
      end,

      --Condition to move on. If the return value is 'true', the story will continue.
      condition = function(event, story)
        if event.tick > 100 then
          return true
        end
      end,

      --Action to perform after condition is met
      action = function(event, story)
        game.print("You completed the objective!")
      end
    },
    {
      --Second story event - example.
      init = function(event, story)
        game.print("Collect 100 iron plate")
      end,
      condition = function(event, story)
        return game.players[1].get_item_count("iron-plate") >= 100
      end,
      action = function(event, story)
        game.print("Well done")
      end
    }
    --Once the end of a branch is reached, the story is finished.
    --The game will now display the mission complete screen.
  },
  {
    --branch 2
  }
}

--Init the helpers and story table. Must be done all times script is loaded.
--story_init_helpers(story_table)

--Update the objective for all players
--set_goal({"objective-1"})

--Flash the goal GUI for players (updating info doesn't flash it)
--flash_goal()
