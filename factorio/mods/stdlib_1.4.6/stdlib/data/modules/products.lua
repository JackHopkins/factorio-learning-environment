local table = require('stdlib/utils/table')

-- Creates the middle man products table
local Products = {
    __class = 'Products',
    __index = require('stdlib/data/data'),
    Parent = nil,
    Results = nil,
    Ingredients = nil,

}
setmetatable(Products, Products)

local ProductData = require('stdlib/data/modules/product-data')

function Products:Parent()
    return self.parent
end

function Products:Results()
    return self.parent:Results()
end

function Products:Ingredients()
    return self.parent:Ingredients()
end

local function format_base(ingredients)
    local new = {}
    for _, ing in pairs(ingredients) do
        if ing.name then
            new[#new + 1] = table.deepcopy(ing)
        elseif #ing > 0 then
            new[#new + 1] = {type = 'item', name = ing[1], amount = ing[2]}
        end
    end
    return new
end

local function format_base_results(products, difficulty)
    local new = {}
    difficulty = difficulty and products.parent[difficulty]
    if difficulty then
        if difficulty.results then
            return format_base(products.parent[difficulty].results)
        end
        new[#new + 1] = {type = 'item', name = difficulty.result, amount = difficulty.result_count or 1}
    else
        if products.parent.results then
            return format_base(products.parent.results)
        end
        new[#new + 1] = {type = 'item', name = products.parent.result, amount = products.parent.result_count or 1}
    end
    return new
end

Products._mt = {
    __index = function(_, k)
        if ProductData[k] ~= nil then
            return ProductData[k]
        end
        return Products[k]
    end,
    __class = 'products'
}
--Gets a single ingredient
function Products:__call(parent, product_type)
    if parent.products then
        return parent.products[product_type]
    end
    local products = {
        __class = 'products',
        parent = parent,
        ingredients = {},
        results = {}
    }
    products.__index = products
    setmetatable(products, Products._mt)

    local meta = {
        ingredients = {
            __class = 'ingredients',
            __index = products,
            __tostring = ProductData._mt.__tostring,
            __call = self.Parent,
            __len = ProductData._mt.__len
        },
        results = {
            __class = 'results',
            __index = products,
            __tostring = ProductData._mt.__tostring,
            __call = self.Parent,
            __len = ProductData._mt.__len
        }
    }

    setmetatable(products.ingredients, meta.ingredients)
    setmetatable(products.results, meta.results)

    rawset(parent, 'products', products)

    if parent:is_valid('recipe') then
        if parent.normal then
            products.ingredients.normal = format_base(parent.normal.ingredients)
            products.ingredients.expensive = format_base(parent.expensive.ingredients)
            products.results.normal = format_base_results(products, 'normal')
            products.results.expensive = format_base_results(products, 'expensive')
        else
            products.ingredients.regular = format_base(parent.ingredients)
            products.results.regular = format_base_results(products)
        end
    end
    return products[product_type]
end

return Products
