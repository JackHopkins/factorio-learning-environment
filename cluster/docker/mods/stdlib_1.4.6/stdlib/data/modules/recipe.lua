local Recipe = {
    __class = 'Recipe',
    __index = require('stdlib/data/data'),
    __call = function(self, recipe) return self:get(recipe, 'recipe') end
}
setmetatable(Recipe, Recipe)

-- luacheck: ignore

local Is = require('stdlib/utils/is')
local Item = require('stdlib/data/item')

-- function Recipe:__call(recipe)
--     local new = self:get(recipe, 'recipe')
--     rawset(new, 'is_difficult', new.normal ~= nil)
--     return new
-- end

local Products = require('stdlib/data/modules/products')

function Recipe:Ingredients()
    return Products(self, 'ingredients')
end
Recipe.Ing = Recipe.Ingredients

function Recipe:Results()
    return Products(self, 'results')
end

return Recipe
