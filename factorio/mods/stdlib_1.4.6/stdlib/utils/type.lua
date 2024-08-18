local type = type

local Type = {
    Table = function(param) return type(param) == 'table' end,
    Function = function(param) return type(param) == 'function' or type((getmetatable(param) or {}).__call) == 'function' end,
    Nil = function(param) return param == nil end,
    String = function(param) return type(param) == 'string' end,
    Number = function(param) return type(param) == 'number' end,
}

return Type
