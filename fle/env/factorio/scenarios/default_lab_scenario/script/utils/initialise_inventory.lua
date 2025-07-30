global.actions.initialise_inventory = function(player_index, item_names_and_counts_json)
    local player = global.agent_characters[player_index]
    local item_names_and_counts = game.json_to_table(item_names_and_counts_json)

    -- Loop through the entity names and insert them into the player's inventory
    for item, count in pairs(item_names_and_counts) do
        player.get_main_inventory().insert{name=item, count=count}
    end
end