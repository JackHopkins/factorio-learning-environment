local M = {}

M.events = {}

M.actions = {}

M.actions.get_prototype_recipe = function(player_index, recipe_name)
    local player = global.agent_characters[player_index]
    local recipe = player.force.recipes[recipe_name]
    if not recipe then
        return "recipe doesnt exist"
    end
    local serialized = utils.serialize_recipe(recipe)
    return serialized
end

return M
