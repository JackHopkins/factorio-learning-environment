-- control.lua — save-based mod entrypoint

-- Helper to require a list of modules under a prefix.
local function require_dir(prefix, list)
  log("Loading " .. prefix .. " with " .. #list .. " modules")
  for _, name in pairs(list) do require(prefix .. name) end
end

-- Initialize persistent state early (Factorio will persist `global` with the save).
global = global or {}
global.actions = global.actions or {}
global.utils = global.utils or {}


-- Load utilities/admin/agent tools at top-level (outside events/RCON).
require_dir("script.utils.", {
  -- e.g. "table_util", "positions", "strings"
  'clear_entities',
  'enemies',
  'initialise',
  'priority_queue',
  'reset',
  'alerts',
  'build_checkerboard',
  'recipe_fluid_connection_mappings',
  'clear_inventory',
  'initialise_inventory',
  'util',
  'production_score',
  'serialize',
  'checksum',
  'reset_position',
  'connection_points',
})

require_dir("script.tools.admin.", {
  -- e.g. "tp", "ban", "blueprint_io"
  'clear_entities',
  'enemies',
  'initialise',
  'priority_queue',
  'reset',
  'alerts',
  'build_checkerboard',
  'recipe_fluid_connection_mappings',
  'clear_inventory',
  'initialise_inventory',
  'util',
  'production_score',
  'serialize',
  'checksum',
  'reset_position',
  'connection_points',
})

require_dir("script.tools.agent.", {
  'get_messages',
  'load_research_state',
  'inspect_entities',
  'production_stats',
  'clear_collision_boxes',
  'regenerate_resources',
  'extend_collision_boxes',
  'load_blueprint',
  'save_blueprint',
  'render',
  'get_factory_centroid',
  'clear_entities',
  'get_path',
  'save_research_state',
  'request_path',
  'render_message',
  'save_entity_state',
  'get_production_stats',
  'load_entity_state',
})

-- Register events/commands AFTER everything is required.
script.on_init(function()
  -- any init work
end)
