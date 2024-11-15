--- Data
-- @classmod Data

require('__stdlib__/stdlib/core') -- Calling core up here to setup any required global stuffs

if _G.remote and _G.script then
    error('Data Modules can only be required in the data stage', 2)
end

local Table = require('__stdlib__/stdlib/utils/table')
local groups = require('__stdlib__/stdlib/data/modules/groups')

local Data = {
    __class = 'Data',
    __index = require('__stdlib__/stdlib/core'),
    Sprites = require('__stdlib__/stdlib/data/modules/sprites'),
    Pipes = require('__stdlib__/stdlib/data/modules/pipes'),
    Util = require('__stdlib__/stdlib/data/modules/util'),
    _default_options = {
        ['silent'] = false, -- Don't log if not present
        ['fail'] = false, -- Error instead of logging
        ['verbose'] = false, -- Extra logging info
        ['extend'] = true, -- Extend the data
        ['skip_string_validity'] = false, -- Skip checking for valid data
        ['items_and_fluids'] = true -- consider fluids valid for Item checks
    }
}
setmetatable(Data, Data)
--))

--(( Local Functions ))--

-- This is the tracing function.
local function log_trace(self, object, object_type)
    local msg = (self.__class and self.__class or '') .. (self.name and '/' .. self.name or '') .. ' '
    msg = msg .. (object_type and (object_type .. '/') or '') .. tostring(object) .. ' does not exist.'

    local trace = data_traceback()
    log(msg .. trace)
end
--)) END Local Functions ((--

--(( METHODS ))--

--- Is this a valid object
-- @tparam[opt] string type if present is the object this type
-- @treturn self
function Data:is_valid(type)
    if type then
        return rawget(self, 'valid') == type or false
    else
        return rawget(self, 'valid') and true or false
    end
end

function Data:is_class(class)
    if class then
        return self.__class == class or false
    else
        return self.__class and true or false
    end
end

function Data:print(...)
    local arr = {}
    for _, key in pairs({...}) do
        arr[#arr + 1] = inspect(self[key])
    end
    print(Table.unpack(arr))
    return self
end

function Data:log(tbl)
    local reduce_spam = function(item, path)
        -- if item == self.class then
        --     return {item.__class, self.__class}
        -- end
        if item == self._object_mt then
            return {self.__class, tostring(self)}
        end
        if path[#path] == 'parent' then
            return {tostring(item), item.__class}
        end
        if path[#path] == 'class' then
            return {self.__class, item.__class}
        end
        if path[#path] == inspect.METATABLE then
            return {self.__class or item.__class, item.__class}
        end
        return item
    end
    log(inspect(tbl and tbl or self, {process = reduce_spam}))
    return self
end

function Data:serpent()
    log(serpent.block(self, {name = self.name, metatostring = false, nocode = true, comment = false}))
    return self
end

function Data:error(msg)
    error(msg or 'Forced Error')
    return self
end

--- Changes the validity of the object.
-- @tparam boolean bool
-- @treturn self
function Data:continue(bool)
    rawset(self, 'valid', (bool and rawget(self, '_raw') and self.type) or false)
    return self
end

--- Changes the validity of the object if the passed function is true.
-- @tparam function func the function to test, self is passed as the first paramater
-- @treturn self
function Data:continue_if(func, ...)
    rawset(self, 'valid', (func(self, ...) and rawget(self, '_raw') and self.type) or false)
    return self
end

--- Extend object into the data table
-- @tparam[opt] boolean force Extend even if it is already extended
-- @treturn self
function Data:extend(force)
    if self.valid and (self.options.extend or force) then
        if not self.extended or force then
            local t = data.raw[self.type]
            if t == nil then
                t = {}
                data.raw[self.type] = t
            end
            t[self.name] = self._raw
            self.extended = true
        end
    end
    if force then
        log('NOTICE: Force extend ' .. self.type .. '/' .. self.name)
    elseif not self.options.extend and not self.extended then
        log('NOTICE: Did not extend ' .. self.type .. '/' .. self.name)
    end
    if self.overwrite then
        log('NOTICE: Overwriting ' .. self.type .. '/' .. self.name)
    end
    return self
end

--- Copies a recipe to a new recipe.
-- @tparam string new_name The new name for the recipe.
-- @tparam string result
-- @tparam[opt] table opts
-- @treturn self
function Data:copy(new_name, result, opts)
    assert(type(new_name) == 'string', 'new_name must be a string')
    if self:is_valid() then
        result = result or new_name
        local copy = Table.deep_copy(rawget(self, '_raw'))
        copy.name = new_name

        -- For Entities
        -- Need to also check mining results!!!!!!
        if copy.minable and copy.minable.result then
            copy.minable.result = result
        end

        -- For items
        if copy.place_result then
            copy.place_result = result
        end

        -- rail planners
        if copy.placeable_by and copy.placeable_by.item then
            copy.placeable_by.item = result
        end

        -- For recipes, should also to check results!!
        if copy.type == 'recipe' then
            if copy.normal and copy.normal.result then
                copy.normal.result = new_name
                copy.expensive.result = new_name
            else
                if copy.result then
                    copy.result = new_name
                end
            end
        end

        return self(copy, nil, opts or self.options)
    else
        error('Cannot Copy, invalid prototype', 4)
    end
end

--(( Flags ))--
function Data:Flags(create)
    if create then
        self.flags = Data.Unique_Array(self.flags)
    end
    return self.flags or Data.Unique_Array()
end

function Data:add_flag(flag)
    self:Flags(true):add(flag)
    return self
end

function Data:remove_flag(flag)
    self:Flags(true):remove(flag)
    return self
end

function Data:has_flag(flag)
    return self:Flags():all(flag)
end

function Data:any_flag(flag)
    return self:Flags():all(flag)
end

--)) Flags ((--

--- Run a function if the object is valid.
-- The object and any additional paramaters are passed to the function.
-- @tparam function func then function to run.
-- @treturn self
function Data:run_function(func, ...)
    if self:is_valid() then
        func(self, ...)
    end
    return self
end
Data.execute = Data.run_function

--- Run a function on a valid object and return its results.
-- @tparam function func the function to run. self is passed as the first paramter
-- @treturn boolean if the object was valid
-- @treturn the results from the passed function
function Data:get_function_results(func, ...)
    if self:is_valid() then
        return true, func(self, ...)
    end
end

--- Set the unique array class to the field if the field is present
-- @tparam table tab
-- @treturn self
function Data:set_unique_array(tab)
    if self:is_valid() and tab then
        self.Unique_Array(tab)
    end
    return self
end

--- Add or change a field.
-- @tparam string field the field to change.
-- @tparam mixed value the value to set on the field.
-- @treturn self
function Data:set_field(field, value)
    self[field] = value
    return self
end
Data.set = Data.set_field

--- Iterate a dictionary table and set fields on the object. Existing fields are overwritten.
-- @tparam table tab dictionary table of fields to set.
-- @treturn self
function Data:set_fields(tab)
    if self:is_valid() then
        for field, value in pairs(tab) do
            self[field] = value
        end
    end
    return self
end

--- Get a field.
-- @tparam string field
-- @tparam mixed default_value return this if the field doesn't exist
-- @treturn nil|mixed the value of the field
function Data:get_field(field, default_value)
    if self:is_valid() then
        local has = self[field]
        if has ~= nil then
            return has
        else
            return default_value
        end
    end
end

--- Iterate an array of fields and return the values as paramaters
-- @tparam array arr
-- @tparam boolean as_dictionary Return the results as a dictionary table instead of parameters
-- @treturn mixed the parameters
-- @usage local icon, name = Data('stone-furnace', 'furnace'):get_fields({icon, name})
function Data:get_fields(arr, as_dictionary)
    if self:is_valid() then
        local values = {}
        for _, name in pairs(arr) do
            values[as_dictionary and name or #values + 1] = self[name]
        end
        return as_dictionary and values or Table.unpack(values)
    end
end

--- Remove an indiviual field from the the object
-- @tparam string field The field to remove
-- @treturn self
function Data:remove_field(field)
    if self:is_valid() then
        self[field] = nil
    end
    return self
end

--- Iterate a string array and set to nil.
-- @tparam table arr string array of fields to remove.
-- @treturn self
function Data:remove_fields(arr)
    if self:is_valid() then
        for _, field in pairs(arr) do
            self[field] = nil
        end
    end
    return self
end

--- Change the item-subgroup and/or order.
-- @tparam[opt=nil] string subgroup, The subgroup to change to if valid.
-- @tparam[opt=nil] string order The order string to use
-- note if subgroup is non nil and subgroub is not valid order wil not be changed.
-- @treturn self
function Data:subgroup_order(subgroup, order)
    if self:is_valid() then
        if subgroup then
            if data.raw['item-subgroup'][subgroup] then
                self.subgroup = subgroup
            else
                order = false
            end
        end
        if order and #order > 0 then
            self.order = order
        end
    end
    return self
end

--- Replace an icon
-- @tparam string icon
-- @tparam int size
function Data:replace_icon(icon, size)
    if self:is_valid() then
        if type(icon) == 'table' then
            self.icons = icon
            self.icon = nil
        else
            self.icon = icon
        end
        self.icon_size = size or self.icon_size
    end
    if not self.icon_size then
        error('Icon present but icon size not detected')
    end
    return self
end

--- Get the icons
-- @tparam[opt=false] boolean copy return a copy of the icons table
-- @treturn table icons
function Data:get_icons(copy)
    if self:is_valid() then
        return copy and Table.deep_copy(self.icons) or self.icons
    end
end

function Data:get_icon()
    if self:is_valid() then
        return self.icon
    end
end

function Data:make_icons(...)
    if self:is_valid() then
        if not self.icons then
            if self.icon then
                self.icons = {{icon = self.icon, icon_size = self.icon_size}}
                self.icon = nil
            else
                self.icons = {}
            end
        end
        for _, icon in pairs({...}) do
            self.icons[#self.icons + 1] = Table.deep_copy(icon)
        end
    end
    return self
end

function Data:set_icon_at(index, values)
    if self:is_valid() then
        if self.icons then
            for k, v in pairs(values or {}) do
                self.icons[index].k = v
            end
        end
    end
    return self
end

--- Get the objects name.
-- @treturn string the objects name
function Data:tostring()
    return self.valid and (self.name and self.type) and (self.type .. '/' .. self.name) or rawtostring(self)
end

function Data:pairs(source, opts)
    local index, val
    if not source and self.type then
        source = data.raw[self.type]
    else
        local type = type(source)
        source = type == 'string' and data.raw[source] or (assert(type == 'table', 'Source missing') and source)
    end

    local function _next()
        index, val = next(source, index)
        if index then
            return index, self(val, nil, opts)
        end
    end

    return _next, index, val
end

--- Returns a valid thing object reference. This is the main getter.
-- @tparam string|table object The thing to use, if string the thing must be in data.raw[type], tables are not verified
-- @tparam[opt] string object_type the raw type. Required if object is a string
-- @tparam[opt] table opts options to pass
-- @treturn Object
function Data:get(object, object_type, opts)
    --assert(type(object) == 'string' or type(object) == 'table', 'object string or table is required')

    -- Create our middle man container object
    local new = {
        class = self.class or self,
        _raw = nil,
        _products = nil,
        _parent = nil,
        valid = false,
        extended = false,
        overwrite = false,
        options = Table.merge(Table.deep_copy(Data._default_options), opts or self.options or {})
    }

    if type(object) == 'table' then
        assert(object.type and object.name, 'name and type are required')

        new._raw = object
        new.valid = object.type
        --Is a data-raw that we are overwriting
        local existing = data.raw[object.type] and data.raw[object.type][object.name]
        new.extended = existing == object
        new.overwrite = not new.extended and existing and true or false
    elseif type(object) == 'string' then
        --Get type from object_type, or fluid or item_and_fluid_types
        local types = (object_type and {object_type}) or (self.__class == 'Item' and groups.item_and_fluid)
        if types then
            for _, type in pairs(types) do
                new._raw = data.raw[type] and data.raw[type][object]
                if new._raw then
                    new.valid = new._raw.type
                    new.extended = true
                    break
                end
            end
        else
            error('object_type is missing for ' .. (self.__class or 'Unknown') .. '/' .. (object or ''), 3)
        end
    end

    setmetatable(new, self._object_mt)
    if new.valid then
        rawset(new, '_parent', new)
        self.Unique_Array.set(new.flags)
        self.Unique_Array.set(new.crafting_categories)
        self.Unique_Array.set(new.mining_categories)
        self.Unique_Array.set(new.inputs)
    elseif not new.options.silent then
        log_trace(new, object, object_type)
    end
    return new:extend()
end
Data.__call = Data.get
--)) END Methods ((--

-- This is the table set on new objects
Data._object_mt = {
    --__class = "Data",
    -- index from _raw if that is not available then retrieve from the class
    __index = function(t, k)
        return rawget(t, '_raw') and t._raw[k] or t.class[k]
    end,
    -- Only allow setting on valid _raw tables.
    __newindex = function(t, k, v)
        if rawget(t, 'valid') and rawget(t, '_raw') then
            t._raw[k] = v
        end
    end,
    -- Call the getter on itself
    __call = function(t, ...)
        return t:__call(...)
    end,
    -- use Core.tostring
    __tostring = Data.tostring
}

return Data
