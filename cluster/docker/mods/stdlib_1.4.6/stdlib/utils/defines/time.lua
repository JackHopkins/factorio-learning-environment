--- A defines module for retrieving the number of ticks in 1 unit of time.
-- Extends the Factorio defines table.
-- @module defines.time

-- defines table is automatically required in all mod loading stages.

local SECOND = 60
local MINUTE = SECOND * 60
local HOUR = MINUTE * 60
local DAY = HOUR * 24
local WEEK = DAY * 7
local MONTH = DAY * 30
local YEAR = DAY * 365

--- Returns the number of ticks in a second, minute, hour, day, week, month, or year.
-- @table time
-- @usage local ten_seconds = defines.time.second * 10
local time = {
    second = SECOND, -- the number of Factorio ticks in a second
    minute = MINUTE, -- the number of Factorio ticks in a second
    hour = HOUR, -- the number of Factorio ticks in an hour
    day = DAY, -- the number of Factorio ticks in an day
    week = WEEK, -- the number of Factorio ticks in a week
    month = MONTH, -- the number of Factorio ticks in a month (30 days)
    year = YEAR -- the number of Factorio ticks in a year (365 days)
}

_G.defines = _G.defines or {}
_G.defines.time = time

return time
