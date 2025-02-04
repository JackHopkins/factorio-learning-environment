util =
{
  table = {}
}

-- Helper to check if a tile is water
function is_water_tile(tile_name)
    return tile_name == "water" or
           tile_name == "deepwater" or
           tile_name == "water-green" or
           tile_name == "deepwater-green" or
           tile_name == "water-shallow" or
           tile_name == "water-mud"
end

function table.deepcopy(object)
  local lookup_table = {}
  local function _copy(object)
    if type(object) ~= "table" then
      return object
    -- don't copy factorio rich objects
    elseif object.__self then
      return object
    elseif lookup_table[object] then
      return lookup_table[object]
    end
    local new_table = {}
    lookup_table[object] = new_table
    for index, value in pairs(object) do
      new_table[_copy(index)] = _copy(value)
    end
    return setmetatable(new_table, getmetatable(object))
  end
  return _copy(object)
end

function table.compare( tbl1, tbl2 )
  if tbl1 == tbl2 then return true end
  for k, v in pairs( tbl1 ) do
    if  type(v) == "table" and type(tbl2[k]) == "table" then
      if not table.compare( v, tbl2[k] )  then return false end
    else
      if ( v ~= tbl2[k] ) then return false end
    end
  end
  for k, v in pairs( tbl2 ) do
    if tbl1[k] == nil then return false end
  end
  return true
end

util.table.deepcopy = table.deepcopy
util.table.compare = table.compare
util.copy = util.table.deepcopy

function util.distance(position1, position2)
  local x1 = position1[1] or position1.x
  local y1 = position1[2] or position1.y
  local x2 = position2[1] or position2.x
  local y2 = position2[2] or position2.y
  return ((x1 - x2) ^ 2 + (y1 - y2) ^ 2) ^ 0.5
end

function util.positiontostr(pos)
  return string.format("[%g, %g]", pos[1] or pos.x, pos[2] or pos.y)
end

function util.formattime(ticks)
  local seconds = ticks / 60
  local minutes = math.floor((seconds)/60)
  local seconds = math.floor(seconds - 60*minutes)
  return string.format("%d:%02d", minutes, seconds)
end

function util.color(hex)  -- supports 'rrggbb', 'rgb', 'rrggbbaa', 'rgba', 'ww', 'w'
  local function h(i,j)
    return j and tonumber("0x"..hex:sub(i,j)) / 255 or tonumber("0x"..hex:sub(i,i)) / 15
  end

  hex = hex:gsub("#","")
  return #hex == 6 and {r = h(1,2), g = h(3,4), b = h(5,6)}
    or #hex == 3 and {r = h(1), g = h(2), b = h(3)}
    or #hex == 8 and {r = h(1,2), g = h(3,4), b = h(5,6), a = h(7,8)}
    or #hex == 4 and {r = h(1), g = h(2), b = h(3), a = h(4)}
    or #hex == 2 and {r = h(1,2), g = h(1,2), b = h(1,2)}
    or #hex == 1 and {r = h(1), g = h(1), b = h(1)}
    or {r=1, g=1, b=1}
end

function util.premul_color(color)
  local r = color.r or color[1]
  local g = color.g or color[2]
  local b = color.b or color[3]
  local a = color.a or color[4] or 1
  return
  {
    r = r and (r * a),
    g = g and (g * a),
    b = b and (b * a),
    a = a
  }
end

function util.mix_color(c1, c2)
  return
  {
    (c1.r or c1[1] or 0) * (c2.r or c2[1] or 0),
    (c1.g or c1[2] or 0) * (c2.g or c2[2] or 0),
    (c1.b or c1[3] or 0) * (c2.b or c2[3] or 0),
    (c1.a or c1[4] or 1) * (c2.a or c2[4] or 1)
  }
end

function util.multiply_color(c1, n)
  return
  {
    (c1.r or c1[1] or 0) * (n or 0),
    (c1.g or c1[2] or 0) * (n or 0),
    (c1.b or c1[3] or 0) * (n or 0),
    (c1.a or c1[4] or 1) * (n or 1)
  }
end

function util.get_color_with_alpha(color, alpha, normalized_alpha)
  local new_color =
  {
    r = color.r or color[1] or 0,
    g = color.g or color[2] or 0,
    b = color.b or color[3] or 0
  }
  new_color.a = normalized_alpha and (new_color.r > 1 or new_color.g > 1 or new_color.b > 1) and alpha * 255 or alpha
  return new_color
end

function util.moveposition(position, direction, distance)

  if direction == defines.direction.north then
    return {position[1], position[2] - distance}
  end

  if direction == defines.direction.south then
    return {position[1], position[2] + distance}
  end

  if direction == defines.direction.east then
    return {position[1] + distance, position[2]}
  end

  if direction == defines.direction.west then
    return {position[1] - distance, position[2]}
  end
end

function util.oppositedirection(direction)
  if not tonumber(direction) then error(direction .. " is not a valid direction") end
  return (direction + 4) % 8
end

function util.multiplystripes(count, stripes)
  local ret = {}
  for _, stripe in ipairs(stripes) do
    for _ = 1, count do
      ret[#ret + 1] = stripe
    end
  end
  return ret
end

function util.by_pixel(x,y)
  return {x / 32, y / 32}
end

function util.by_pixel_hr(x,y)
  return {x / 64, y / 64}
end

function util.foreach_sprite_definition(table_, fun_)
  --for k, tab in pairs(table_) do
    fun_(table_)
    if table_.hr_version then
      fun_(table_.hr_version)
    end
  --end
  return table_
end

function util.add_shift(a, b)
  if not (a and b) then
    return a or b
  end
  return { a[1] + b[1], a[2] + b[2] }
end

function util.add_shift_offset(offset_, table_)
  return
    util.foreach_sprite_definition(table_, function(tab)
      tab.shift = util.add_shift(tab.shift, offset_)
    end)
end

function util.mul_shift(shift, scale)
  if not (shift and scale) then
    return shift
  end
  return {shift[1] * scale, shift[2] * scale}
end

function util.format_number(amount, append_suffix)
  local suffix = ""
  if append_suffix then
    local suffix_list =
      {
        ["T"] = 1000000000000,
        ["B"] = 1000000000,
        ["M"] = 1000000,
        ["k"] = 1000
      }
    for letter, limit in pairs (suffix_list) do
      if math.abs(amount) >= limit then
        amount = math.floor(amount/(limit/10))/10
        suffix = letter
        break
      end
    end
  end
  local formatted, k = amount
  while true do
    formatted, k = string.gsub(formatted, "^(-?%d+)(%d%d%d)", '%1,%2')
    if (k==0) then
      break
    end
  end
  return formatted..suffix
end

function util.increment(t, k, v)
  t[k] = t[k] + (v or 1)
end

function util.conditional_return(value, data)
  return value and data
end

-- Recursively merges and/or deep-copies tables.
-- Entries in later tables override entries in earlier ones, unless
-- both entries are themselves tables, in which case they are recursively merged.
-- Non-merged tables are deep-copied, so that the result is brand new.
function util.merge(tables)
  local ret = {}
  for i, tab in ipairs(tables) do
    for k, v in pairs(tab) do
      if (type(v) == "table") then
        if (type(ret[k] or false) == "table") then
          ret[k] = util.merge{ret[k], v}
        else
          ret[k] = table.deepcopy(v)
        end
      else
        ret[k] = v
      end
    end
  end
  return ret
end

util.insert_safe = function(entity, item_dict)
  if not (entity and entity.valid and item_dict) then return end
  local items = game.item_prototypes
  local insert = entity.insert
  for name, count in pairs (item_dict) do
    if items[name] then
      insert{name = name, count = count}
    else
      log("Item to insert not valid: "..name)
    end
  end
end

util.remove_safe = function(entity, item_dict)
  if not (entity and entity.valid and item_dict) then return end
  local items = game.item_prototypes
  local remove = entity.remove_item
  for name, count in pairs (item_dict) do
    if items[name] then
      remove{name = name, count = count}
    else
      log("Item to remove not valid: "..name)
    end
  end
end

util.split_whitespace = function(string)
  if not string then return {} end

  local result = {}
  for w in string:gmatch("%S+") do
    table.insert(result, w)
  end
  return result
end

util.split = function(inputstr, sep)
  local result = {}

  for str in string.gmatch(inputstr, "([^"..sep.."]+)") do
    table.insert(result, str)
  end

  return result
end

util.string_starts_with = function(str, start)
  return str.sub(str, 1, string.len(start)) == start
end

util.online_players = function()
  log("But why?")
  return game.connected_players
end

util.clamp = function(x, lower, upper)
  return math.max(lower, math.min(upper, x))
end

local walkable_mask = {"item-layer", "object-layer", "player-layer", "water-tile"}

local is_walkable = function(mask)
  for k, layer in pairs (walkable_mask) do
    if mask[layer] then return false end
  end
  return true
end

util.get_walkable_tile = function()
  for name, tile in pairs (game.tile_prototypes) do
    if is_walkable(tile.collision_mask) and not tile.items_to_place_this then
      return name
    end
  end
  error("No walkable tile in prototype list")
end

-- This function takes 2 icons tables, and adds the second to the first, but applies scale, shift and tint to the entire second set.
-- This allows you to manipulate the entire second icons table in the same way as you would manipulate a single icon when adding to the icons table.
function util.combine_icons(icons1, icons2, inputs, default_icon_size)
  scale = inputs.scale or 1
  shift = inputs.shift or {0, 0}
  tint = inputs.tint or {r = 1, g = 1, b = 1, a = 1}

  local icons = table.deepcopy(icons1)
  for _,icon_to_add in pairs(icons2) do
    local icon = {}
    icon.icon = icon_to_add.icon
    icon.icon_size = icon_to_add.icon_size or default_icon_size or error("No icon size defined for icon \n"..serpent.block(icon))
    icon.scale = scale * (icon_to_add.scale or 32.0 / icon.icon_size)
    icon.icon_mipmaps = icon_to_add.icon_mipmaps
    if icon_to_add.shift then
      icon.shift = {icon_to_add.shift[1] * scale + shift[1], icon_to_add.shift[2] * scale + shift[2]}
    else
      icon.shift = shift
    end
    if icon_to_add.tint then
      icon.tint = util.mix_color(tint, icon_to_add.tint)
    else
      icon.tint = tint
    end
    table.insert(icons,icon)
  end
  return icons
end

local energy_chars =
{
  k = 10^3,
  K = 10^3,
  M = 10^6,
  G = 10^9,
  T = 10^12,
  P = 10^15,
  E = 10^18,
  Z = 10^21,
  Y = 10^24
}

function util.technology_icon_constant_damage(technology_icon)
  local icons =
  {
    {
      icon = technology_icon,
      icon_size = 256, icon_mipmaps = 4
    },
    {
      icon = "__core__/graphics/icons/technology/constants/constant-damage.png",
      icon_size = 128,
      icon_mipmaps = 3,
      shift = {100, 100}
    }
  }
  return icons
end
function util.technology_icon_constant_speed(technology_icon)
  local icons =
  {
    {
      icon = technology_icon,
      icon_size = 256, icon_mipmaps = 4
    },
    {
      icon = "__core__/graphics/icons/technology/constants/constant-speed.png",
      icon_size = 128,
      icon_mipmaps = 3,
      shift = {100, 100}
    }
  }
  return icons
end
function util.technology_icon_constant_movement_speed(technology_icon)
  local icons =
  {
    {
      icon = technology_icon,
      icon_size = 256, icon_mipmaps = 4
    },
    {
      icon = "__core__/graphics/icons/technology/constants/constant-movement-speed.png",
      icon_size = 128,
      icon_mipmaps = 3,
      shift = {100, 100}
    }
  }
  return icons
end
function util.technology_icon_constant_range(technology_icon)
  local icons =
  {
    {
      icon = technology_icon,
      icon_size = 256, icon_mipmaps = 4
    },
    {
      icon = "__core__/graphics/icons/technology/constants/constant-range.png",
      icon_size = 128,
      icon_mipmaps = 3,
      shift = {100, 100}
    }
  }
  return icons
end
function util.technology_icon_constant_equipment(technology_icon)
  local icons =
  {
    {
      icon = technology_icon,
      icon_size = 256, icon_mipmaps = 4
    },
    {
      icon = "__core__/graphics/icons/technology/constants/constant-equipment.png",
      icon_size = 128,
      icon_mipmaps = 3,
      shift = {100, 100}
    }
  }
  return icons
end
function util.technology_icon_constant_followers(technology_icon)
  local icons =
  {
    {
      icon = technology_icon,
      icon_size = 256, icon_mipmaps = 4
    },
    {
      icon = "__core__/graphics/icons/technology/constants/constant-count.png",
      icon_size = 128,
      icon_mipmaps = 3,
      shift = {100, 100}
    }
  }
  return icons
end
function util.technology_icon_constant_capacity(technology_icon)
  local icons =
  {
    {
      icon = technology_icon,
      icon_size = 256, icon_mipmaps = 4
    },
    {
      icon = "__core__/graphics/icons/technology/constants/constant-capacity.png",
      icon_size = 128,
      icon_mipmaps = 3,
      shift = {100, 100}
    }
  }
  return icons
end
function util.technology_icon_constant_stack_size(technology_icon)
  local icons =
  {
    {
      icon = technology_icon,
      icon_size = 256, icon_mipmaps = 4
    },
    {
      icon = "__core__/graphics/icons/technology/constants/constant-capacity.png",
      icon_size = 128,
      icon_mipmaps = 3,
      shift = {100, 100}
    }
  }
  return icons
end
function util.technology_icon_constant_productivity(technology_icon)
  local icons =
  {
    {
      icon = technology_icon,
      icon_size = 256, icon_mipmaps = 4
    },
    {
      icon = "__core__/graphics/icons/technology/constants/constant-mining-productivity.png",
      icon_size = 128,
      icon_mipmaps = 3,
      shift = {100, 100}
    }
  }
  return icons
end
function util.technology_icon_constant_braking_force(technology_icon)
  local icons =
  {
    {
      icon = technology_icon,
      icon_size = 256, icon_mipmaps = 4
    },
    {
      icon = "__core__/graphics/icons/technology/constants/constant-braking-force.png",
      icon_size = 128,
      icon_mipmaps = 3,
      shift = {100, 100}
    }
  }
  return icons
end
function util.technology_icon_constant_mining(technology_icon)
  local icons =
  {
    {
      icon = technology_icon,
      icon_size = 256, icon_mipmaps = 4
    },
    {
      icon = "__core__/graphics/icons/technology/constants/constant-mining.png",
      icon_size = 128,
      icon_mipmaps = 3,
      shift = {100, 100}
    }
  }
  return icons
end

function util.parse_energy(energy)

  local ending = energy:sub(energy:len())
  if not (ending == "J" or ending == "W") then
    error(ending.. " is not a valid unit of energy")
  end

  local multiplier = (ending == "W" and  1 / 60) or 1
  local magnitude = energy:sub(energy:len() - 1, energy:len() - 1)

  if tonumber(magnitude) then
    return tonumber(energy:sub(1, energy:len()-1)) * multiplier
  end

  multiplier = multiplier * (energy_chars[magnitude] or error(magnitude.. " is not valid magnitude"))
  return tonumber(energy:sub(1, energy:len()-2)) * multiplier

end

function util.product_amount(product)
  return product.probability * (product.amount or ((product.amount_min + product.amount_max) / 2))
end

function util.empty_sprite(animation_length)
  return
  {
    filename = "__core__/graphics/empty.png",
    priority = "extra-high",
    width = 1,
    height = 1,
    frame_count = 1,
    repeat_count = animation_length,
    direction_count = 1
  }
end

function util.draw_as_glow(layer)
  layer.draw_as_glow = true
  if layer.hr_version then
    layer.hr_version.draw_as_glow = true
  end
  return layer
end

function util.remove_tile_references(data, array_of_tiles_to_remove)
  -- Does not handle:
  --   explicit tile filters in "selection-tool" items
  --   ItemPrototype::place_as_tile
  --   TilePrototype::next_direction
  --   TilePrototype::transition_merges_with_tile
  --   general tile transitions, only removes tile names from water_tile_type_names

  if (type(array_of_tiles_to_remove) ~= "table") then
    error("The second parameter of util.remove_tile_reference() is expected to be array of strings.")
  end

  local tiles_to_remove = {}
  for i, n in pairs(array_of_tiles_to_remove) do
    tiles_to_remove[n] = true
  end

  local remove_from_mapping = function(mapping)
    if not mapping then
      return
    end

    for _, item in pairs(mapping) do
      if item.tiles then
        for i, t in pairs(item.tiles) do
          if t and tiles_to_remove[t] then
            item.tiles[i] = nil
          end
        end
      end
    end
  end

  for k,e in pairs(data.raw["character"]) do
    remove_from_mapping(e.footstep_particle_triggers)
    remove_from_mapping(e.synced_footstep_particle_triggers)
    remove_from_mapping(e.footprint_particles)
  end

  for k,e in pairs(data.raw["car"]) do
    remove_from_mapping(e.track_particle_triggers)
  end

  if data.raw["fire"] then
    for k, fire in pairs(data.raw["fire"]) do
      if fire.burnt_patch_alpha_variations then
        for i, v in pairs(fire.burnt_patch_alpha_variations) do
          if v and v.tile and tiles_to_remove[v.tile] then
            fire.burnt_patch_alpha_variations[i] = nil
          end
        end
      end
    end
  end

  if water_tile_type_names then
    for i = #water_tile_type_names, 1, -1 do
      if tiles_to_remove[water_tile_type_names[i]] then
          table.remove(water_tile_type_names, i)
      end
    end
  end
end

local remove = table.remove
util.remove_from_list = function(list, value)
  for k, v in pairs (list) do
    if v == value then
      remove(list, k)
      return true
    end
  end
  return false
end

util.list_to_map = function(list)
  local map = {}
  --Here I am trusting you not to give a list of junk.
  for k, value in pairs(list) do
    map[value] = true
  end
  return map
end

return util