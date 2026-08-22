-- Lightweight entity census: name -> {status -> count} for the player
-- force, without serializing full entity attributes. Used by the verifier's
-- per-intervention telemetry when no objective needs entity details.

storage.actions.entity_census = function(player_index)
    local character = storage.agent_characters[player_index]
    if not character or not character.valid then
        return {census = {}, total = 0}
    end
    local force = character.force
    local surface = game.surfaces["nauvis"]
    local entities = surface.find_entities_filtered({force = force})
    local census = {}
    local total = 0
    for _, entity in pairs(entities) do
        if entity.valid then
            local name = entity.name
            local status_name = "unknown"
            local ok, converted = pcall(function()
                return storage.utils.entity_status_names(entity.status)
            end)
            if ok and converted ~= nil then
                status_name = tostring(converted)
                -- Values arrive JSON-quoted from the shared helper.
                status_name = status_name:gsub('^"', ""):gsub('"$', "")
            end
            census[name] = census[name] or {}
            census[name][status_name] = (census[name][status_name] or 0) + 1
            total = total + 1
        end
    end
    return {census = census, total = total}
end
