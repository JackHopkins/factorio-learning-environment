--- Entity class
-- @classmod Data.Entity

local Data = require('__stdlib__/stdlib/data/data')

local Entity = {
    __class = 'Entity',
    __index = Data,
    __call = Data.__call
}
setmetatable(Entity, Entity)

function Entity:get_minable_item()
    local Item = require('__stdlib__/stdlib/data/item')
    if self:is_valid() then
        local m = self.minable
        return Item(m and (m.result or (m.results and (m.results[1] or m.results.name))), nil, self.options)
    end
    return Item()
end

function Entity:is_player_placeable()
    if self:is_valid() then
        return self:Flags():any('player-creation', 'placeable-player')
    end
    return false
end

function Entity:change_lab_inputs(name, add)
    if self:is_valid('lab') then
        Entity.Unique_Array.set(self.inputs)
        if add then
            self.inputs:add(name)
        else
            self.inputs:remove(name)
        end
    else
        log('Entity is not a lab.' .. _G.data_traceback())
    end
    return self
end

return Entity
