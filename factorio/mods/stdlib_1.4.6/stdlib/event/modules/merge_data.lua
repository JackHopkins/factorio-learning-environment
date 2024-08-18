local table = require('__stdlib__/stdlib/utils/table')

local function merge_additional_data(additional_data_array, data)
    for _, new_data in pairs(additional_data_array) do
        if type(new_data) == 'table' then
            table.merge(data, table.deepcopy(new_data))
        elseif type(new_data) == 'function' then
            local new_data_func_result = new_data(data.index)
            if type(new_data_func_result) == 'table' then
                table.merge(data, new_data_func_result)
            else
                error('additional data function did not return a table')
            end
        else
            error('additional data present but is not a function or table')
        end
    end
    return data
end

return merge_additional_data
