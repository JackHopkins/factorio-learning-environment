---
-- Version comparison library for Lua.
--
-- Comparison is simple and straightforward, with basic support for SemVer.
--
-- @usage
-- local version = require("version")
--
-- -- create a version and perform some comparisons
-- local v = version("3.1.0")
-- assert( v == version("3.1"))   -- missing elements default to zero, and hence are equal
-- assert( v > version("3.0"))
--
-- -- create a version range, and check whether a version is within that range
-- local r = version.range("2.75", "3.50.3")
-- assert(r:matches(v))
--
-- -- create a set of multiple ranges, adding elements in a chained fashion
-- local compatible = version.set("1.1","1.2"):allowed("2.1", "2.5"):disallowed("2.3")
--
-- assert(compatible:matches("1.1.3"))
-- assert(compatible:matches("1.1.3"))
-- assert(compatible:matches("2.4"))
-- assert(not compatible:matches("2.0"))
-- assert(not compatible:matches("2.3"))
--
-- -- print a formatted set
-- print(compatible) --> "1.1 to 1.2 and 2.1 to 2.5, but not 2.3"
--
-- -- create an upwards compatibility check, allowing all versions 1.x
-- local c = version.set("1.0","2.0"):disallowed("2.0")
-- assert(c:matches("1.4"))
-- assert(not c:matches("2.0"))
--
-- -- default parsing
-- print(version("5.2"))                    -- "5.2"
-- print(version("Lua 5.2 for me"))         -- "5.2"
-- print(version("5..2"))                   -- nil, "Not a valid version element: '5..2'"
--
-- -- strict parsing
-- print(version.strict("5.2"))             -- "5.2"
-- print(version.strict("Lua 5.2 for me"))  -- nil, "Not a valid version element: 'Lua 5.2 for me'"
-- print(version.strict("5..2"))            -- nil, "Not a valid version element: '5..2'"
--
-- @copyright Kong Inc.
-- @author Thijs Schreijer
-- @license Apache 2.0


local table_insert = table.insert
local table_concat = table.concat
local math_max = math.max

-- Utility split function
local function split(str, pat)
  local t = {}
  local fpat = "(.-)" .. pat
  local last_end = 1
  local s, e, cap = str:find(fpat, 1)

  while s do
    if s ~= 1 or cap ~= "" then
      table_insert(t,cap)
    end

    last_end = e + 1
    s, e, cap = str:find(fpat, last_end)
  end

  if last_end <= #str then
    cap = str:sub(last_end)
    table_insert(t, cap)
  end

  return t
end

-- foreward declaration of constructor
local _new, _range, _set

-- Metatables for version, range and set
local mt_version
mt_version = {
    __index = {
      --- Matches a provider-version on a consumer-version based on the
      -- semantic versioning specification.
      -- The implementation does not support pre-release and/or build metadata,
      -- only the major, minor, and patch levels are compared.
      -- @function ver:semver
      -- @param v Version (string or `version` object) as served by the provider
      -- @return `true` or `false` whether the version matches, or `nil+err`
      -- @usage local consumer = "1.2"     -- consumer requested version
      -- local provider = "1.5.2"   -- provider served version
      --
      -- local compatible = version(consumer):semver(provider)
      semver = function(self, v)
        -- this function will be called once (in the meta table), it will set
        -- the actual function on the version table itself
        if self[1] == 0 then
          -- major 0 is only compatible when equal
          self.semver = function(self2, v2)
            if getmetatable(v2) ~= mt_version then
              local parsed, err = _new(v2, self2.strict)
              if not parsed then return nil, err end
              v2 = parsed
            end
            return self2 == v2
          end
        elseif self[4] then
          -- more than 3 elements, cannot compare
          self.semver = function()
            return nil, "Version has too many elements (semver max 3)"
          end
        else
          local semver_set = _set(self, self[1] + 1, self.strict):disallowed(self[1] + 1)
          self.semver = function(_, v2)
            return semver_set:matches(v2)
          end
        end
        return self:semver(v)
      end
    },
    __eq = function(a,b)
      local l = math_max(#a, #b)
      for i = 1, l do
        if (a[i] or 0) ~= (b[i] or 0) then
          return false
        end
      end
      return true
    end,
    __lt = function(a,b)
      if getmetatable(a) ~= mt_version or getmetatable(b) ~= mt_version then
        local t = getmetatable(a) ~= mt_version and type(a) or type(b)
        error("cannot compare a 'version' to a '" .. t .. "'", 2)
      end
      local l = math_max(#a, #b)
      for i = 1, l do
        if (a[i] or 0) < (b[i] or 0) then
          return true
        end
        if (a[i] or 0) > (b[i] or 0) then
          return false
        end
      end
      return false
    end,
    __tostring = function(self)
      return table_concat(self, ".")
    end,
}

local mt_range = {
  __index = {
      --- Matches a version on a range.
      -- @function range:matches
      -- @param v Version (string or `version` object) to match
      -- @return `true` or `false` whether the version matches the range, or `nil+err`
      matches = function(self, v)
        if getmetatable(v) ~= mt_version then
          local parsed, err = _new(v, self.strict)
          if not parsed then return nil, err end
          v = parsed
        end

        return (v >= self.from) and (v <= self.to)
      end,
    },
    __tostring = function(self)
      local f, t = tostring(self.from), tostring(self.to)
      if f == t then
        return f
      else
        return f .. " to " .. t
      end
    end,
}

local mt_set = {
  __index = {
      --- Adds an ALLOWED range to the set.
      -- @function set:allowed
      -- @param v1 Version or range, if version, the FROM version in either string or `version` object format
      -- @param v2 Version (optional), TO version in either string or `version` object format
      -- @return The `set` object, to easy chain multiple allowed/disallowed ranges, or `nil+err`
      allowed = function(self, v1, v2)
        if getmetatable(v1) == mt_range then
          assert (v2 == nil, "First parameter was a range, second must be nil.")
          table_insert(self.ok, v1)
        else
          local r, err = _range(v1, v2, self.strict)
          if not r then return nil, err end
          table_insert(self.ok, r)
        end
        return self
      end,
      --- Adds a DISALLOWED range to the set.
      -- @function set:disallowed
      -- @param v1 Version or range, if version, the FROM version in either string or `version` object format
      -- @param v2 Version (optional), TO version in either string or `version` object format
      -- @return The `set` object, to easy chain multiple allowed/disallowed ranges, or `nil+err`
      disallowed = function(self,v1, v2)
        if getmetatable(v1) == mt_range then
          assert (v2 == nil, "First parameter was a range, second must be nil.")
          table_insert(self.nok, v1)
        else
          local r, err = _range(v1, v2, self.strict)
          if not r then return nil, err end
          table_insert(self.nok, r)
        end
        return self
      end,

      --- Matches a version against the set of allowed and disallowed versions.
      --
      -- NOTE: `disallowed` has a higher precedence, so a version that matches the `allowed` set,
      -- but also the `disallowed` set, will return `false`.
      -- @function set:matches
      -- @param v1 Version to match (either string or `version` object).
      -- @return `true` or `false` whether the version matches the set, or `nil+err`
      matches = function(self, v)
        if getmetatable(v) ~= mt_version then
          local parsed, err = _new(v, self.strict)
          if not parsed then return nil, err end
          v = parsed
        end

        local success
        for _, range in pairs(self.ok) do
          if range:matches(v) then
            success = true
            break
          end
        end
        if not success then
          return false
        end
        for _, range in pairs(self.nok) do
          if range:matches(v) then
            return false
          end
        end
        return true
      end,
    },
    __tostring = function(self)
      local ok, nok
      if #self.ok == 1 then
        ok = tostring(self.ok[1])
      elseif #self.ok > 1 then
        ok = tostring(self.ok[1])
        for i = 2, #self.ok - 1 do
          ok = ok .. ", " ..tostring(self.ok[i])
        end
        ok = ok .. ", and " .. tostring(self.ok[#self.ok])
      end
      if #self.nok == 1 then
        nok = tostring(self.nok[1])
      elseif #self.nok > 1 then
        nok = tostring(self.nok[1])
        for i = 2, #self.nok - 1 do
          nok = nok .. ", " ..tostring(self.nok[i])
        end
        nok = nok .. ", and " .. tostring(self.nok[#self.nok])
      end
      if ok and nok then
        return ok .. ", but not " .. nok
      else
        return ok
      end
    end,
}


_new = function(v, strict)
  v = tostring(v)
  if strict then
    -- edge case: do not allow trailing dot
    if v:sub(-1,-1) == "." then
      return nil, "Not a valid version element: '"..tostring(v).."'"
    end
  else
    local m = v:match("(%d[%d%.]*)")
    if not m then
      return nil, "Not a valid version element: '"..tostring(v).."'"
    end
    v = m
  end
  local t = split(v, "%.")
  for i, s in ipairs(t) do
    local n = tonumber(s)
    if not n then
      return nil, "Not a valid version element: '"..tostring(v).."'"
    end
    t[i] = n
  end
  t.strict = strict
  return setmetatable(t, mt_version)
end

_range = function(v1,v2, strict)
  local err
  assert (v1 or v2, "At least one parameter is required")
  v1 = v1 or "0"
  v2 = v2 or v1
  if getmetatable(v1) ~= mt_version then
    v1, err = _new(v1, strict)
    if not v1 then return nil, err end
  end
  if getmetatable(v2) ~= mt_version then
    v2, err = _new(v2, strict)
    if not v2 then return nil, err end
  end
  if v1 > v2 then
    return nil, "FROM version must be less than or equal to the TO version"
  end

  return setmetatable({
    from = v1,
    to = v2,
    strict = strict,
  }, mt_range)
end

_set = function(v1, v2, strict)
  return setmetatable({
    ok = {},
    nok = {},
    strict = strict,
  }, mt_set):allowed(v1, v2)
end

local make_module = function(strict)
  return setmetatable({
    --- Creates a new version object from a string.
    -- The returned table will have
    -- comparison operators, eg. LT, EQ, GT. For all comparisons, any missing numbers
    -- will be assumed to be "0" on the least significant side of the version string.
    --
    -- Calling on the module table is a shortcut to `new`.
    -- @param v String formatted as numbers separated by dots (no limit on number of elements).
    -- @return `version` object, or `nil+err`
    -- @usage local v = version.new("0.1")
    -- -- is identical to
    -- local v = version("0.1")
    --
    -- print(v)     --> "0.1"
    -- print(v[1])  --> 0
    -- print(v[2])  --> 1
    new = function(v) return _new(v, strict) end,

    --- Creates a version range.  A `range` object represents a range of versions.
    -- @param v1 The FROM version of the range (string or `version` object). If `nil`, assumed to be 0.
    -- @param v2 (optional) The TO version of the range (string or `version` object). Defaults to `v1`.
    -- @return range object with `from` and `to` fields and `set:matches` method, or `nil+err`.
    -- @usage local r = version.range("0.1"," 2.4")
    --
    -- print(v.from)     --> "0.1"
    -- print(v.to[1])    --> 2
    -- print(v.to[2])    --> 4
    range = function(v1,v2) return _range(v1, v2, strict) end,

    --- Creates a version set.
    -- A `set` is an object that contains a number of allowed and disallowed version `range` objects.
    -- @param v1 initial version/range to allow, see `set:allowed` for parameter descriptions
    -- @param v2 initial version/range to allow, see `set:allowed` for parameter descriptions
    -- @return a `set` object, with `ok` and `nok` lists and a `set:matches` method, or `nil+err`
    set = function(v1, v2) return _set(v1, v2, strict) end,
  }, {
    __call = function(self, ...)
      return self.new(...)
    end
  })
end

local _M = make_module(false)
--- Similar module, but with stricter parsing rules.
-- `version.strict` is identical to the `version` module itself, but it requires
-- exact version strings, where as the regular parser will simply grab the
-- first sequence of numbers and dots from the string.
-- @field strict same module, but for stricter parsing.
_M.strict = make_module(true)

return _M
