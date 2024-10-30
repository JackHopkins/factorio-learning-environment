```
/c global.actions.set_inserter_speed(game.player.index, 2)  -- Double inserter speed
/c global.actions.set_furnace_speed(game.player.index, 1.5)  -- 1.5x furnace speed
/c global.actions.set_all_speeds(game.player.index, 2)  -- Double all speeds
/c global.actions.set_all_speeds(game.player.index, 1)  -- Reset all speeds
/c global.actions.set_belt_speed(game.player.index, 250)
```

```
/c game.forces["player"].technologies["transport-belt"].effect_description = string.format("Belt speed: %.2f items/second", game.entity_prototypes["transport-belt"].belt_speed * 100)
```
```/c game.print(dump(game.forces["player"].technologies))
```/c game.print(dump(game.forces["player"].technologies['transport-belt'].effect_description))