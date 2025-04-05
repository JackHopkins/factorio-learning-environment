-- Character Registry System
if not global.character_registry then
    global.character_registry = {
        ordered_characters = {},  -- Array to maintain order
        character_map = {},       -- Map for quick lookups
        player_to_characters = {} -- Map player_index to their character unit_numbers
    }
end

-- Register event handlers when the mod loads
script.on_event(defines.events.on_entity_created, function(event)
    local entity = event.entity
    if entity and entity.type == "character" then
        register_character(entity)
    end
end)

-- Function to register a new character
function register_character(character)
    local unit_number = character.unit_number
    local player = character.player
    
    -- Add to ordered list
    table.insert(global.character_registry.ordered_characters, unit_number)
    
    -- Add to lookup map
    global.character_registry.character_map[unit_number] = {
        entity = character,
        index = #global.character_registry.ordered_characters
    }
    
    -- If character belongs to a player, track that relationship
    if player then
        if not global.character_registry.player_to_characters[player.index] then
            global.character_registry.player_to_characters[player.index] = {}
        end
        table.insert(global.character_registry.player_to_characters[player.index], unit_number)
    end
    
    return #global.character_registry.ordered_characters  -- Return the index instead of unit_number
end

-- Function to get character by index (maintains order)
function get_character_by_index(index)
    local unit_number = global.character_registry.ordered_characters[index]
    if unit_number then
        return global.character_registry.character_map[unit_number].entity
    end
    return nil
end

-- Function to get character by unit number
function get_character_by_unit_number(unit_number)
    return global.character_registry.character_map[unit_number] and 
           global.character_registry.character_map[unit_number].entity or nil
end

-- Function to get all characters for a player
function get_player_characters(player_index)
    local unit_numbers = global.character_registry.player_to_characters[player_index] or {}
    local characters = {}
    for _, unit_number in ipairs(unit_numbers) do
        table.insert(characters, get_character_by_unit_number(unit_number))
    end
    return characters
end

-- Function to get the primary character for a player (first one registered)
function get_primary_character(player_index)
    local unit_numbers = global.character_registry.player_to_characters[player_index]
    if unit_numbers and #unit_numbers > 0 then
        return get_character_by_unit_number(unit_numbers[1])
    end
    return nil
end

-- Export functions to global namespace
global.character_registry.get_character_by_index = get_character_by_index
global.character_registry.get_character_by_unit_number = get_character_by_unit_number
global.character_registry.get_player_characters = get_player_characters
global.character_registry.get_primary_character = get_primary_character 