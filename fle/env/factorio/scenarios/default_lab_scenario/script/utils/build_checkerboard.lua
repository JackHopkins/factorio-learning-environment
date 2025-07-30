local player = global.agent_characters[arg1]
local surface = player.surface

surface.build_checkerboard({{-100, -100}, {100, 100}})