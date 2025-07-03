global.actions.print = function(message)
    message = dump(message)
    return '"'..message..'"'
end