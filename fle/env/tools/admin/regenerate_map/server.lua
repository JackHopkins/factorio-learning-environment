function global.actions.regenerate_map(player_index)
  ------------------------------------------- 0.  Quick handles
  local player   = global.agent_characters[player_index] or error("bad player")
  local surface  = player.surface                -- normally "nauvis"
  local force    = player.force                  -- normally "player"

  ------------------------------------------- 1.  Reset the random seed for deterministic drops
  local map_gen_seed = surface.map_gen_settings.seed

  ------------------------------------------- 2.  Create a new seeded random generator for the map
  -- This ensures that any RNG-dependent operations (like rock mining) are deterministic
  if not global.map_random_generator then
    global.map_random_generator = game.create_random_generator(map_gen_seed)
  end
  global.map_random_generator.re_seed(map_gen_seed)

  ------------------------------------------- 3.  Rerun the map generator
  surface.regenerate_entity({'rock-huge', 'rock-big'})       -- nil → "everything with autoplace"
end
