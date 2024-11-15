--item.lua

local paperclip = table.deepcopy(data.raw["item"]["iron-gear-wheel"])
paperclip.name = "paperclip"
paperclip.type = "item"
paperclip.stack_size = 1000
paperclip.icons = {
  {
    icon = "__headless-player__/graphics/paperclip.png",
    icon_size = 128
  },
}

local recipe = table.deepcopy(data.raw["recipe"]["iron-gear-wheel"])
recipe.name = "recipe-paperclip"
recipe.enabled = true
recipe.icons = {
  {
    icon = "__headless-player__/graphics/paperclip.png",
    icon_size = 128
  }
}
recipe.ingredients = {{"iron-plate",2}}
recipe.result = "paperclip"

data:extend{paperclip,recipe}