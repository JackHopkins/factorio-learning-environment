local table = require('stdlib/utils/table')
-- luacheck: ignore
-- Product data is the result or ingredients table and associated methods
local ProductData = {
    __class = 'products',

    has = nil,
    add = nil,
    remove = nil,
    clear = nil,
    convert = nil,
    update = nil,
}

function ProductData:convert()
    if self.parent.valid then
    end
end

function ProductData:add(normal, expensive)
    if self.parent.valid then
        if self.normal then
            self.normal[#self.normal + 1] = {type = 'item', name = 'test', amount = 1}
            self.expensive[#self.expensive + 1] = {type = 'item', name = 'test', amount = 5}
        else
            self.regular[#self.regular + 1] = {type = 'item', name = 'test', amount = 1}
        end
        return self:update()
    end
    return self
end

function ProductData:remove(normal, expensive)
    if self.parent.valid then
        expensive = (expensive == true or expensive == nil) and normal

        expensive = expensive == true and normal or expensive
        if normal then
            local difficulty = self.normal or self.regular
            for index, product in pairs(difficulty) do
                if product.name == normal then
                    table.remove(difficulty, index)
                end
            end
        end
        if expensive and self.expensive then
            for index, product in pairs(self.expensive) do
                if product.name == expensive then
                    table.remove(self.expensive, index)
                end
            end
        end
        return self:update()
    end
    return self
end

function ProductData:replace()
    if self.parent.valid then
    end
end

function ProductData:clear()
    if self.parent.valid then
        local EMPTY = {}
        table.clear(rawget(self, 'expensive') or EMPTY)
        table.clear(rawget(self, 'normal') or EMPTY)
        table.clear(rawget(self, 'regular') or EMPTY)
        self:update()
    end
    return self
end

function ProductData:update()
    if self.parent.valid then
        local class = getmetatable(self).__class
        if (self.normal or self.regular) ~= (self.parent.normal[class] or self.parent[class]) then
            if self.parent.normal then
                self.parent.normal[class] = self.normal
                self.parent.expensive[class] = self.expensive
                if class == 'results' then
                    self.parent.normal.result = nil
                    self.parent.expensive.result = nil
                    self.parent.normal.result_count = nil
                    self.parent.expensive.result_count = nil
                end
            else
                self.parent[class] = self.regular
                if class == 'results' then
                    self.result = nil
                    self.result_count = nil
                end
            end
        end
    end
    return self
end

function ProductData:has(normal, expensive)
    if self.parent.valid then
        expensive = (expensive == true) and normal
        local has_normal, has_expensive = true, true
        if normal then
            has_normal = false
            for _, prod in pairs(self.normal or self.regular) do
                if prod.name == normal then
                    has_normal = true
                    break
                end
            end
        end
        if expensive then
            has_expensive = false
            for _, prod in pairs(self.expensive) do
                if prod.name == expensive then
                    has_expensive = true
                    break
                end
            end
        end
        return has_normal and has_expensive
    end
    return false
end

--Only using __tostring?
ProductData._mt = {
    __class = 'products',
    __index = ProductData,
    __tostring = function(self)
        local strtab = {}
        for _, ing in ipairs(self.normal or self.regular) do
            strtab[#strtab + 1] = ing.amount .. 'x ' .. ing.name
        end
        return table.concat(strtab, ', ')
    end,
    __len = function(t) return table.size(t.normal or t.regular) end
}

return ProductData
