--- Migration helper functions
-- @module Misc.Migrate

local Migrate = {
    __class = 'Migrate',
    __index = require('__stdlib__/stdlib/core')
}
setmetatable(Migrate, Migrate)

local Is = require('__stdlib__/stdlib/utils/is')

--- Migrate a dictionary of recipe -> tech names
-- @tparam dictionary dictionary
function Migrate.Recipes(dictionary)
    Is.Assert.Table(dictionary, 'dictionary of recipes->technology not found')
    for _, force in pairs(game.forces) do
        for recipe, tech in pairs(dictionary) do
            if force.technologies[tech] and force.technologies[tech].researched then
                if force.recipes[recipe] then
                    force.recipes[recipe].enabled = true
                end
            end
        end
    end
end

function Migrate.all_recipes()
    for _, force in pairs(game.forces) do
        for _, tech in pairs(force.technologies) do
            if tech.researched then
                for _, unlock in pairs(tech.effects or {}) do
                    if unlock.type == 'unlock-recipe' then
                        force.recipes[unlock.recipe].enabled = true
                    end
                end
            end
        end
    end
end

return Migrate
