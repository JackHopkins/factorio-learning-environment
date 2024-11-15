--- Technology
-- @classmod Data.Technology

local Data = require('__stdlib__/stdlib/data/data')

local Technology = {
    __class = 'Technology',
    __index = Data,
}

function Technology:__call(tech)
    return self:get(tech, 'technology')
end
setmetatable(Technology, Technology)

function Technology:add_effect(effect, unlock_type)
    assert(effect)

    --todo fix for non recipe types
    local add_unlock =
        function(technology, name)
        local effects = technology.effects
        effects[#effects + 1] = {
            type = unlock_type,
            recipe = name
        }
    end

    if self:is_valid('technology') then
        local Recipe = require('__stdlib__/stdlib/data/recipe')
        unlock_type = (not unlock_type and 'unlock-recipe') or unlock_type
        local r_name = type(effect) == 'table' and effect.name or effect
        if unlock_type == 'unlock-recipe' or not unlock_type then
            if Recipe(effect):is_valid() then
                add_unlock(self, r_name)
            end
        end
    elseif self:is_valid('recipe') then
        unlock_type = 'unlock-recipe'
        -- Convert to array and return first valid tech
        local techs = type(effect) == 'string' and {effect} or effect
        for _, name in pairs(techs) do
            local tech = Technology(name)
            if tech:is_valid('technology') then
                self:set_enabled(false)
                add_unlock(tech, self.name)
                break
            end
        end
    end

    return self
end

function Technology:remove_effect(tech_name, unlock_type, name)
    if self:is_valid('technology') then
        return self, name, unlock_type -- TODO finish
    elseif self:is_valid('recipe') then
        if tech_name then
            local tech = Technology(tech_name)
            if tech:is_valid() then
                for index, effect in pairs(tech.effects or {}) do
                    if effect.type == 'unlock-recipe' and effect.recipe == self.name then
                        table.remove(tech.effects, index)
                    end
                end
            end
        else
            for _, tech in pairs(data.raw['technology']) do
                for index, effect in pairs(tech.effects or {}) do
                    if effect.type == 'unlock-recipe' and effect.recipe == self.name then
                        table.remove(tech.effects, index)
                    end
                end
            end
        end
    end
    return self
end

function Technology:add_pack(new_pack, count)
    if self:is_valid('technology') then
        local Item = require('__stdlib__/stdlib/data/item')
        if type(new_pack) == 'table' then
            count = new_pack[2] or 1
            new_pack = new_pack[1]
        elseif type(new_pack) == 'string' then
            count = count or 1
        else
            error('new_pack must be a table or string')
        end

        if Item(new_pack):is_valid() then
            self.unit.ingredients = self.unit.ingredients or {}
            local ing = self.unit.ingredients
            ing[#ing + 1] = {new_pack, count}
        end
    end
    return self
end

function Technology:remove_pack(pack)
    if self:is_valid('technology') then
        local ings = self.unit.ingredients
        for i, ing in pairs(ings or {}) do
            if ing[1] == pack then
                table.remove(ings, i)
                break
            end
        end
    end
    return self
end

function Technology:replace_pack(old_pack, new_pack, count)
    if self:is_valid('technology') then
        local ings = self.unit.ingredients
        for i, ing in pairs(ings or {}) do
            if ing[1] == old_pack then
                ing[1] = new_pack
                ing[2] = count or ing[2] or 1
                break
            end
        end
    end
    return self
end

function Technology:add_prereq(tech_name)
    if self:is_valid('technology') and Technology(tech_name):is_valid() then
        self.prerequisites = self.prerequisites or {}
        local pre = self.prerequisites
        for _, existing in pairs(pre) do
            if existing == tech_name then
                return self
            end
        end

        pre[#pre + 1] = tech_name
    end
    return self
end

function Technology:remove_prereq(tech_name)
    if self:is_valid('technology') then
        local pre = self.prerequisites or {}
        for i = #pre, 1, -1 do
            if pre[i] == tech_name then
                table.remove(pre, i)
                break
            end
        end
        if #pre == 0 then
            self.prerequisites = nil
        end
    end
    return self
end

return Technology
