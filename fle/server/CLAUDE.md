You are here to help me integrate MCP with the Factorio Learning Environment.

---
# Source Tree

Source Tree:

```
PaperclipMaximiser
├── cluster
│   ├── docker
│   │   ├── !README.md
│   │   ├── build_alternative_installation_location.sh
│   │   ├── requirements.txt
│   │   ├── run_local.sh
│   │   ├── config
│   │   │   ├── scenario.sh
│   │   │   ├── mod-list.json
│   │   │   ├── factorio.pem
│   │   │   ├── config.ini
│   │   │   ├── server-settings.json
│   │   │   ├── docker-entrypoint.sh
│   │   │   ├── map-gen-settings.json
│   │   │   ├── rconpw
│   │   │   ├── docker-update-mods.sh
│   │   │   ├── map-settings.json
│   │   │   ├── update-mods.sh
│   │   │   └── scenario2map.sh
│   │   ├── probe.sh
│   │   ├── Dockerfile
│   │   ├── setup_docker_repo.sh
│   │   ├── install-docker.sh
│   │   ├── run.sh
│   │   ├── build.sh
│   │   ├── mods
│   │   │   ├── stdlib_1.4.6
│   │   │   │   ├── stdlib-docs
│   │   │   │   │   ├── spectre-icons.min.css
│   │   │   │   │   ├── index.html
│   │   │   │   │   ├── ldoc.css
│   │   │   │   │   ├── classes
│   │   │   │   │   │   ├── LinkedList.html
│   │   │   │   │   │   ├── Data.Recipe.html
│   │   │   │   │   │   ├── string_array.html
│   │   │   │   │   │   ├── Data.Entity.html
│   │   │   │   │   │   ├── Data.html
│   │   │   │   │   │   ├── unique_array.html
│   │   │   │   │   │   ├── Data.Item.html
│   │   │   │   │   │   ├── Vendor.Enumerable.html
│   │   │   │   │   │   ├── Data.Category.html
│   │   │   │   │   │   ├── Data.Technology.html
│   │   │   │   │   │   └── Data.Fluid.html
│   │   │   │   │   ├── spectre.min.css
│   │   │   │   │   ├── examples
│   │   │   │   │   │   └── event.lua.html
│   │   │   │   │   ├── scripts
│   │   │   │   │   │   ├── quickstart.html
│   │   │   │   │   │   └── Developer.html
│   │   │   │   │   ├── modules
│   │   │   │   │   │   ├── Area.Direction.html
│   │   │   │   │   │   ├── Utils.table.html
│   │   │   │   │   │   ├── Utils.string.html
│   │   │   │   │   │   ├── Area.Chunk.html
│   │   │   │   │   │   ├── Entity.Inventory.html
│   │   │   │   │   │   ├── Area.Surface.html
│   │   │   │   │   │   ├── Entity.Entity.html
│   │   │   │   │   │   ├── Entity.Resource.html
│   │   │   │   │   │   ├── Data.Sprites.html
│   │   │   │   │   │   ├── Event.Surface.html
│   │   │   │   │   │   ├── vendor.version.html
│   │   │   │   │   │   ├── Event.Event.html
│   │   │   │   │   │   ├── Data.Util.html
│   │   │   │   │   │   ├── Misc.Config.html
│   │   │   │   │   │   ├── Core.html
│   │   │   │   │   │   ├── Area.Area.html
│   │   │   │   │   │   ├── Area.Orientation.html
│   │   │   │   │   │   ├── Utils.Globals.html
│   │   │   │   │   │   ├── Data.Pipes.html
│   │   │   │   │   │   ├── Utils.Is.html
│   │   │   │   │   │   ├── defines.anticolor.html
│   │   │   │   │   │   ├── Event.Force.html
│   │   │   │   │   │   ├── defines.time.html
│   │   │   │   │   │   ├── Misc.Logger.html
│   │   │   │   │   │   ├── defines.lightcolor.html
│   │   │   │   │   │   ├── Event.Gui.html
│   │   │   │   │   │   ├── Utils.Color.html
│   │   │   │   │   │   ├── defines.color.html
│   │   │   │   │   │   ├── Event.Filters.html
│   │   │   │   │   │   ├── Game.html
│   │   │   │   │   │   ├── Event.Trains.html
│   │   │   │   │   │   ├── Utils.math.html
│   │   │   │   │   │   ├── Area.Position.html
│   │   │   │   │   │   ├── Area.Tile.html
│   │   │   │   │   │   ├── Utils.Iter.html
│   │   │   │   │   │   ├── Event.Changes.html
│   │   │   │   │   │   ├── Misc.Migrate.html
│   │   │   │   │   │   ├── Misc.Queue.html
│   │   │   │   │   │   └── Event.Player.html
│   │   │   │   │   └── topics
│   │   │   │   │       ├── contributing.md.html
│   │   │   │   │       ├── LICENSE.html
│   │   │   │   │       ├── style-guide.md.html
│   │   │   │   │       ├── changelog.txt.html
│   │   │   │   │       └── readme.md.html
│   │   │   │   ├── LICENSE
│   │   │   │   ├── readme.md
│   │   │   │   ├── thumbnail.png
│   │   │   │   ├── info.json
│   │   │   │   ├── stdlib
│   │   │   │   │   ├── misc
│   │   │   │   │   │   ├── logger.lua
│   │   │   │   │   │   ├── migrate.lua
│   │   │   │   │   │   ├── queue.lua
│   │   │   │   │   │   └── config.lua
│   │   │   │   │   ├── game.lua
│   │   │   │   │   ├── area
│   │   │   │   │   │   ├── area.lua
│   │   │   │   │   │   ├── direction.lua
│   │   │   │   │   │   ├── tile.lua
│   │   │   │   │   │   ├── surface.lua
│   │   │   │   │   │   ├── position.lua
│   │   │   │   │   │   ├── chunk.lua
│   │   │   │   │   │   └── orientation.lua
│   │   │   │   │   ├── entity
│   │   │   │   │   │   ├── inventory.lua
│   │   │   │   │   │   ├── entity.lua
│   │   │   │   │   │   └── resource.lua
│   │   │   │   │   ├── utils
│   │   │   │   │   │   ├── type.lua
│   │   │   │   │   │   ├── classes
│   │   │   │   │   │   │   ├── linked_list.lua
│   │   │   │   │   │   │   ├── string_array.lua
│   │   │   │   │   │   │   └── unique_array.lua
│   │   │   │   │   │   ├── iter.lua
│   │   │   │   │   │   ├── defines
│   │   │   │   │   │   │   ├── anticolor.lua
│   │   │   │   │   │   │   ├── time.lua
│   │   │   │   │   │   │   ├── color_list.lua
│   │   │   │   │   │   │   ├── lightcolor.lua
│   │   │   │   │   │   │   └── color.lua
│   │   │   │   │   │   ├── is.lua
│   │   │   │   │   │   ├── math.lua
│   │   │   │   │   │   ├── color.lua
│   │   │   │   │   │   ├── globals.lua
│   │   │   │   │   │   ├── string.lua
│   │   │   │   │   │   └── table.lua
│   │   │   │   │   ├── config.lua
│   │   │   │   │   ├── scripts
│   │   │   │   │   │   ├── interface.lua
│   │   │   │   │   │   └── quickstart.lua
│   │   │   │   │   ├── data
│   │   │   │   │   │   ├── category.lua
│   │   │   │   │   │   ├── developer
│   │   │   │   │   │   │   └── developer.lua
│   │   │   │   │   │   ├── technology.lua
│   │   │   │   │   │   ├── data.lua
│   │   │   │   │   │   ├── fluid.lua
│   │   │   │   │   │   ├── item.lua
│   │   │   │   │   │   ├── modules
│   │   │   │   │   │   │   ├── class.yuml
│   │   │   │   │   │   │   ├── recipe-test.lua
│   │   │   │   │   │   │   ├── notes.txt
│   │   │   │   │   │   │   ├── pipes.lua
│   │   │   │   │   │   │   ├── recipe.txt
│   │   │   │   │   │   │   ├── products.lua
│   │   │   │   │   │   │   ├── util.lua
│   │   │   │   │   │   │   ├── groups.lua
│   │   │   │   │   │   │   ├── sprites.lua
│   │   │   │   │   │   │   ├── product-data.lua
│   │   │   │   │   │   │   └── recipe.lua
│   │   │   │   │   │   ├── entity.lua
│   │   │   │   │   │   └── recipe.lua
│   │   │   │   │   ├── event
│   │   │   │   │   │   ├── event.lua
│   │   │   │   │   │   ├── surface.lua
│   │   │   │   │   │   ├── force.lua
│   │   │   │   │   │   ├── gui.lua
│   │   │   │   │   │   ├── trains.lua
│   │   │   │   │   │   ├── changes.lua
│   │   │   │   │   │   ├── modules
│   │   │   │   │   │   │   ├── dump_event_data.lua
│   │   │   │   │   │   │   ├── event_filters.lua
│   │   │   │   │   │   │   └── merge_data.lua
│   │   │   │   │   │   └── player.lua
│   │   │   │   │   ├── core.lua
│   │   │   │   │   └── vendor
│   │   │   │   │       ├── middleclass.lua
│   │   │   │   │       ├── bump.lua
│   │   │   │   │       ├── inspect.lua
│   │   │   │   │       ├── cron.lua
│   │   │   │   │       ├── beholder.lua
│   │   │   │   │       ├── version.lua
│   │   │   │   │       ├── enumerable.lua
│   │   │   │   │       ├── memoize.lua
│   │   │   │   │       ├── stateful.lua
│   │   │   │   │       ├── pulsar.lua
│   │   │   │   │       ├── mm.lua
│   │   │   │   │       ├── md5.lua
│   │   │   │   │       ├── semver.lua
│   │   │   │   │       └── serpent.lua
│   │   │   │   └── changelog.txt
│   │   │   ├── mod-list.json
│   │   │   └── headless-player_0.1.0
│   │   │       ├── locale
│   │   │       │   └── en
│   │   │       │       └── en.cfg
│   │   │       ├── description.json
│   │   │       ├── data.lua
│   │   │       ├── info.json
│   │   │       └── graphics
│   │   │           └── paperclip.png
│   │   └── main.py
│   ├── docker-compose-linux.yml
│   ├── local
│   │   ├── !README.md
│   │   ├── requirements.txt
│   │   ├── factorio_server_login.py
│   │   ├── create_docker_compose_config.py
│   │   ├── docker-compose-1.yml
│   │   ├── cluster_ips.py
│   │   ├── docker-compose-20.yml
│   │   ├── assets
│   │   │   ├── connect_to_address_button.png
│   │   │   ├── multiplayer_button.png
│   │   │   ├── connect_button.png
│   │   │   ├── quit_button.png
│   │   │   └── ip_field.png
│   │   ├── docker-compose-24.yml
│   │   └── docker-compose-33.yml
│   ├── scenarios
│   │   ├── default_lab_scenario_small
│   │   │   ├── locale
│   │   │   │   └── en
│   │   │   │       ├── level-01-locale.cfg
│   │   │   │       └── freeplay.cfg
│   │   │   ├── control.lua
│   │   │   ├── freeplay.lua
│   │   │   ├── description.json
│   │   │   ├── paperclips.lua
│   │   │   ├── planet1.png
│   │   │   ├── script.dat
│   │   │   ├── info.json
│   │   │   ├── control2.lua
│   │   │   └── blueprint.zip
│   │   ├── default_lab_scenario
│   │   │   └── README.md
│   │   └── open_world
│   │       ├── locale
│   │       │   └── en
│   │       │       ├── level-01-locale.cfg
│   │       │       └── freeplay.cfg
│   │       ├── control.lua
│   │       ├── freeplay.lua
│   │       ├── description.json
│   │       ├── paperclips.lua
│   │       ├── planet1.png
│   │       ├── script.dat
│   │       ├── info.json
│   │       ├── control2.lua
│   │       └── blueprint.zip
│   ├── docker-compose.yml
│   └── remote
│       ├── !README.md
│       ├── factorio_server_login.py
│       ├── cluster_ips.py
│       └── cluster.cloudformation.yaml
├── run.py
├── pytest.ini
├── LICENSE
├── uv.lock
├── pyproject.toml
├── agents
│   ├── basic_agent.py
│   ├── voyager
│   │   └── summary_cache
│   ├── __init__.py
│   ├── utils
│   │   ├── parse_response.py
│   │   ├── __init__.py
│   │   ├── formatters
│   │   │   ├── conversation_formatter_abc.py
│   │   │   ├── recursive_report_formatter.py
│   │   │   ├── recursive_formatter.py
│   │   │   └── __init__.py
│   │   ├── python_parser.py
│   │   ├── llm_utils.py
│   │   └── llm_factory.py
│   ├── agent_abc.py
│   └── visual_agent.py
├── pyvenv.cfg
├── mcp
├── leaderboard
│   ├── readme.md
│   ├── results
│   │   ├── llama-3.3-70b.json
│   │   ├── gpt-4o-mini.json
│   │   ├── gemini-2.json
│   │   ├── gpt-4o.json
│   │   ├── deepseek-chat.json
│   │   └── claude-3-5-sonnet.json
│   ├── public
│   │   ├── index.html
│   │   └── combined-results.json
│   ├── package-lock.json
│   ├── package.json
│   ├── build
│   │   ├── index.html
│   │   ├── combined-results.json
│   │   ├── asset-manifest.json
│   │   └── static
│   │       ├── css
│   │       │   ├── main.06c39b3c.css
│   │       │   └── main.06c39b3c.css.map
│   │       └── js
│   │           ├── main.28a2068e.js.LICENSE.txt
│   │           ├── main.28a2068e.js.map
│   │           └── main.28a2068e.js
│   ├── processed
│   │   └── combined-results.json
│   └── src
│       ├── index.js
│       ├── index.css
│       ├── components
│       │   └── Leaderboard.jsx
│       └── App.js
├── docs
│   ├── favicon.ico
│   ├── index.html
│   ├── static
│   │   ├── css
│   │   │   ├── bulma-slider.min.css
│   │   │   ├── fontawesome.all.min.css
│   │   │   ├── bulma-carousel.min.css
│   │   │   ├── academicons.min.css
│   │   │   └── bulma.min.css
│   │   └── js
│   │       ├── index.js
│   │       ├── fontawesome.all.min.js
│   │       ├── bulma-carousel.min.js
│   │       └── bulma-slider.min.js
│   └── assets
│       ├── images
│       │   ├── figure_4.png
│       │   ├── figure_5.png
│       │   ├── figure_6.png
│       │   ├── figure_2.png
│       │   ├── actions.png
│       │   ├── figure_1.png
│       │   ├── table_1.png
│       │   ├── team
│       │   │   ├── mart.png
│       │   │   ├── akbir.png
│       │   │   └── jack.png
│       │   └── repl.png
│       ├── videos
│       │   ├── compressed_2213-cropped-h264.mp4
│       │   ├── compressed_761-cropped-h264.mp4
│       │   ├── compressed_803-cropped-h264.mp4
│       │   ├── compressed_527-cropped-h264.mp4
│       │   ├── compressed_1897-cropped-h264.mp4
│       │   ├── compressed_720-cropped-h264.mp4
│       │   ├── compressed_1897-cropped.webp
│       │   ├── compressed_527-cropped.webp
│       │   ├── compressed_767-cropped-h264.mp4
│       │   ├── compressed_1891-cropped-h264.mp4
│       │   └── compressed_804-cropped-h264.mp4
│       └── documents
│           └── paper.pdf
├── README.md
├── env
│   ├── tests
│   │   ├── test_rcon_utils.py
│   │   ├── conftest.py
│   │   ├── test_warnings.py
│   │   ├── blueprints
│   │   │   ├── __init__.py
│   │   │   ├── test_save_load.py
│   │   │   └── test_blueprint_based_policies.py
│   │   ├── complex
│   │   │   ├── __init__.py
│   │   │   ├── test_slow.py
│   │   │   └── test_edge_cases.py
│   │   ├── __init__.py
│   │   ├── status
│   │   │   ├── test_pump_status.py
│   │   │   ├── test_pipes_status.py
│   │   │   ├── test_poles_status.py
│   │   │   └── __init__.py
│   │   ├── benchmarks
│   │   │   ├── benchmark_interpreter.py
│   │   │   ├── test_demo_video.py
│   │   │   ├── __init__.py
│   │   │   ├── test_elapsed_ticks.py
│   │   │   ├── test_script_caching.py
│   │   │   └── benchmark_api.py
│   │   ├── test_functions.py
│   │   ├── actions
│   │   │   ├── test_extract_item.py
│   │   │   ├── test_nearest_buildable.py
│   │   │   ├── test_request_path.py
│   │   │   ├── test_pickup_entity.py
│   │   │   ├── test_print.py
│   │   │   ├── test_sleep.py
│   │   │   ├── test_can_place.py
│   │   │   ├── test_rotate.py
│   │   │   ├── test_get_research_progress.py
│   │   │   ├── __init__.py
│   │   │   ├── test_get_prototype_recipe.py
│   │   │   ├── test_get_resource_patch.py
│   │   │   ├── test_harvest_resource.py
│   │   │   ├── test_score.py
│   │   │   ├── _test_inspect_entities.py
│   │   │   ├── test_insert_item.py
│   │   │   ├── test_set_research.py
│   │   │   ├── test_get_entities.py
│   │   │   ├── test_place_next_to_and_rotate.py
│   │   │   ├── test_get_entity.py
│   │   │   ├── test_set_entity_recipe.py
│   │   │   ├── test_place.py
│   │   │   ├── test_craft.py
│   │   │   ├── test_place_entity_next_to.py
│   │   │   ├── test_move_to.py
│   │   │   ├── test_render.py
│   │   │   ├── test_connect_entities_dry_run.py
│   │   │   ├── _test_shift_entity.py
│   │   │   ├── test_nearest.py
│   │   │   └── test_inspect_inventory.py
│   │   ├── eval
│   │   │   ├── test_achievements.py
│   │   │   ├── test_recursive_formatter.py
│   │   │   ├── _test_recursive_formatter_functional.py
│   │   │   ├── test_save_load_python_namespace.py
│   │   │   ├── __init__.py
│   │   │   ├── samplers
│   │   │   │   ├── test_weighted_reward_sampler.py
│   │   │   │   ├── __init__.py
│   │   │   │   ├── test_kld_mean_sampler.py
│   │   │   │   └── test_python_parser.py
│   │   │   ├── test_python_parser.py
│   │   │   ├── test_profits.py
│   │   │   ├── test_game_state.py
│   │   │   ├── test_mcts_chunker.py
│   │   │   ├── test_production_divergence.py
│   │   │   └── test_conversation_formatter.py
│   │   ├── test_production_stats.py
│   │   ├── connect
│   │   │   ├── test_connect_poles.py
│   │   │   ├── test_fluid_handlers.py
│   │   │   ├── test_connect_transport_belts.py
│   │   │   ├── __init__.py
│   │   │   ├── test_connect_underground_pipes.py
│   │   │   ├── test_connect_pipes.py
│   │   │   ├── test_connect_underground_belts.py
│   │   │   └── test_connect_walls.py
│   │   ├── functional
│   │   │   ├── test_defence.py
│   │   │   ├── test_objectives.py
│   │   │   ├── test_auto_fueling_iron_smelting_factory.py
│   │   │   ├── test_electricity_unit.py
│   │   │   ├── __init__.py
│   │   │   ├── test_research.py
│   │   │   ├── test_multi_drill_multi_furnace.py
│   │   │   ├── test_auto_refilling_coal.py
│   │   │   ├── test_small_iron_factory.py
│   │   │   ├── test_full_oil_chain.py
│   │   │   ├── test_multiple_drills_multiple_furnaces.py
│   │   │   ├── test_factory_unit.py
│   │   │   └── test_chemical_plants.py
│   │   ├── test_variables.py
│   │   ├── entities
│   │   │   ├── test_assemblers.py
│   │   │   ├── test_drill.py
│   │   │   ├── test_nuclear_reactor.py
│   │   │   ├── test_fluid_processors.py
│   │   │   ├── test_power_generators.py
│   │   │   ├── test_rockets.py
│   │   │   └── test_inserters.py
│   │   └── test_eval.py
│   ├── __init__.py
│   └── src
│       ├── instance.py
│       ├── tools
│       │   ├── agent.md
│       │   ├── controller.py
│       │   ├── admin
│       │   │   ├── load_research_state
│       │   │   │   ├── server.lua
│       │   │   │   └── client.py
│       │   │   ├── inspect_entities
│       │   │   │   ├── server.lua
│       │   │   │   └── deprecated
│       │   │   ├── production_stats
│       │   │   │   ├── server.lua
│       │   │   │   └── client.py
│       │   │   ├── clear_collision_boxes
│       │   │   │   ├── server.lua
│       │   │   │   └── client.py
│       │   │   ├── regenerate_resources
│       │   │   │   ├── server.lua
│       │   │   │   └── client.py
│       │   │   ├── extend_collision_boxes
│       │   │   │   ├── server.lua
│       │   │   │   └── client.py
│       │   │   ├── load_blueprint
│       │   │   │   ├── server.lua
│       │   │   │   └── client.py
│       │   │   ├── save_blueprint
│       │   │   │   ├── server.lua
│       │   │   │   └── client.py
│       │   │   ├── render
│       │   │   │   ├── agent.md
│       │   │   │   ├── server.lua
│       │   │   │   ├── layers
│       │   │   │   │   ├── natural_layer_renderer.py
│       │   │   │   │   ├── connection_layers_renderer.py
│       │   │   │   │   ├── grid_layer_renderer.py
│       │   │   │   │   ├── marker_layers_renderer.py
│       │   │   │   │   ├── layer_renderer.py
│       │   │   │   │   ├── entities_layer_renderer.py
│       │   │   │   │   ├── water_layer_renderer.py
│       │   │   │   │   └── resource_layer_renderer.py
│       │   │   │   ├── renderer.py
│       │   │   │   ├── client.py
│       │   │   │   ├── utils
│       │   │   │   │   ├── render_config.py
│       │   │   │   │   ├── tile_renderer.py
│       │   │   │   │   ├── image_calculator.py
│       │   │   │   │   ├── natural_renderer.py
│       │   │   │   │   ├── electricity_renderer.py
│       │   │   │   │   ├── entity_categoriser.py
│       │   │   │   │   ├── connection_renderer.py
│       │   │   │   │   ├── legend_renderer.py
│       │   │   │   │   ├── shape_renderer.py
│       │   │   │   │   └── colour_manager.py
│       │   │   │   └── rendered_image.py
│       │   │   ├── get_factory_centroid
│       │   │   │   ├── server.lua
│       │   │   │   ├── server2.lua
│       │   │   │   └── client.py
│       │   │   ├── observe_all
│       │   │   │   ├── server.lua
│       │   │   │   └── client.py
│       │   │   ├── clear_entities
│       │   │   │   ├── server.lua
│       │   │   │   └── client.py
│       │   │   ├── get_path
│       │   │   │   ├── server.lua
│       │   │   │   └── client.py
│       │   │   ├── save_research_state
│       │   │   │   ├── server.lua
│       │   │   │   └── client.py
│       │   │   ├── request_path
│       │   │   │   ├── server.lua
│       │   │   │   └── client.py
│       │   │   ├── save_entity_state
│       │   │   │   ├── server.lua
│       │   │   │   └── client.py
│       │   │   ├── get_production_stats
│       │   │   │   ├── server.lua
│       │   │   │   └── client.py
│       │   │   └── load_entity_state
│       │   │       ├── server.lua
│       │   │       └── client.py
│       │   ├── agent
│       │   │   ├── inspect_inventory
│       │   │   │   ├── agent.md
│       │   │   │   ├── server.lua
│       │   │   │   └── client.py
│       │   │   ├── get_entity
│       │   │   │   ├── agent.md
│       │   │   │   ├── server.lua
│       │   │   │   └── client.py
│       │   │   ├── nearest
│       │   │   │   ├── agent.md
│       │   │   │   ├── server.lua
│       │   │   │   └── client.py
│       │   │   ├── harvest_resource
│       │   │   │   ├── agent.md
│       │   │   │   ├── server.lua
│       │   │   │   └── client.py
│       │   │   ├── shift_entity
│       │   │   │   └── client.py
│       │   │   ├── craft_item
│       │   │   │   ├── agent.md
│       │   │   │   ├── server.lua
│       │   │   │   └── client.py
│       │   │   ├── place_entity_next_to
│       │   │   │   ├── agent.md
│       │   │   │   ├── server.lua
│       │   │   │   └── client.py
│       │   │   ├── sleep
│       │   │   │   ├── agent.md
│       │   │   │   ├── server.lua
│       │   │   │   └── client.py
│       │   │   ├── set_research
│       │   │   │   ├── agent.md
│       │   │   │   ├── server.lua
│       │   │   │   └── client.py
│       │   │   ├── get_research_progress
│       │   │   │   ├── agent.md
│       │   │   │   ├── server.lua
│       │   │   │   └── client.py
│       │   │   ├── rotate_entity
│       │   │   │   ├── agent.md
│       │   │   │   ├── server.lua
│       │   │   │   └── client.py
│       │   │   ├── pickup_entity
│       │   │   │   ├── agent.md
│       │   │   │   ├── server.lua
│       │   │   │   └── client.py
│       │   │   ├── get_prototype_recipe
│       │   │   │   ├── agent.md
│       │   │   │   ├── server.lua
│       │   │   │   └── client.py
│       │   │   ├── print
│       │   │   │   ├── agent.md
│       │   │   │   ├── server.lua
│       │   │   │   └── client.py
│       │   │   ├── nearest_buildable
│       │   │   │   ├── agent.md
│       │   │   │   ├── server.lua
│       │   │   │   └── client.py
│       │   │   ├── score
│       │   │   │   ├── server.lua
│       │   │   │   └── client.py
│       │   │   ├── set_entity_recipe
│       │   │   │   ├── agent.md
│       │   │   │   ├── server.lua
│       │   │   │   └── client.py
│       │   │   ├── extract_item
│       │   │   │   ├── agent.md
│       │   │   │   ├── server.lua
│       │   │   │   └── client.py
│       │   │   ├── insert_item
│       │   │   │   ├── agent.md
│       │   │   │   ├── server.lua
│       │   │   │   └── client.py
│       │   │   ├── can_place_entity
│       │   │   │   ├── agent.md
│       │   │   │   ├── server.lua
│       │   │   │   └── client.py
│       │   │   ├── get_resource_patch
│       │   │   │   ├── agent.md
│       │   │   │   ├── server.lua
│       │   │   │   └── client.py
│       │   │   ├── connect_entities
│       │   │   │   ├── agent.md
│       │   │   │   ├── server.lua
│       │   │   │   ├── client.py
│       │   │   │   ├── resolvers
│       │   │   │   │   ├── power_connection_resolver.py
│       │   │   │   │   ├── fluid_connection_resolver.py
│       │   │   │   │   └── transport_connection_resolver.py
│       │   │   │   ├── path_result.py
│       │   │   │   ├── resolver.py
│       │   │   │   └── groupable_entities.py
│       │   │   ├── get_connection_amount
│       │   │   │   ├── agent.md
│       │   │   │   ├── server.lua
│       │   │   │   └── client.py
│       │   │   ├── get_entities
│       │   │   │   ├── server.lua
│       │   │   │   └── client.py
│       │   │   ├── move_to
│       │   │   │   ├── agent.md
│       │   │   │   ├── server.lua
│       │   │   │   └── client.py
│       │   │   ├── launch_rocket
│       │   │   │   ├── agent.md
│       │   │   │   ├── server.lua
│       │   │   │   └── client.py
│       │   │   └── place_entity
│       │   │       ├── agent.md
│       │   │       ├── server.lua
│       │   │       └── client.py
│       │   ├── init.py
│       │   └── tool.py
│       ├── requirements.txt
│       ├── rcon
│       │   ├── PKG-INFO
│       │   ├── factorio_rcon_py.egg-info
│       │   │   ├── PKG-INFO
│       │   │   ├── SOURCES.txt
│       │   │   ├── requires.txt
│       │   │   ├── top_level.txt
│       │   │   └── dependency_links.txt
│       │   ├── factorio_rcon
│       │   │   ├── __init__.py
│       │   │   └── factorio_rcon.py
│       │   ├── __init__.py
│       │   ├── README.md
│       │   ├── setup.py
│       │   └── setup.cfg
│       ├── transaction.py
│       ├── utils
│       │   ├── rcon.py
│       │   ├── controller_loader
│       │   │   ├── manual_generator.py
│       │   │   ├── call_info.py
│       │   │   ├── type_definition_processor.py
│       │   │   ├── schema_generator.py
│       │   │   ├── code_analyzer.py
│       │   │   ├── system_prompt_generator.py
│       │   │   └── module_loader.py
│       │   ├── parse_llama_to_gpt.py
│       │   ├── bcolors.py
│       │   ├── achievements.py
│       │   └── profits.py
│       ├── models
│       │   ├── game_state.py
│       │   ├── technology_state.py
│       │   ├── conversation.py
│       │   ├── serializable_function.py
│       │   ├── generation_parameters.py
│       │   ├── __init__.py
│       │   ├── message.py
│       │   ├── camera.py
│       │   ├── program.py
│       │   ├── achievements.py
│       │   └── research_state.py
│       ├── exceptions
│       │   ├── hinting_name_error.py
│       │   └── insufficient_score_exception.py
│       ├── game_types.py
│       ├── lua_manager.py
│       ├── lib
│       │   ├── clear_entities.lua
│       │   ├── enemies.lua
│       │   ├── initialise.lua
│       │   ├── priority_queue.lua
│       │   ├── reset.lua
│       │   ├── alerts.lua
│       │   ├── README.md
│       │   ├── build_checkerboard.lua
│       │   ├── recipe_fluid_connection_mappings.lua
│       │   ├── clear_inventory.lua
│       │   ├── initialise_inventory.lua
│       │   ├── util.lua
│       │   ├── production_score.lua
│       │   ├── serialize.lua
│       │   ├── checksum.lua
│       │   ├── reset_position.lua
│       │   └── connection_points.lua
│       ├── gym
│       │   ├── observation_state.py
│       │   ├── test_utils.py
│       │   ├── __init__.py
│       │   ├── readme.md
│       │   ├── factorio_environment.py
│       │   ├── utils.py
│       │   └── vocabulary.py
│       ├── entities.py
│       └── namespace.py
├── CONTRIBUTING.md
├── eval
│   ├── tasks
│   │   ├── default_task.py
│   │   ├── task_factory.py
│   │   ├── supervised_results
│   │   │   └── beam_supervised
│   │   │       └── claude-3-5-sonnet-20241022
│   │   │           ├── 20250210_183724
│   │   │           ├── 20250210_183550
│   │   │           └── 20250210_183759
│   │   ├── __init__.py
│   │   ├── throughput_task.py
│   │   ├── task_definitions
│   │   │   ├── plastic_bar_throughput_16.json
│   │   │   ├── electronic_circuit_throughput_16.json
│   │   │   ├── iron_gear_wheel_throughput_16.json
│   │   │   ├── steel_plate_throughput_16.json
│   │   │   ├── stone_wall_throughput_16.json
│   │   │   ├── military_science_pack_throughput_16.json
│   │   │   ├── iron_gear_wheel_throughput_unbounded.json
│   │   │   ├── sulfur_throughput_16.json
│   │   │   ├── automation_science_pack_throughput_16.json
│   │   │   ├── iron_plate_throughput_unbounded.json
│   │   │   ├── open_play.json
│   │   │   ├── iron_plate_throughput_16.json
│   │   │   ├── iron_ore_throughput_16.json
│   │   │   ├── crude_oil_throughput_16.json
│   │   │   ├── logistics_science_pack_throughput_16.json
│   │   │   ├── petroleum_gas_throughput_16.json
│   │   │   └── inserter_throughput_16.json
│   │   ├── task_abc.py
│   │   └── unbounded_throughput_task.py
│   ├── __init__.py
│   ├── evaluator.py
│   └── open
│       ├── MANUAL_short.md
│       ├── __init__.py
│       ├── db_client.py
│       ├── beam
│       │   ├── run_milestones.py
│       │   ├── run.py
│       │   ├── __init__.py
│       │   ├── beam_search.py
│       │   ├── README.md
│       │   ├── run_parallel.py
│       │   └── beam_search_milestones.py
│       ├── MANUAL.md
│       ├── independent_runs
│       │   ├── run_config_example_lab_play.json
│       │   ├── run.py
│       │   ├── run_config_llama4_lab_play.json
│       │   ├── value_calculator.py
│       │   ├── __init__.py
│       │   ├── trajectory_runner.py
│       │   ├── run_config.json
│       │   ├── simple_evaluator.py
│       │   ├── run_config_claude3.7_lab_play.json
│       │   ├── run_config_thinking_open.json
│       │   ├── run_config_gemini2.5_lab_play.json
│       │   ├── run_vision.py
│       │   ├── run_config_thinking_vision.json
│       │   └── run_config_example_open_play.json
│       └── mcts
│           ├── instance_group.py
│           ├── parallel_mcts_config.py
│           ├── planning_mcts.py
│           ├── requirements.txt
│           ├── results.py
│           ├── blueprints_to_programs.py
│           ├── planning_models.py
│           ├── plan_generator_1.py
│           ├── mcts_factory.py
│           ├── __init__.py
│           ├── logger.py
│           ├── readme.md
│           ├── supervised_task_executor_abc.py
│           ├── objective_mcts.py
│           ├── blueprint_scenario_sampler.py
│           ├── __main__chunked.py
│           ├── parallel_mcts.py
│           ├── chunked_mcts.py
│           ├── parallel_planning_mcts.py
│           ├── samplers
│           │   ├── objective_sampler.py
│           │   ├── beam_sampler.py
│           │   ├── db_sampler.py
│           │   ├── __init__.py
│           │   ├── dynamic_reward_weighted_sampler.py
│           │   └── kld_achievement_sampler.py
│           ├── grouped_logger.py
│           ├── main.py
│           ├── __main__objective_mcts.py
│           ├── __main__planning_agent.py
│           ├── mcts.py
│           └── parallel_supervised_config.py
└── data
    ├── blueprints_to_policies
    │   ├── blueprint_metadata_generator.py
    │   ├── loop_generator.py
    │   ├── processing_state.py
    │   ├── util.py
    │   ├── parse_blueprints.py
    │   ├── __init__.py
    │   ├── models
    │   │   ├── blueprint_entity.py
    │   │   └── __init__.py
    │   ├── factorio_school.py
    │   ├── README.md
    │   ├── blueprint_analyzer.py
    │   ├── test_template.jinja2
    │   ├── blueprint_analyzer_with_connect.py
    │   ├── schema.json
    │   ├── trajectory_generator.py
    │   ├── blueprint_refactor.py
    │   └── blueprint_analyzer_with_place_next_to.py
    ├── _screenshots
    ├── plans
    │   ├── factorio_guides
    │   ├── iron_plate_factory_objectives.json
    │   ├── plan_crawler.py
    │   ├── prompts.py
    │   ├── README.md
    │   ├── objective_tree_generator.py
    │   ├── research_automation.json
    │   └── plan_parser.py
    ├── __init__.py
    ├── screenshots_to_mp4.py
    ├── recipes
    │   ├── recipes.lua
    │   └── main.py
    ├── scripts
    │   ├── init
    │   │   ├── create_ore.lua
    │   │   ├── random_map.lua
    │   │   ├── create_character.lua
    │   │   ├── mine.lua
    │   │   ├── enact_truce.lua
    │   │   ├── pollute.lua
    │   │   ├── delete_rocks.lua
    │   │   ├── reset.lua
    │   │   ├── walk.lua
    │   │   ├── revoke_truce.lua
    │   │   ├── count_all.lua
    │   │   ├── give_item.lua
    │   │   ├── clear_map.lua
    │   │   ├── create_force.lua
    │   │   └── remove_cliffs.lua
    │   ├── init.lua
    │   ├── teleport.lua
    │   ├── position.lua
    │   ├── inventory.lua
    │   ├── create_character.lua
    │   ├── day_time.lua
    │   ├── count_items.lua
    │   ├── players.lua
    │   ├── print.lua
    │   ├── get_view.lua
    │   ├── stats.lua
    │   ├── count.lua
    │   ├── count_entities.lua
    │   ├── get_associated_characters.lua
    │   ├── reveal_map.lua
    │   └── players1.lua
    ├── screenshots_from_run.py
    ├── prompts
    │   ├── self_correct_script_finetune
    │   │   ├── user_message.md
    │   │   └── system_message.md
    │   ├── finetuning_prompts
    │   │   ├── user_message.md
    │   │   ├── system_message_policy.md
    │   │   ├── user_message_synth.md
    │   │   ├── system_message_policy_synth.md
    │   │   └── system_message_steps.md
    │   ├── prompts_for_rag
    │   │   ├── recipes.md
    │   │   ├── user_message_correct.md
    │   │   ├── user_message.md
    │   │   ├── system_message_policy.md
    │   │   ├── planning_examples
    │   │   │   └── rag_functions
    │   │   │       ├── Craft 1 burner-mining-drill from scratch
    │   │   │       │   ├── input.md
    │   │   │       │   └── plan.md
    │   │   │       ├── automate_drill_to_chest
    │   │   │       │   ├── input.md
    │   │   │       │   └── plan.md
    │   │   │       ├── Connect and power electric mining drill
    │   │   │       │   ├── input.md
    │   │   │       │   └── plan.md
    │   │   │       ├── Smelt_items_with_furnace
    │   │   │       │   ├── input.md
    │   │   │       │   └── plan.md
    │   │   │       ├── Craft 1 electric-mining-drill with fixed inventory
    │   │   │       │   ├── input.md
    │   │   │       │   └── plan.md
    │   │   │       ├── Smelt_items
    │   │   │       │   ├── input.md
    │   │   │       │   └── plan.md
    │   │   │       └── automate_copper_transport_to_chest
    │   │   │           ├── input.md
    │   │   │           └── plan.md
    │   │   ├── user_message_planning.md
    │   │   ├── system_message_planning.md
    │   │   └── system_message_correct.md
    │   ├── prompts_for_notebook
    │   │   ├── finetuning_prompts
    │   │   │   ├── system_message_step_filler.md
    │   │   │   └── user_message_step_filler.md
    │   │   ├── recipes.md
    │   │   ├── user_message_step.md
    │   │   ├── system_message_step_filler.md
    │   │   ├── user_message_correct.md
    │   │   ├── system_message_step_old_backup.md
    │   │   ├── user_message_step_filler.md
    │   │   ├── planning_examples
    │   │   │   └── rag_functions
    │   │   │       ├── Create_electric_coal_mine
    │   │   │       │   ├── input.md
    │   │   │       │   └── plan.md
    │   │   │       ├── create_automatic_copper_mine copy
    │   │   │       │   ├── input.md
    │   │   │       │   └── plan.md
    │   │   │       ├── create_automatic_copper_mine
    │   │   │       │   ├── input.md
    │   │   │       │   └── plan.md
    │   │   │       ├── connect_chest_to_existing_furnaces
    │   │   │       │   ├── input.md
    │   │   │       │   └── plan.md
    │   │   │       └── assembling_machine
    │   │   │           ├── input.md
    │   │   │           └── plan.md
    │   │   ├── system_message_correct_old_backup.md
    │   │   ├── system_message_correct_filler.md
    │   │   ├── user_message_correct_filler.md
    │   │   ├── user_message_planning.md
    │   │   ├── system_message_step.md
    │   │   ├── system_message_planning.md
    │   │   ├── system_message_planning_substeps.md
    │   │   └── system_message_correct.md
    │   ├── planning
    │   │   ├── user_message.md
    │   │   └── system_message.md
    │   ├── self_correct_script_outcome
    │   │   ├── user_message.md
    │   │   └── system_message.md
    │   ├── postprocessing
    │   │   ├── backfill_objectives
    │   │   │   ├── user_message.md
    │   │   │   ├── examples
    │   │   │   │   ├── connect_things
    │   │   │   │   │   ├── snippet.py
    │   │   │   │   │   └── details.json
    │   │   │   │   └── craft_furnace
    │   │   │   │       ├── snippet.py
    │   │   │   │       └── details.json
    │   │   │   └── system_prompt.md
    │   │   └── backfill_plans
    │   │       ├── recipes.md
    │   │       ├── user_message.md
    │   │       ├── examples
    │   │       │   ├── craft_with_chest
    │   │       │   │   ├── snippet.py
    │   │       │   │   └── details.json
    │   │       │   └── create_burner_mine
    │   │       │       ├── snippet.py
    │   │       │       └── details.json
    │   │       └── system_prompt.md
    │   ├── steps_to_function
    │   │   ├── user_message.md
    │   │   ├── examples
    │   │   │   └── example_1_output.md
    │   │   └── system_message.md
    │   ├── steps_to_script
    │   │   ├── user_message.md
    │   │   └── system_message.md
    │   ├── bottoms_up_prompts
    │   │   ├── objective_generation
    │   │   │   ├── user_message.md
    │   │   │   ├── examples
    │   │   │   │   └── create_automatic_copper_mine
    │   │   │   │       ├── input.md
    │   │   │   │       └── output.md
    │   │   │   └── system_message.md
    │   │   ├── finetuning_prompts
    │   │   │   ├── step_judge
    │   │   │   │   ├── user_prompt.md
    │   │   │   │   └── system_prompt.md
    │   │   │   ├── step_supervised
    │   │   │   │   ├── user_prompt.md
    │   │   │   │   └── system_prompt.md
    │   │   │   ├── user_message_step_filler.md
    │   │   │   ├── step_generator
    │   │   │   │   ├── user_prompt.md
    │   │   │   │   └── system_prompt.md
    │   │   │   ├── system_message_policy.md
    │   │   │   ├── system_message_policy_refined.md
    │   │   │   ├── executor_plan
    │   │   │   │   ├── user_prompt.md
    │   │   │   │   └── system_prompt.md
    │   │   │   ├── system_message_policy_self_gen.md
    │   │   │   └── system_message.md
    │   │   ├── skill_generator
    │   │   │   ├── user_message.md
    │   │   │   └── system_message.md
    │   │   ├── implementation_reflection
    │   │   │   ├── system_message_old.md
    │   │   │   ├── user_message.md
    │   │   │   └── system_message.md
    │   │   └── implementation_generation
    │   │       ├── user_message.md
    │   │       └── system_message.md
    │   ├── self_correct_script_process
    │   │   ├── user_message.md
    │   │   └── system_message.md
    │   └── outcome_test
    │       ├── user_message.md
    │       └── system_message.md
    └── run_trace.py

```


---

# MCP Python SDK

<div align="center">

<strong>Python implementation of the Model Context Protocol (MCP)</strong>

[![PyPI][pypi-badge]][pypi-url]
[![MIT licensed][mit-badge]][mit-url]
[![Python Version][python-badge]][python-url]
[![Documentation][docs-badge]][docs-url]
[![Specification][spec-badge]][spec-url]
[![GitHub Discussions][discussions-badge]][discussions-url]

</div>

<!-- omit in toc -->
## Table of Contents

- [MCP Python SDK](#mcp-python-sdk)
  - [Overview](#overview)
  - [Installation](#installation)
    - [Adding MCP to your python project](#adding-mcp-to-your-python-project)
    - [Running the standalone MCP development tools](#running-the-standalone-mcp-development-tools)
  - [Quickstart](#quickstart)
  - [What is MCP?](#what-is-mcp)
  - [Core Concepts](#core-concepts)
    - [Server](#server)
    - [Resources](#resources)
    - [Tools](#tools)
    - [Prompts](#prompts)
    - [Images](#images)
    - [Context](#context)
  - [Running Your Server](#running-your-server)
    - [Development Mode](#development-mode)
    - [Claude Desktop Integration](#claude-desktop-integration)
    - [Direct Execution](#direct-execution)
    - [Mounting to an Existing ASGI Server](#mounting-to-an-existing-asgi-server)
  - [Examples](#examples)
    - [Echo Server](#echo-server)
    - [SQLite Explorer](#sqlite-explorer)
  - [Advanced Usage](#advanced-usage)
    - [Low-Level Server](#low-level-server)
    - [Writing MCP Clients](#writing-mcp-clients)
    - [MCP Primitives](#mcp-primitives)
    - [Server Capabilities](#server-capabilities)
  - [Documentation](#documentation)
  - [Contributing](#contributing)
  - [License](#license)

[pypi-badge]: https://img.shields.io/pypi/v/mcp.svg
[pypi-url]: https://pypi.org/project/mcp/
[mit-badge]: https://img.shields.io/pypi/l/mcp.svg
[mit-url]: https://github.com/modelcontextprotocol/python-sdk/blob/main/LICENSE
[python-badge]: https://img.shields.io/pypi/pyversions/mcp.svg
[python-url]: https://www.python.org/downloads/
[docs-badge]: https://img.shields.io/badge/docs-modelcontextprotocol.io-blue.svg
[docs-url]: https://modelcontextprotocol.io
[spec-badge]: https://img.shields.io/badge/spec-spec.modelcontextprotocol.io-blue.svg
[spec-url]: https://spec.modelcontextprotocol.io
[discussions-badge]: https://img.shields.io/github/discussions/modelcontextprotocol/python-sdk
[discussions-url]: https://github.com/modelcontextprotocol/python-sdk/discussions

## Overview

The Model Context Protocol allows applications to provide context for LLMs in a standardized way, separating the concerns of providing context from the actual LLM interaction. This Python SDK implements the full MCP specification, making it easy to:

- Build MCP clients that can connect to any MCP server
- Create MCP servers that expose resources, prompts and tools
- Use standard transports like stdio and SSE
- Handle all MCP protocol messages and lifecycle events

## Installation

### Adding MCP to your python project

We recommend using [uv](https://docs.astral.sh/uv/) to manage your Python projects. 

If you haven't created a uv-managed project yet, create one:

   ```bash
   uv init mcp-server-demo
   cd mcp-server-demo
   ```

   Then add MCP to your project dependencies:

   ```bash
   uv add "mcp[cli]"
   ```

Alternatively, for projects using pip for dependencies:
```bash
pip install "mcp[cli]"
```

### Running the standalone MCP development tools

To run the mcp command with uv:

```bash
uv run mcp
```

## Quickstart

Let's create a simple MCP server that exposes a calculator tool and some data:

```python
# server.py
from mcp.server.fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("Demo")


# Add an addition tool
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b


# Add a dynamic greeting resource
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    return f"Hello, {name}!"
```

You can install this server in [Claude Desktop](https://claude.ai/download) and interact with it right away by running:
```bash
mcp install server.py
```

Alternatively, you can test it with the MCP Inspector:
```bash
mcp dev server.py
```

## What is MCP?

The [Model Context Protocol (MCP)](https://modelcontextprotocol.io) lets you build servers that expose data and functionality to LLM applications in a secure, standardized way. Think of it like a web API, but specifically designed for LLM interactions. MCP servers can:

- Expose data through **Resources** (think of these sort of like GET endpoints; they are used to load information into the LLM's context)
- Provide functionality through **Tools** (sort of like POST endpoints; they are used to execute code or otherwise produce a side effect)
- Define interaction patterns through **Prompts** (reusable templates for LLM interactions)
- And more!

## Core Concepts

### Server

The FastMCP server is your core interface to the MCP protocol. It handles connection management, protocol compliance, and message routing:

```python
# Add lifespan support for startup/shutdown with strong typing
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass

from fake_database import Database  # Replace with your actual DB type

from mcp.server.fastmcp import Context, FastMCP

# Create a named server
mcp = FastMCP("My App")

# Specify dependencies for deployment and development
mcp = FastMCP("My App", dependencies=["pandas", "numpy"])


@dataclass
class AppContext:
    db: Database


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage application lifecycle with type-safe context"""
    # Initialize on startup
    db = await Database.connect()
    try:
        yield AppContext(db=db)
    finally:
        # Cleanup on shutdown
        await db.disconnect()


# Pass lifespan to server
mcp = FastMCP("My App", lifespan=app_lifespan)


# Access type-safe lifespan context in tools
@mcp.tool()
def query_db(ctx: Context) -> str:
    """Tool that uses initialized resources"""
    db = ctx.request_context.lifespan_context.db
    return db.query()
```

### Resources

Resources are how you expose data to LLMs. They're similar to GET endpoints in a REST API - they provide data but shouldn't perform significant computation or have side effects:

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("My App")


@mcp.resource("config://app")
def get_config() -> str:
    """Static configuration data"""
    return "App configuration here"


@mcp.resource("users://{user_id}/profile")
def get_user_profile(user_id: str) -> str:
    """Dynamic user data"""
    return f"Profile data for user {user_id}"
```

### Tools

Tools let LLMs take actions through your server. Unlike resources, tools are expected to perform computation and have side effects:

```python
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("My App")


@mcp.tool()
def calculate_bmi(weight_kg: float, height_m: float) -> float:
    """Calculate BMI given weight in kg and height in meters"""
    return weight_kg / (height_m**2)


@mcp.tool()
async def fetch_weather(city: str) -> str:
    """Fetch current weather for a city"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://api.weather.com/{city}")
        return response.text
```

### Prompts

Prompts are reusable templates that help LLMs interact with your server effectively:

```python
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base

mcp = FastMCP("My App")


@mcp.prompt()
def review_code(code: str) -> str:
    return f"Please review this code:\n\n{code}"


@mcp.prompt()
def debug_error(error: str) -> list[base.Message]:
    return [
        base.UserMessage("I'm seeing this error:"),
        base.UserMessage(error),
        base.AssistantMessage("I'll help debug that. What have you tried so far?"),
    ]
```

### Images

FastMCP provides an `Image` class that automatically handles image data:

```python
from mcp.server.fastmcp import FastMCP, Image
from PIL import Image as PILImage

mcp = FastMCP("My App")


@mcp.tool()
def create_thumbnail(image_path: str) -> Image:
    """Create a thumbnail from an image"""
    img = PILImage.open(image_path)
    img.thumbnail((100, 100))
    return Image(data=img.tobytes(), format="png")
```

### Context

The Context object gives your tools and resources access to MCP capabilities:

```python
from mcp.server.fastmcp import FastMCP, Context

mcp = FastMCP("My App")


@mcp.tool()
async def long_task(files: list[str], ctx: Context) -> str:
    """Process multiple files with progress tracking"""
    for i, file in enumerate(files):
        ctx.info(f"Processing {file}")
        await ctx.report_progress(i, len(files))
        data, mime_type = await ctx.read_resource(f"file://{file}")
    return "Processing complete"
```

## Running Your Server

### Development Mode

The fastest way to test and debug your server is with the MCP Inspector:

```bash
mcp dev server.py

# Add dependencies
mcp dev server.py --with pandas --with numpy

# Mount local code
mcp dev server.py --with-editable .
```

### Claude Desktop Integration

Once your server is ready, install it in Claude Desktop:

```bash
mcp install server.py

# Custom name
mcp install server.py --name "My Analytics Server"

# Environment variables
mcp install server.py -v API_KEY=abc123 -v DB_URL=postgres://...
mcp install server.py -f .env
```

### Direct Execution

For advanced scenarios like custom deployments:

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("My App")

if __name__ == "__main__":
    mcp.run()
```

Run it with:
```bash
python server.py
# or
mcp run server.py
```

### Mounting to an Existing ASGI Server

You can mount the SSE server to an existing ASGI server using the `sse_app` method. This allows you to integrate the SSE server with other ASGI applications.

```python
from starlette.applications import Starlette
from starlette.routing import Mount, Host
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("My App")

# Mount the SSE server to the existing ASGI server
app = Starlette(
    routes=[
        Mount('/', app=mcp.sse_app()),
    ]
)

# or dynamically mount as host
app.router.routes.append(Host('mcp.acme.corp', app=mcp.sse_app()))
```

For more information on mounting applications in Starlette, see the [Starlette documentation](https://www.starlette.io/routing/#submounting-routes).

## Examples

### Echo Server

A simple server demonstrating resources, tools, and prompts:

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Echo")


@mcp.resource("echo://{message}")
def echo_resource(message: str) -> str:
    """Echo a message as a resource"""
    return f"Resource echo: {message}"


@mcp.tool()
def echo_tool(message: str) -> str:
    """Echo a message as a tool"""
    return f"Tool echo: {message}"


@mcp.prompt()
def echo_prompt(message: str) -> str:
    """Create an echo prompt"""
    return f"Please process this message: {message}"
```

### SQLite Explorer

A more complex example showing database integration:

```python
import sqlite3

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("SQLite Explorer")


@mcp.resource("schema://main")
def get_schema() -> str:
    """Provide the database schema as a resource"""
    conn = sqlite3.connect("database.db")
    schema = conn.execute("SELECT sql FROM sqlite_master WHERE type='table'").fetchall()
    return "\n".join(sql[0] for sql in schema if sql[0])


@mcp.tool()
def query_data(sql: str) -> str:
    """Execute SQL queries safely"""
    conn = sqlite3.connect("database.db")
    try:
        result = conn.execute(sql).fetchall()
        return "\n".join(str(row) for row in result)
    except Exception as e:
        return f"Error: {str(e)}"
```

## Advanced Usage

### Low-Level Server

For more control, you can use the low-level server implementation directly. This gives you full access to the protocol and allows you to customize every aspect of your server, including lifecycle management through the lifespan API:

```python
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fake_database import Database  # Replace with your actual DB type

from mcp.server import Server


@asynccontextmanager
async def server_lifespan(server: Server) -> AsyncIterator[dict]:
    """Manage server startup and shutdown lifecycle."""
    # Initialize resources on startup
    db = await Database.connect()
    try:
        yield {"db": db}
    finally:
        # Clean up on shutdown
        await db.disconnect()


# Pass lifespan to server
server = Server("example-server", lifespan=server_lifespan)


# Access lifespan context in handlers
@server.call_tool()
async def query_db(name: str, arguments: dict) -> list:
    ctx = server.request_context
    db = ctx.lifespan_context["db"]
    return await db.query(arguments["query"])
```

The lifespan API provides:
- A way to initialize resources when the server starts and clean them up when it stops
- Access to initialized resources through the request context in handlers
- Type-safe context passing between lifespan and request handlers

```python
import mcp.server.stdio
import mcp.types as types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions

# Create a server instance
server = Server("example-server")


@server.list_prompts()
async def handle_list_prompts() -> list[types.Prompt]:
    return [
        types.Prompt(
            name="example-prompt",
            description="An example prompt template",
            arguments=[
                types.PromptArgument(
                    name="arg1", description="Example argument", required=True
                )
            ],
        )
    ]


@server.get_prompt()
async def handle_get_prompt(
    name: str, arguments: dict[str, str] | None
) -> types.GetPromptResult:
    if name != "example-prompt":
        raise ValueError(f"Unknown prompt: {name}")

    return types.GetPromptResult(
        description="Example prompt",
        messages=[
            types.PromptMessage(
                role="user",
                content=types.TextContent(type="text", text="Example prompt text"),
            )
        ],
    )


async def run():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="example",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(run())
```

### Writing MCP Clients

The SDK provides a high-level client interface for connecting to MCP servers:

```python
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client

# Create server parameters for stdio connection
server_params = StdioServerParameters(
    command="python",  # Executable
    args=["example_server.py"],  # Optional command line arguments
    env=None,  # Optional environment variables
)


# Optional: create a sampling callback
async def handle_sampling_message(
    message: types.CreateMessageRequestParams,
) -> types.CreateMessageResult:
    return types.CreateMessageResult(
        role="assistant",
        content=types.TextContent(
            type="text",
            text="Hello, world! from model",
        ),
        model="gpt-3.5-turbo",
        stopReason="endTurn",
    )


async def run():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(
            read, write, sampling_callback=handle_sampling_message
        ) as session:
            # Initialize the connection
            await session.initialize()

            # List available prompts
            prompts = await session.list_prompts()

            # Get a prompt
            prompt = await session.get_prompt(
                "example-prompt", arguments={"arg1": "value"}
            )

            # List available resources
            resources = await session.list_resources()

            # List available tools
            tools = await session.list_tools()

            # Read a resource
            content, mime_type = await session.read_resource("file://some/path")

            # Call a tool
            result = await session.call_tool("tool-name", arguments={"arg1": "value"})


if __name__ == "__main__":
    import asyncio

    asyncio.run(run())
```

### MCP Primitives

The MCP protocol defines three core primitives that servers can implement:

| Primitive | Control               | Description                                         | Example Use                  |
|-----------|-----------------------|-----------------------------------------------------|------------------------------|
| Prompts   | User-controlled       | Interactive templates invoked by user choice        | Slash commands, menu options |
| Resources | Application-controlled| Contextual data managed by the client application   | File contents, API responses |
| Tools     | Model-controlled      | Functions exposed to the LLM to take actions        | API calls, data updates      |

### Server Capabilities

MCP servers declare capabilities during initialization:

| Capability  | Feature Flag                 | Description                        |
|-------------|------------------------------|------------------------------------|
| `prompts`   | `listChanged`                | Prompt template management         |
| `resources` | `subscribe`<br/>`listChanged`| Resource exposure and updates      |
| `tools`     | `listChanged`                | Tool discovery and execution       |
| `logging`   | -                            | Server logging configuration       |
| `completion`| -                            | Argument completion suggestions    |

## Documentation

- [Model Context Protocol documentation](https://modelcontextprotocol.io)
- [Model Context Protocol specification](https://spec.modelcontextprotocol.io)
- [Officially supported servers](https://github.com/modelcontextprotocol/servers)

## Contributing

We are passionate about supporting contributors of all levels of experience and would love to see you get involved in the project. See the [contributing guide](CONTRIBUTING.md) to get started.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
