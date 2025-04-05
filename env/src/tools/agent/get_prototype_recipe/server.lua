global.actions.get_prototype_recipe = function(character_index, recipe_name)
    local character = global.character_registry.get_character_by_index(character_index)
    if not character then
        error("Character not found in registry at index " .. character_index)
    end
    
    local recipe = character.force.recipes[recipe_name]
    if not recipe then
        return "recipe doesnt exist"
    end
    local serialized = global.utils.serialize_recipe(recipe)
    return serialized
end

