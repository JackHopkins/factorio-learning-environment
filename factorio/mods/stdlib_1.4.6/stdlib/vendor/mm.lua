-- Terminal color (and formatting) codes.
local C = {
  e = '\27[0m', -- reset

  -- Text attributes.
  br = '\27[1m', -- bright
  di = '\27[2m', -- dim
  it = '\27[3m', -- italics
  un = '\27[4m', -- underscore
  bl = '\27[5m', -- blink
  re = '\27[7m', -- reverse
  hi = '\27[8m', -- hidden

  -- Text colors.
  k = '\27[30m', -- black
  r = '\27[31m', -- red
  g = '\27[32m', -- green
  y = '\27[33m', -- yellow
  b = '\27[34m', -- blue
  m = '\27[35m', -- magenta
  c = '\27[36m', -- cyan
  w = '\27[37m', -- white

  -- Background colors.
  _k = '\27[40m', -- black
  _r = '\27[41m', -- red
  _g = '\27[42m', -- green
  _y = '\27[43m', -- yellow
  _b = '\27[44m', -- blue
  _m = '\27[45m', -- magenta
  _c = '\27[46m', -- cyan
  _w = '\27[47m'  -- white
}

local METATABLE = { "<metatable>", colors = C.it .. C.y }
local INDENT = "   "

-- The default sequence separator.
local SEP = " "

-- The open and close brackets can be any piece (notably, a sequence with
-- colors). The separator must be a plain string.
local BOPEN, BSEP, BCLOSE = 1, 2, 3

-- The default frame brackets and separator.
local BRACKETS = {
  { "{", colors = C.br },
  ",",
  { "}", colors = C.br }
}

local STR_HALF = 30
local MAX_STR_LEN = STR_HALF * 2

-- Names to use for named references. The order is important; these are aligned
-- with the colors in `NAME_COLORS`.
local NAMES = {
  "Cherry",
  "Apple",
  "Lemon",
  "Blueberry",
  "Jam",
  "Cream",
  "Rhubarb",
  "Lime",
  "Butter",
  "Grape",
  "Pomegranate",
  "Sugar",
  "Cinnamon",
  "Avocado",
  "Honey",
}

-- Colors to use for named references. Don't use black nor white.
local NAME_COLORS = { C.r, C.g, C.y, C.b, C.m, C.c }

-- Reserved Lua keywords as a convenient look-up table.
local RESERVED = {
  ['and'] = true,
  ['break'] = true,
  ['do'] = true,
  ['else'] = true,
  ['elseif'] = true,
  ['end'] = true,
  ['false'] = true,
  ['for'] = true,
  ['function'] = true,
  ['goto'] = true,
  ['if'] = true,
  ['in'] = true,
  ['local'] = true,
  ['nil'] = true,
  ['not'] = true,
  ['or'] = true,
  ['repeat'] = true,
  ['return'] = true,
  ['then'] = true,
  ['true'] = true,
  ['until'] = true,
  ['while'] = true
}


--
-- Namers
--

local function new_namer ()
  local index = 1
  local suffix = 1
  local color_index = 1

  return function ()
    -- Pick the name.
    local result = NAMES [index]
    if suffix > 1 then
      result = result .. " " .. tostring (suffix)
    end

    index = index + 1
    if index > #NAMES then
      index = 1
      suffix = suffix + 1
    end

    -- Pick the color.
    local color = NAME_COLORS [color_index]

    color_index = color_index + 1
    if color_index > #NAME_COLORS then
      color_index = 1
    end

    return { result, colors = C.un .. color }
  end
end


--
-- Context
--


local function new_context ()
  return {
    occur = {},
    named = {},
    next_name = new_namer (),

    prev_indent = '',
    next_indent = INDENT,
    line_len = 0,
    max_width = 78,

    result = ''
  }
end


--
-- Translating into pieces
--

-- Translaters take any Lua value and create pieces to represent them.
--
-- Some values should only be serialized once, both to prevent cycles and to
-- prevent redundancy. Or in other cases, these values cannot be serialized
-- (such as functions) but if they appear multiple times we want to express
-- that they are the same.
--
-- When a translater encounters such a value for the first time, it is
-- registered in the context in `occur`. The value is wrapped in a plain table
-- with the `id` field pointing to the original value. If the value is
-- serializable, such as a table, then the the `def` field contains the piece
-- to display. If it is unserializable or it is not the first time this value
-- has occurred, the `def` field is nil.
--
-- In the cleaning stage, these `id` fields are replaced with their names. If a
-- `def` field is present, then a sequence is generated to define the name with
-- the piece.

local translaters = {}
local translate, ident_friendly


function translate (val, ctx)
  -- Try to find a type-specific translater.
  local by_type = translaters [type (val)]

  if by_type then
    -- If there is a type-specific translater, call it.
    return by_type (val, ctx)
  end

  -- Otherwise perform the default translation.

  -- Check whether we've already encountered this value.
  if ctx.occur [val] then
    -- We have; give it a name if we haven't already.
    if not ctx.named [val] then
      ctx.named [val] = ctx.next_name ()
    end

    -- Return the value as a reference.
    return { id = val }
  else
    -- We haven't; mark it as encountered.
    ctx.occur [val] = true

    -- Return the value as a definition.
    return { id = val, def = tostring (val) }
  end
end


translaters ['function'] = function (val, ctx)
  -- Check whether we've already encountered this function.
  if ctx.occur [val] then
    -- We have; give it a name if we haven't already.
    if not ctx.named [val] then
      ctx.named [val] = ctx.next_name ()
    end
  else
    -- We haven't; mark it as encountered.
    ctx.occur [val] = true
  end

  -- Return the unserialized function.
  return { id = val }
end


function translaters.table (val, ctx)
  -- Check whether we've already encountered this table.
  if ctx.occur [val] then
    -- We have; give it a name if we haven't already.
    if not ctx.named [val] then
      ctx.named [val] = ctx.next_name ()
    end

    -- Return the unserialized table.
    return { id = val }
  else
    -- We haven't; mark it as encountered.
    ctx.occur [val] = true

    -- Construct the frame for this table.
    local result = {
      bracket = BRACKETS
    }

    -- The equals-sign between key and value.
    local eq = { "=", colors = C.di }

    -- Represent the metatable, if present.
    local mt = getmetatable (val)
    if mt then
      -- Translate the metatable.
      mt = translate (mt, ctx)
      table.insert (result, { METATABLE, eq, mt })
    end

    -- Represent the contents.
    for k, v in pairs (val) do
      -- If it is a string key which can be represented without quotes, leave
      -- it plain.
      if ident_friendly (k) then
        -- Leave the key as it is.
        k = { k, colors = C.m }
      else
        -- Otherwise translate the key.
        k = translate (k, ctx)
      end

      -- Translate the value.
      v = translate (v, ctx)

      table.insert (result, { k, eq, v })
    end

    -- Wrap the result with its id.
    return { id = val, def = result }
  end
end


function translaters.string (val)
  if #val <= MAX_STR_LEN then
    -- The string is short enough; display it all.
    local a = string.format ('%q', val)
    a = string.gsub (a, '\n', 'n')

    return { a, colors = C.g }
  else
    -- The string is too long. Only show the start and end.
    local a = string.format ('%q', string.sub (val, 1, STR_HALF))
    a = string.gsub (a, '\n', 'n')
    local b = string.format ('%q', string.sub (val, -STR_HALF))
    b = string.gsub (b, '\n', 'n')

    return { a, { "...", colors = C.di }, b, colors = C.g, sep = '', tight = true }
  end
end


function translaters.number (val)
  return { tostring (val), colors = C.m .. C.br }
end


-- Check whether a value can be represented as a Lua identifier, without the
-- need for quotes or translation.
--
-- If the value is not a string, this immediately returns false. Otherwise, the
-- string must be a valid Lua name: a sequence of letters, digits, and
-- underscores that doesn't start with a digit and isn't a reserved keyword.
--
-- See http://www.lua.org/manual/5.3/manual.html#3.1
function ident_friendly (val)
  -- The value must be a string.
  if type (val) ~= 'string' then
    return false
  end

  if string.find (val, '^[_%a][_%a%d]*$') then
    -- The value is a Lua name; check if it is reserved.
    if RESERVED [val] then
      -- The value is a resreved keyword.
      return false
    else
      -- The value is a valid name.
      return true
    end
  else
    -- The value is not a Lua name.
    return false
  end
end


--
-- Cleaning pieces
--


local function clean (piece, ctx)
  if type (piece) == 'table' then
    -- Check if it's an id reference.
    if piece.id then
      local name = ctx.named [piece.id]
      local def = piece.def

      -- Check whether it has been given a name.
      if name then
        local header = {
          "<", type (piece.id), " ", name, ">",
          colors = C.it,
          sep = '',
          tight = true
        }
        -- Named. Check whether the reference has a definition.
        if def then
          -- Create a sequence defining the name to the definition.
          return { header, { "is", colors = C.di }, clean (piece.def, ctx) }
        else
          -- Show just the name.
          return header
        end
      else
        -- No name. Check whether the reference has a definition.
        if def then
          -- Display the definition without any header.
          return clean (piece.def, ctx)
        else
          -- Display just the type.
          return {
            "<", type (piece.id), ">",
            colors = C.it,
            sep = '',
            tight = true
          }
        end
      end

    -- Check if it's a frame.
    elseif piece.bracket then
      -- Clean each child.
      for i, child in ipairs (piece) do
        piece [i] = clean (child, ctx)
      end
      return piece

    -- Otherwise it's a sequence.
    else
      -- Clean each child.
      for i, child in ipairs (piece) do
        piece [i] = clean (child, ctx)
      end
      return piece
    end
  else
    -- It's a plain value, not a table; no cleaning is needed.
    return piece
  end
end


--
-- Displaying pieces
--


-- Pieces are either frames (with brackets), sequences (no brackets), or
-- strings.

-- Frames are displayed either short-form as { a = 1 } or long-form as
-- {
--   a = 1
-- }.


-- Declare all the local functions first, so they can refer to each other.
local min_len, display, display_frame, display_sequence, display_string,
      display_frame_short, display_frame_long, newline, newline_no_indent,
      write, write_nolength, space_here, space_newline


-- Dispatch based on the piece's type.
function display (piece, ctx)
  if type (piece) == 'string' then
    -- String.
    return display_string (piece, ctx)
  elseif piece.bracket then
    -- Frame.
    return display_frame (piece, ctx)
  else
    -- Sequence.
    return display_sequence (piece, ctx)
  end
end


-- Display a frame.
function display_frame (frame, ctx)
  if #frame == 0 then
    -- If the frame is empty, just display the brackets.
    local str = {
      frame.bracket [BOPEN], frame.bracket [BCLOSE],
      sep = '',
      tight = true
    }
    return display (str, ctx)
  end

  local ml = min_len (frame)

  -- Try to fit the frame short-form on this line.
  if ml <= space_here (ctx) then
    return display_frame_short (frame, ctx)

  -- Otherwise try to fit it short-form on the next line.
  elseif ml <= space_newline (ctx) then
    newline (ctx)
    return display_frame_short (frame, ctx)

  -- Otherwise display it long-form.
  else
    return display_frame_long (frame, ctx)
  end
end


function display_frame_short (frame, ctx)
  -- Short-form frames never wrap onto new lines, so we don't need to do any
  -- length checking (it's already been done for us).

  -- Write the open bracket.
  display (frame.bracket [BOPEN], ctx)
  write (" ", ctx)

  -- Display the first child.
  display (frame [1], ctx)

  -- Display the remaining children.
  for i = 2, #frame do
    local child = frame [i]

    -- Write the separator.
    write (frame.bracket [BSEP], ctx)
    write (" ", ctx)

    -- Display the child.
    display (child, ctx)
  end

  -- Write the close bracket.
  write (" ", ctx)
  display (frame.bracket [BCLOSE], ctx)
end


function display_frame_long (frame, ctx)
  -- Remember the original value of next_indent.
  local old_old_indent = ctx.prev_indent
  local old_indent = ctx.next_indent

  -- Display the open bracket.
  display (frame.bracket [BOPEN], ctx)

  -- Increase the indentation.
  ctx.prev_indent = old_indent
  ctx.next_indent = old_indent .. INDENT

  -- For all but the last child...
  for i = 1, #frame - 1 do
    local child = frame [i]

    -- Start a new line with old indentation.
    newline_no_indent (ctx)
    write (old_indent, ctx)

    -- Display the child.
    display (child, ctx)

    -- Write the separator.
    write (frame.bracket [BSEP], ctx)
  end

  -- For the last child...
  do
    local child = frame [#frame]

    -- Start a new line with old indentation.
    newline_no_indent (ctx)
    write (old_indent, ctx)

    -- Display the child.
    display (child, ctx)
    -- No separator.
  end

  -- Write the close bracket.
  newline_no_indent (ctx)
  write (old_old_indent, ctx)
  display (frame.bracket [BCLOSE], ctx)

  -- Return to the old indentation.
  ctx.prev_indent = old_old_indent
  ctx.next_indent = old_indent
end


function display_sequence (piece, ctx)
  if #piece > 0 then
    -- Check if this is a tight sequence.
    if piece.tight then
      -- Try to fit the entire sequence on one line.
      local ml = min_len (piece, ctx)

      -- If it won't fit here, but it would fit on the next line, then write it
      -- on the next line; otherwise, write it here.
      if ml > space_here (ctx) and ml <= space_newline (ctx) then
        newline (ctx)
      end
    end

    -- Apply the colors, if given.
    if piece.colors then
      write_nolength (piece.colors, ctx)
    end

    -- Display the first child.
    display (piece [1], ctx)

    -- For each following children:
    for i = 2, #piece do
      local child = piece [i]

      -- Apply the colors, if given.
      if piece.colors then
        write_nolength (piece.colors, ctx)
      end

      -- Write a separator.
      write (piece.sep or SEP, ctx)

      -- Then display the child.
      display (child, ctx)
    end

    -- Reset the colors.
    if piece.colors then
      write_nolength (C.e, ctx)
    end
  end
end


function display_string (piece, ctx)
  local ml = min_len (piece)

  -- If it won't fit here, but it would fit on the next line, then write it on
  -- the next line; otherwise, write it here.
  if ml > space_here (ctx) and ml <= space_newline (ctx) then
    newline (ctx)
  end

  write (piece, ctx)
end


-- The minimum length to display this piece, if it is placed all on one line.
function min_len (piece, ctx)
  -- For strings, simply return their length.
  if type (piece) == 'string' then
    return #piece
  end

  -- Otherwise, we have some calculations to do.
  local result = 0

  if piece.bracket then
    -- This is a frame.

    -- If it's an empty frame, just the open and close brackets.
    if #piece == 0 then
      return min_len (piece.bracket [BOPEN]) + min_len (piece.bracket [BCLOSE])
    end

    -- Open and close brackets, plus a space for each.
    result = result + min_len (piece.bracket [BOPEN]) +
      min_len (piece.bracket [BCLOSE]) + 2

    -- A separator between each item, plus a space for each.
    result = result + (#piece - 1) * (#piece.bracket[BSEP] + 1)
  else
    -- This is a sequence.

    -- If it's an empty sequence, then nothing.
    if #piece == 0 then
      return 0
    end

    -- A single separator between each item.
    result = result + (#piece - 1) * #(piece.sep or SEP)
  end

  -- For both frames and sequences:
  -- Find the minimum length of each child.
  for _, child in ipairs (piece) do
    result = result + min_len (child, ctx)
  end

  return result
end


function newline (ctx)
  ctx.result = ctx.result .. "\n"
  ctx.line_len = 0
  write (ctx.next_indent, ctx)
end


function newline_no_indent (ctx)
  ctx.result = ctx.result .. "\n"
  ctx.line_len = 0
end


function write (str, ctx)
  ctx.result = ctx.result .. str
  ctx.line_len = ctx.line_len + #str
end


function write_nolength (str, ctx)
  ctx.result = ctx.result .. str
end


function space_here (ctx)
  return math.max (0, ctx.max_width - ctx.line_len)
end


function space_newline (ctx)
  return math.max (0, ctx.max_width - #ctx.next_indent)
end


--
-- Main function
--


return function (val)
  if val == nil then
    print (nil)
  else
    local ctx = new_context ()
    local piece = translate (val, ctx)
    piece = clean (piece, ctx)
    display (piece, ctx)
    print (C.e .. ctx.result .. C.e)
  end
end
