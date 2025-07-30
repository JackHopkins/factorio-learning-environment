-- Helper function to get fluid type from ingredient/product
local function get_fluid_type(item)
    if item.type == "fluid" then
        return item.name
    end
    return nil
end

-- Helper function to get position offsets based on fluid type and recipe
local function get_refinery_position_offsets(fluid_type, recipe, is_input)
    -- Basic oil processing
    if #recipe.ingredients == 1 then
        if not is_input then
            return 2, -3  -- Top right
        else
            return 1, 3 -- Bottom right
        end
    end

    -- game.print(serpent.block(recipe.ingredients))
    -- Advanced oil processing
    if #recipe.ingredients == 2 and recipe.ingredients[2].name == "crude-oil" then
        if is_input then
            if fluid_type == "crude-oil" then
                return 1, 3  -- Top left
            else
                return -1, 3   -- Top right (water)
            end
        else
            if fluid_type == "heavy-oil" then
                return -2, -3     -- Bottom left
            elseif fluid_type == "light-oil" then
                return 0, -3      -- Bottom middle
            else
                return 2, -3      -- Bottom right (heavy oil)
            end
        end
    end

    -- Coal liquefaction
    if #recipe.ingredients == 3 and recipe.ingredients[3].name == "steam" then
        if is_input then
            if fluid_type == "steam" then
                return 1, 3  -- Top left
            else
                return -1, 3   -- Top right (heavy oil)
            end
        else
            if fluid_type == "petroleum-gas" then
                return -2, -3     -- Bottom left
            elseif fluid_type == "light-oil" then
                return 0, -3      -- Bottom middle
            else
                return 2, -3      -- Bottom right (heavy oil)
            end
        end
    end
    return 0,0
end

-- Helper function to get chemical plant position offsets
local function get_chemical_plant_position_offsets(index, total, is_input)
    if is_input then
        if total == 1 then
            return -1, -1.5  -- Bottom left for single input
        else
            -- For two inputs, space them out
            return -1 + (index - 1) * 2, -1.5
        end
    else
        -- Outputs always go on the left side
        return -1, 1.5
    end
end

-- Helper function to rotate coordinates based on entity direction
local function rotate_coordinates(x_offset, y_offset, direction)
    if direction == defines.direction.north then
        return x_offset, y_offset
    elseif direction == defines.direction.south then
        return -x_offset, -y_offset
    elseif direction == defines.direction.east then
        return -y_offset, x_offset
    elseif direction == defines.direction.west then
        return y_offset, -x_offset
    end
end

global.utils.get_refinery_fluid_mappings = function(entity, recipe)
    if not entity or not recipe then return nil end
    if not entity.position then return nil end

    local x, y = entity.position.x, entity.position.y
    local input_points = {}
    local output_points = {}

    -- Map inputs
    for _, ingredient in pairs(recipe.ingredients) do
        if ingredient.type == "fluid" then
            local x_offset, y_offset = get_refinery_position_offsets(ingredient.name, recipe, true)
            local rotated_x, rotated_y = rotate_coordinates(x_offset, y_offset, entity.direction)
            table.insert(input_points, {
                x = x + rotated_x,
                y = y + rotated_y,
                type = "\""..ingredient.name.."\""
            })
        end
    end

    -- Map outputs
    for _, product in pairs(recipe.products) do
        if product.type == "fluid" then
            local x_offset, y_offset = get_refinery_position_offsets(product.name, recipe, false)
            local rotated_x, rotated_y = rotate_coordinates(x_offset, y_offset, entity.direction)
            table.insert(output_points, {
                x = x + rotated_x,
                y = y + rotated_y,
                type = "\""..product.name.."\""
            })
        end
    end

    return {
        inputs = input_points,
        outputs = output_points
    }
end

-- Helper function to map connection points to fluid types for chemical plant
global.utils.get_chemical_plant_fluid_mappings = function(entity, recipe)
    if not entity or not recipe then return nil end
    if not entity.position then return nil end

    local x, y = entity.position.x, entity.position.y
    local input_points = {}
    local output_points = {}

    -- Count fluid inputs
    local fluid_inputs = {}
    for _, ingredient in pairs(recipe.ingredients) do
        if ingredient.type == "fluid" then
            table.insert(fluid_inputs, ingredient)
        end
    end

    -- Map inputs
    for i, ingredient in ipairs(fluid_inputs) do
        local x_offset, y_offset = get_chemical_plant_position_offsets(i, #fluid_inputs, true)
        local rotated_x, rotated_y = rotate_coordinates(x_offset, y_offset, entity.direction)
        table.insert(input_points, {
            x = x + rotated_x,
            y = y + rotated_y,
            type = "\""..ingredient.name.."\""
        })
    end

    -- Map outputs
    for _, product in pairs(recipe.products) do
        if product.type == "fluid" then
            local x_offset, y_offset = get_chemical_plant_position_offsets(1, 1, false)
            local rotated_x, rotated_y = rotate_coordinates(x_offset, y_offset, entity.direction)
            table.insert(output_points, {
                x = x + rotated_x,
                y = y + rotated_y,
                type = "\""..product.name.."\""
            })
        end
    end

    return {
        inputs = input_points,
        outputs = output_points
    }
end