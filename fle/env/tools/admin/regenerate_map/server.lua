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

  local radius     = 10                      -- in *chunks*
  local center_cx  = math.floor(player.position.x / 32)
  local center_cy  = math.floor(player.position.y / 32)

  local chunks = {}
  for dx = -radius, radius do
    for dy = -radius, radius do
      table.insert(chunks, {x = center_cx + dx, y = center_cy + dy})
    end
  end

  ------------------------------------------- 3.  Rerun the map generator
  local tree_names = {}
  for name, proto in pairs(game.entity_prototypes) do
      if proto.type == "tree" then
          table.insert(tree_names, name)
      end
  end

  -- Add rocks to the list
  table.insert(tree_names, 'rock-huge')
  table.insert(tree_names, 'rock-big')

  -- Regenerate them
  surface.regenerate_entity(tree_names, chunks)
end
