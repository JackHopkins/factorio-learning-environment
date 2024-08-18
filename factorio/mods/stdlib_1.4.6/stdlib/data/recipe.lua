--- Recipe class
-- @classmod Data.Recipe

local Data = require('__stdlib__/stdlib/data/data')
local Table = require('__stdlib__/stdlib/utils/table')

local Recipe = {
    __class = 'Recipe',
    __index = Data,
}

function Recipe:__call(recipe)
    local new = self:get(recipe, 'recipe')
    -- rawset(new, 'Ingredients', {})
    -- rawset(new, 'Results', {})
    return new
end
setmetatable(Recipe, Recipe)

-- Returns a formated ingredient or prodcut table
local function format(ingredient, result_count)
    local Item = require('__stdlib__/stdlib/data/item')
    local object
    if type(ingredient) == 'table' then
        if ingredient.valid and ingredient:is_valid() then
            return ingredient
        elseif ingredient.name then
            if Item(ingredient.name, ingredient.type):is_valid() then
                object = Table.deepcopy(ingredient)
                if not object.amount and not (object.amount_min and object.amount_max and object.probability) then
                    error('Result table requires amount or probabilities')
                end
            end
        elseif #ingredient > 0 then
            -- Can only be item types not fluid
            local item = Item(ingredient[1])
            if item:is_valid() and item.type ~= 'fluid' then
                object = {
                    type = 'item',
                    name = ingredient[1],
                    amount = ingredient[2] or 1
                }
            end
        end
    elseif type(ingredient) == 'string' then
        -- Our shortcut so we need to check it
        local item = Item(ingredient)
        if item:is_valid() then
            object = {
                type = item.type == 'fluid' and 'fluid' or 'item',
                name = ingredient,
                amount = result_count or 1
            }
        end
    end
    return object
end

-- Format items for difficulties
-- If expensive is a boolean then return a copy of normal for expensive
local function get_difficulties(normal, expensive)
    return format(normal), format((expensive == true and Table.deepcopy(normal)) or expensive)
end

--- Remove an ingredient from an ingredients table.
-- @tparam table ingredients
-- @tparam string name Name of the ingredient to remove
local function remove_ingredient(ingredients, name)
    name = name.name
    for i, ingredient in pairs(ingredients or {}) do
        if ingredient[1] == name or ingredient.name == name then
            ingredients[i] = nil
            return true
        end
    end
end

--- Replace an ingredient.
-- @tparam table ingredients Ingredients table
-- @tparam string find ingredient to replace
-- @tparam concepts.ingredient replace
-- @tparam boolean replace_name_only Don't replace amounts
local function replace_ingredient(ingredients, find, replace, replace_name_only)
    for i, ingredient in pairs(ingredients or {}) do
        if ingredient[1] == find or ingredient.name == find then
            if replace_name_only then
                local amount = ingredient[2] or ingredient.amount
                replace.amount = amount
            end
            ingredients[i] = replace
            return true
        end
    end
end

--- Add an ingredient to a recipe.
-- @tparam string|Concepts.ingredient normal
-- @tparam[opt] string|Concepts.ingredient|boolean expensive
-- @treturn Recipe
function Recipe:add_ingredient(normal, expensive)
    if self:is_valid() then
        normal, expensive = get_difficulties(normal, expensive)

        if self.normal then
            if normal then
                self.normal.ingredients = self.normal.ingredients or {}
                self.normal.ingredients[#self.normal.ingredients + 1] = normal
            end
            if expensive then
                self.expensive.ingredients = self.expensive.ingredients or {}
                self.expensive.ingredients[#self.expensive.ingredients + 1] = expensive
            end
        elseif normal then
            self.ingredients = self.ingredients or {}
            self.ingredients[#self.ingredients + 1] = normal
        end
    end
    return self
end
Recipe.add_ing = Recipe.add_ingredient

--- Remove one ingredient completely.
-- @tparam string normal
-- @tparam string|boolean expensive expensive recipe to remove, or if true remove normal recipe from both
-- @treturn Recipe
function Recipe:remove_ingredient(normal, expensive)
    if self:is_valid() then
        normal, expensive = get_difficulties(normal, expensive)
        if self.normal then
            if normal then
                remove_ingredient(self.normal.ingredients, normal)
            end
            if expensive then
                remove_ingredient(self.expensive.ingredients, expensive)
            end
        elseif normal then
            remove_ingredient(self.ingredients, normal)
        end
    end
    return self
end
Recipe.rem_ing = Recipe.remove_ingredient

--- Replace one ingredient with another.
-- @tparam string replace
-- @tparam string|ingredient normal
-- @tparam[opt] string|ingredient|boolean expensive
function Recipe:replace_ingredient(replace, normal, expensive)
    assert(replace, 'Missing recipe to replace')
    if self:is_valid() then
        local n_string = type(normal) == 'string'
        local e_string = type(expensive == true and normal or expensive) == 'string'
        normal, expensive = get_difficulties(normal, expensive)
        if self.normal then
            if normal then
                replace_ingredient(self.normal.ingredients, replace, normal, n_string)
            end
            if expensive then
                replace_ingredient(self.expensive.ingredients, replace, expensive, e_string)
            end
        elseif normal then
            replace_ingredient(self.ingredients, replace, normal, n_string)
        end
    end
    return self
end
Recipe.rep_ing = Recipe.replace_ingredient

-- Currently does no checking
function Recipe:clear_ingredients()
    if self:is_valid() then
        if self.normal then
            if self.normal.ingredients then
                self.normal.ingredients = {}
            end
            if self.expensive.ingredients then
                self.expensive.ingredients = {}
            end
        elseif self.ingredients then
            self.ingredients = {}
        end
    end
    return self
end

--- Converts a recipe to the difficulty recipe format.
-- @tparam[opt] number expensive_energy crafting energy_required for the expensive recipe
-- @treturn self
function Recipe:make_difficult(expensive_energy)
    if self:is_valid('recipe') and not self.normal then
        --convert all ingredients
        local normal, expensive = {}, {}
        for _, ingredient in ipairs(self.ingredients) do
            local this = format(ingredient)
            normal[#normal + 1] = this
            expensive[#expensive + 1] = Table.deepcopy(this)
        end

        local r_normal, r_expensive = {}, {}
        for _, ingredient in ipairs(self.results or {self.result}) do
            local this = format(ingredient)
            r_normal[#r_normal + 1] = this
            r_expensive[#r_expensive + 1] = Table.deepcopy(this)
        end

        self.normal = {
            enabled = self.enabled,
            energy_required = self.energy_required,
            ingredients = normal,
            results = r_normal,
            main_product = self.main_product
        }
        self.expensive = {
            enabled = self.enabled,
            energy_required = expensive_energy or self.energy_required,
            ingredients = expensive,
            results = r_expensive,
            main_product = self.main_product
        }

        self.ingredients = nil
        self.result = nil
        self.results = nil
        self.result_count = nil
        self.energy_required = nil
        self.enabled = nil
        self.main_product = nil
    end
    return self
end

--- Change the recipe category.
-- @tparam string category_name The new crafting category
-- @treturn self
function Recipe:change_category(category_name)
    if self:is_valid() then
        local Category = require('__stdlib__/stdlib/data/category')
        self.category = Category(category_name, 'recipe-category'):is_valid() and category_name or self.category
    end
    return self
end
Recipe.set_category = Recipe.change_category

--- Add to technology as a recipe unlock.
-- @tparam string tech_name Name of the technology to add the unlock too
-- @treturn self
function Recipe:add_unlock(tech_name)
    if self:is_valid() then
        local Tech = require('__stdlib__/stdlib/data/technology')
        Tech.add_effect(self, tech_name) --self is passed as a valid recipe
    end
    return self
end

--- Remove the recipe unlock from the technology.
-- @tparam string tech_name Name of the technology to remove the unlock from
-- @treturn self
function Recipe:remove_unlock(tech_name)
    if self:is_valid('recipe') then
        local Tech = require('__stdlib__/stdlib/data/technology')
        Tech.remove_effect(self, tech_name, 'unlock-recipe')
    end
    return self
end

--- Set the enabled status of the recipe.
-- @tparam boolean enabled Enable or disable the recipe
-- @treturn self
function Recipe:set_enabled(enabled)
    if self:is_valid() then
        if self.normal then
            self.normal.enabled = enabled
            self.expensive.enabled = enabled
        else
            self.enabled = enabled
        end
    end
    return self
end

--- Convert result type to results type.
-- @treturn self
function Recipe:convert_results()
    if self:is_valid('recipe') then
        if self.normal then
            if self.normal.result then
                self.normal.results = {
                    format(self.normal.result, self.normal.result_count or 1)
                }
                self.normal.result = nil
                self.normal.result_count = nil
            end
            if self.expensive.result then
                self.expensive.results = {
                    format(self.expensive.result, self.expensive.result_count or 1)
                }
                self.expensive.result = nil
                self.expensive.result_count = nil
            end
        elseif self.result then
            self.results = {
                format(self.result, self.result_count or 1)
            }
            self.result = nil
            self.result_count = nil
        end
    end
    return self
end

--- Set the main product of the recipe.
-- @tparam string|boolean main_product if boolean then use normal/expensive recipes passed as main product
-- @tparam[opt] Concepts.Product|string normal recipe
-- @tparam[opt] Concepts.Product|string expensive recipe
-- @treturn self
function Recipe:set_main_product(main_product, normal, expensive)
    if self:is_valid('recipe') then
        normal, expensive = get_difficulties(normal, expensive)
        local normal_main, expensive_main
        if main_product then
            local Item = require('__stdlib__/stdlib/data/item')
            if type(main_product) == 'string' and Item(main_product):is_valid() then
                normal_main = normal and main_product
                expensive_main = expensive and main_product
            elseif type(main_product) == 'boolean' then
                normal_main = normal and Item(normal.name):is_valid() and normal.name
                expensive_main = expensive and Item(expensive.name):is_valid() and expensive.name
            end
            if self.normal then
                self.normal.main_product = normal_main
                self.expensive.main_product = expensive_main
            else
                self.main_product = normal_main
            end
        end
    end
    return self
end

--- Remove the main product of the recipe.
-- @tparam[opt=false] boolean for_normal
-- @tparam[opt=false] boolean for_expensive
function Recipe:remove_main_product(for_normal, for_expensive)
    if self:is_valid('recipe') then
        if self.normal then
            if for_normal or (for_normal == nil and for_expensive == nil) then
                self.normal.main_product = nil
            end
            if for_expensive or (for_normal == nil and for_expensive == nil) then
                self.expensive.main_product = nil
            end
        elseif for_normal or (for_normal == nil and for_expensive == nil) then
            self.main_product = nil
        end
    end
    return self
end

--- Add a new product to results, converts if needed.
-- @tparam string|Concepts.product normal
-- @tparam[opt] string|Concepts.product|boolean expensive
-- @tparam[opt] string main_product
function Recipe:add_result(normal, expensive, main_product)
    if self:is_valid() then
        normal, expensive = get_difficulties(normal, expensive)
        self:convert_results()
        self:set_main_product(main_product, normal, expensive)

    -- if self.normal then
    --     if normal then
    --     end
    --     if expensive then
    --     end
    -- elseif normal then
    -- end
    end
    return self
end

--- Remove a product from results, converts if needed.
-- @tparam[opt] string|Concepts.product normal
-- @tparam[opt] string|Concepts.product|boolean expensive
-- @tparam[opt] string main_product new main_product to use
function Recipe:remove_result(normal, expensive, main_product)
    if self:is_valid() then
        normal, expensive = get_difficulties(normal, expensive)
        self:convert_results()
        self:set_main_product(main_product, normal, expensive)

    -- if self.normal then
    --     if normal then
    --     end
    --     if expensive then
    --     end
    -- elseif normal then
    -- end
    end
    return self
end

--- Remove a product from results, converts if needed.
-- @tparam string|Concepts.product result_name
-- @tparam[opt] string|Concepts.product normal
-- @tparam[opt] string|Concepts.product|boolean expensive
-- @tparam[opt] string main_product
function Recipe:replace_result(result_name, normal, expensive, main_product)
    if self:is_valid() and normal or expensive then
        result_name = format(result_name)
        if result_name then
            normal, expensive = get_difficulties(normal, expensive)
            self:convert_results()
            self:remove_result(result_name, expensive and result_name)
            self:set_main_product(main_product, normal, expensive)

        -- if self.normal then
        --     if normal then
        --     end
        --     if expensive then
        --     end
        -- elseif normal then
        -- end
        end
    end
    return self
end

return Recipe
