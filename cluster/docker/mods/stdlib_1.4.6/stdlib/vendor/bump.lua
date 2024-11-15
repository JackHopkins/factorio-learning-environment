local bump = {
    _VERSION     = 'bump v3.1.7',
    _URL         = 'https://github.com/kikito/bump.lua',
    _DESCRIPTION = 'A collision detection library for Lua',
    _LICENSE     = [[
      MIT LICENSE

      Copyright (c) 2014 Enrique García Cota

      Permission is hereby granted, free of charge, to any person obtaining a
      copy of this software and associated documentation files (the
      "Software"), to deal in the Software without restriction, including
      without limitation the rights to use, copy, modify, merge, publish,
      distribute, sublicense, and/or sell copies of the Software, and to
      permit persons to whom the Software is furnished to do so, subject to
      the following conditions:

      The above copyright notice and this permission notice shall be included
      in all copies or substantial portions of the Software.

      THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
      OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
      MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
      IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
      CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
      TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
      SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
    ]]
  }

  ------------------------------------------
  -- Auxiliary functions
  ------------------------------------------
  local DELTA = 1e-10 -- floating-point margin of error

  local abs, floor, ceil, min, max = math.abs, math.floor, math.ceil, math.min, math.max

  local function sign(x)
    if x > 0 then return 1 end
    if x == 0 then return 0 end
    return -1
  end

  local function nearest(x, a, b)
    if abs(a - x) < abs(b - x) then return a else return b end
  end

  local function assertType(desiredType, value, name)
    if type(value) ~= desiredType then
      error(name .. ' must be a ' .. desiredType .. ', but was ' .. tostring(value) .. '(a ' .. type(value) .. ')')
    end
  end

  local function assertIsPositiveNumber(value, name)
    if type(value) ~= 'number' or value <= 0 then
      error(name .. ' must be a positive integer, but was ' .. tostring(value) .. '(' .. type(value) .. ')')
    end
  end

  local function assertIsRect(x,y,w,h)
    assertType('number', x, 'x')
    assertType('number', y, 'y')
    assertIsPositiveNumber(w, 'w')
    assertIsPositiveNumber(h, 'h')
  end

  local defaultFilter = function()
    return 'slide'
  end

  ------------------------------------------
  -- Rectangle functions
  ------------------------------------------

  local function rect_getNearestCorner(x,y,w,h, px, py)
    return nearest(px, x, x+w), nearest(py, y, y+h)
  end

  -- This is a generalized implementation of the liang-barsky algorithm, which also returns
  -- the normals of the sides where the segment intersects.
  -- Returns nil if the segment never touches the rect
  -- Notice that normals are only guaranteed to be accurate when initially ti1, ti2 == -math.huge, math.huge
  local function rect_getSegmentIntersectionIndices(x,y,w,h, x1,y1,x2,y2, ti1,ti2)
    ti1, ti2 = ti1 or 0, ti2 or 1
    local dx, dy = x2-x1, y2-y1
    local nx, ny
    local nx1, ny1, nx2, ny2 = 0,0,0,0
    local p, q, r

    for side = 1,4 do
      if     side == 1 then nx,ny,p,q = -1,  0, -dx, x1 - x     -- left
      elseif side == 2 then nx,ny,p,q =  1,  0,  dx, x + w - x1 -- right
      elseif side == 3 then nx,ny,p,q =  0, -1, -dy, y1 - y     -- top
      else                  nx,ny,p,q =  0,  1,  dy, y + h - y1 -- bottom
      end

      if p == 0 then
        if q <= 0 then return nil end
      else
        r = q / p
        if p < 0 then
          if     r > ti2 then return nil
          elseif r > ti1 then ti1,nx1,ny1 = r,nx,ny
          end
        else -- p > 0
          if     r < ti1 then return nil
          elseif r < ti2 then ti2,nx2,ny2 = r,nx,ny
          end
        end
      end
    end

    return ti1,ti2, nx1,ny1, nx2,ny2
  end

  -- Calculates the minkowsky difference between 2 rects, which is another rect
  local function rect_getDiff(x1,y1,w1,h1, x2,y2,w2,h2)
    return x2 - x1 - w1,
           y2 - y1 - h1,
           w1 + w2,
           h1 + h2
  end

  local function rect_containsPoint(x,y,w,h, px,py)
    return px - x > DELTA      and py - y > DELTA and
           x + w - px > DELTA  and y + h - py > DELTA
  end

  local function rect_isIntersecting(x1,y1,w1,h1, x2,y2,w2,h2)
    return x1 < x2+w2 and x2 < x1+w1 and
           y1 < y2+h2 and y2 < y1+h1
  end

  local function rect_getSquareDistance(x1,y1,w1,h1, x2,y2,w2,h2)
    local dx = x1 - x2 + (w1 - w2)/2
    local dy = y1 - y2 + (h1 - h2)/2
    return dx*dx + dy*dy
  end

  local function rect_detectCollision(x1,y1,w1,h1, x2,y2,w2,h2, goalX, goalY)
    goalX = goalX or x1
    goalY = goalY or y1

    local dx, dy      = goalX - x1, goalY - y1
    local x,y,w,h     = rect_getDiff(x1,y1,w1,h1, x2,y2,w2,h2)

    local overlaps, ti, nx, ny

    if rect_containsPoint(x,y,w,h, 0,0) then -- item was intersecting other
      local px, py    = rect_getNearestCorner(x,y,w,h, 0, 0)
      local wi, hi    = min(w1, abs(px)), min(h1, abs(py)) -- area of intersection
      ti              = -wi * hi -- ti is the negative area of intersection
      overlaps = true
    else
      local ti1,ti2,nx1,ny1 = rect_getSegmentIntersectionIndices(x,y,w,h, 0,0,dx,dy, -math.huge, math.huge)

      -- item tunnels into other
      if ti1
      and ti1 < 1
      and (abs(ti1 - ti2) >= DELTA) -- special case for rect going through another rect's corner
      and (0 < ti1 + DELTA
        or 0 == ti1 and ti2 > 0)
      then
        ti, nx, ny = ti1, nx1, ny1
        overlaps   = false
      end
    end

    if not ti then return end

    local tx, ty

    if overlaps then
      if dx == 0 and dy == 0 then
        -- intersecting and not moving - use minimum displacement vector
        local px, py = rect_getNearestCorner(x,y,w,h, 0,0)
        if abs(px) < abs(py) then py = 0 else px = 0 end
        nx, ny = sign(px), sign(py)
        tx, ty = x1 + px, y1 + py
      else
        -- intersecting and moving - move in the opposite direction
        local ti1, _
        ti1,_,nx,ny = rect_getSegmentIntersectionIndices(x,y,w,h, 0,0,dx,dy, -math.huge, 1)
        if not ti1 then return end
        tx, ty = x1 + dx * ti1, y1 + dy * ti1
      end
    else -- tunnel
      tx, ty = x1 + dx * ti, y1 + dy * ti
    end

    return {
      overlaps  = overlaps,
      ti        = ti,
      move      = {x = dx, y = dy},
      normal    = {x = nx, y = ny},
      touch     = {x = tx, y = ty},
      itemRect  = {x = x1, y = y1, w = w1, h = h1},
      otherRect = {x = x2, y = y2, w = w2, h = h2}
    }
  end

  ------------------------------------------
  -- Grid functions
  ------------------------------------------

  local function grid_toWorld(cellSize, cx, cy)
    return (cx - 1)*cellSize, (cy-1)*cellSize
  end

  local function grid_toCell(cellSize, x, y)
    return floor(x / cellSize) + 1, floor(y / cellSize) + 1
  end

  -- grid_traverse* functions are based on "A Fast Voxel Traversal Algorithm for Ray Tracing",
  -- by John Amanides and Andrew Woo - http://www.cse.yorku.ca/~amana/research/grid.pdf
  -- It has been modified to include both cells when the ray "touches a grid corner",
  -- and with a different exit condition

  local function grid_traverse_initStep(cellSize, ct, t1, t2)
    local v = t2 - t1
    if     v > 0 then
      return  1,  cellSize / v, ((ct + v) * cellSize - t1) / v
    elseif v < 0 then
      return -1, -cellSize / v, ((ct + v - 1) * cellSize - t1) / v
    else
      return 0, math.huge, math.huge
    end
  end

  local function grid_traverse(cellSize, x1,y1,x2,y2, f)
    local cx1,cy1        = grid_toCell(cellSize, x1,y1)
    local cx2,cy2        = grid_toCell(cellSize, x2,y2)
    local stepX, dx, tx  = grid_traverse_initStep(cellSize, cx1, x1, x2)
    local stepY, dy, ty  = grid_traverse_initStep(cellSize, cy1, y1, y2)
    local cx,cy          = cx1,cy1

    f(cx, cy)

    -- The default implementation had an infinite loop problem when
    -- approaching the last cell in some occassions. We finish iterating
    -- when we are *next* to the last cell
    while abs(cx - cx2) + abs(cy - cy2) > 1 do
      if tx < ty then
        tx, cx = tx + dx, cx + stepX
        f(cx, cy)
      else
        -- Addition: include both cells when going through corners
        if tx == ty then f(cx + stepX, cy) end
        ty, cy = ty + dy, cy + stepY
        f(cx, cy)
      end
    end

    -- If we have not arrived to the last cell, use it
    if cx ~= cx2 or cy ~= cy2 then f(cx2, cy2) end

  end

  local function grid_toCellRect(cellSize, x,y,w,h)
    local cx,cy = grid_toCell(cellSize, x, y)
    local cr,cb = ceil((x+w) / cellSize), ceil((y+h) / cellSize)
    return cx, cy, cr - cx + 1, cb - cy + 1
  end

  ------------------------------------------
  -- Responses
  ------------------------------------------

  local touch = function(world, col, x,y,w,h, goalX, goalY, filter)
    return col.touch.x, col.touch.y, {}, 0
  end

  local cross = function(world, col, x,y,w,h, goalX, goalY, filter)
    local cols, len = world:project(col.item, x,y,w,h, goalX, goalY, filter)
    return goalX, goalY, cols, len
  end

  local slide = function(world, col, x,y,w,h, goalX, goalY, filter)
    goalX = goalX or x
    goalY = goalY or y

    local tch, move  = col.touch, col.move
    if move.x ~= 0 or move.y ~= 0 then
      if col.normal.x ~= 0 then
        goalX = tch.x
      else
        goalY = tch.y
      end
    end

    col.slide = {x = goalX, y = goalY}

    x,y = tch.x, tch.y
    local cols, len  = world:project(col.item, x,y,w,h, goalX, goalY, filter)
    return goalX, goalY, cols, len
  end

  local bounce = function(world, col, x,y,w,h, goalX, goalY, filter)
    goalX = goalX or x
    goalY = goalY or y

    local tch, move = col.touch, col.move
    local tx, ty = tch.x, tch.y

    local bx, by = tx, ty

    if move.x ~= 0 or move.y ~= 0 then
      local bnx, bny = goalX - tx, goalY - ty
      if col.normal.x == 0 then bny = -bny else bnx = -bnx end
      bx, by = tx + bnx, ty + bny
    end

    col.bounce   = {x = bx,  y = by}
    x,y          = tch.x, tch.y
    goalX, goalY = bx, by

    local cols, len    = world:project(col.item, x,y,w,h, goalX, goalY, filter)
    return goalX, goalY, cols, len
  end

  ------------------------------------------
  -- World
  ------------------------------------------

  local World = {}
  local World_mt = {__index = World}

  -- Private functions and methods

  local function sortByWeight(a,b) return a.weight < b.weight end

  local function sortByTiAndDistance(a,b)
    if a.ti == b.ti then
      local ir, ar, br = a.itemRect, a.otherRect, b.otherRect
      local ad = rect_getSquareDistance(ir.x,ir.y,ir.w,ir.h, ar.x,ar.y,ar.w,ar.h)
      local bd = rect_getSquareDistance(ir.x,ir.y,ir.w,ir.h, br.x,br.y,br.w,br.h)
      return ad < bd
    end
    return a.ti < b.ti
  end

  local function addItemToCell(self, item, cx, cy)
    self.rows[cy] = self.rows[cy] or setmetatable({}, {__mode = 'v'})
    local row = self.rows[cy]
    row[cx] = row[cx] or {itemCount = 0, x = cx, y = cy, items = setmetatable({}, {__mode = 'k'})}
    local cell = row[cx]
    self.nonEmptyCells[cell] = true
    if not cell.items[item] then
      cell.items[item] = true
      cell.itemCount = cell.itemCount + 1
    end
  end

  local function removeItemFromCell(self, item, cx, cy)
    local row = self.rows[cy]
    if not row or not row[cx] or not row[cx].items[item] then return false end

    local cell = row[cx]
    cell.items[item] = nil
    cell.itemCount = cell.itemCount - 1
    if cell.itemCount == 0 then
      self.nonEmptyCells[cell] = nil
    end
    return true
  end

  local function getDictItemsInCellRect(self, cl,ct,cw,ch)
    local items_dict = {}
    for cy=ct,ct+ch-1 do
      local row = self.rows[cy]
      if row then
        for cx=cl,cl+cw-1 do
          local cell = row[cx]
          if cell and cell.itemCount > 0 then -- no cell.itemCount > 1 because tunneling
            for item,_ in pairs(cell.items) do
              items_dict[item] = true
            end
          end
        end
      end
    end

    return items_dict
  end

  local function getCellsTouchedBySegment(self, x1,y1,x2,y2)

    local cells, cellsLen, visited = {}, 0, {}

    grid_traverse(self.cellSize, x1,y1,x2,y2, function(cx, cy)
      local row  = self.rows[cy]
      if not row then return end
      local cell = row[cx]
      if not cell or visited[cell] then return end

      visited[cell] = true
      cellsLen = cellsLen + 1
      cells[cellsLen] = cell
    end)

    return cells, cellsLen
  end

  local function getInfoAboutItemsTouchedBySegment(self, x1,y1, x2,y2, filter)
    local cells, len = getCellsTouchedBySegment(self, x1,y1,x2,y2)
    local cell, rect, l,t,w,h, ti1,ti2, tii0,tii1
    local visited, itemInfo, itemInfoLen = {},{},0
    for i=1,len do
      cell = cells[i]
      for item in pairs(cell.items) do
        if not visited[item] then
          visited[item]  = true
          if (not filter or filter(item)) then
            rect           = self.rects[item]
            l,t,w,h        = rect.x,rect.y,rect.w,rect.h

            ti1,ti2 = rect_getSegmentIntersectionIndices(l,t,w,h, x1,y1, x2,y2, 0, 1)
            if ti1 and ((0 < ti1 and ti1 < 1) or (0 < ti2 and ti2 < 1)) then
              -- the sorting is according to the t of an infinite line, not the segment
              tii0,tii1    = rect_getSegmentIntersectionIndices(l,t,w,h, x1,y1, x2,y2, -math.huge, math.huge)
              itemInfoLen  = itemInfoLen + 1
              itemInfo[itemInfoLen] = {item = item, ti1 = ti1, ti2 = ti2, weight = min(tii0,tii1)}
            end
          end
        end
      end
    end
    table.sort(itemInfo, sortByWeight)
    return itemInfo, itemInfoLen
  end

  local function getResponseByName(self, name)
    local response = self.responses[name]
    if not response then
      error(('Unknown collision type: %s (%s)'):format(name, type(name)))
    end
    return response
  end


  -- Misc Public Methods

  function World:addResponse(name, response)
    self.responses[name] = response
  end

  function World:project(item, x,y,w,h, goalX, goalY, filter)
    assertIsRect(x,y,w,h)

    goalX = goalX or x
    goalY = goalY or y
    filter  = filter  or defaultFilter

    local collisions, len = {}, 0

    local visited = {}
    if item ~= nil then visited[item] = true end

    -- This could probably be done with less cells using a polygon raster over the cells instead of a
    -- bounding rect of the whole movement. Conditional to building a queryPolygon method
    local tl, tt = min(goalX, x),       min(goalY, y)
    local tr, tb = max(goalX + w, x+w), max(goalY + h, y+h)
    local tw, th = tr-tl, tb-tt

    local cl,ct,cw,ch = grid_toCellRect(self.cellSize, tl,tt,tw,th)

    local dictItemsInCellRect = getDictItemsInCellRect(self, cl,ct,cw,ch)

    for other,_ in pairs(dictItemsInCellRect) do
      if not visited[other] then
        visited[other] = true

        local responseName = filter(item, other)
        if responseName then
          local ox,oy,ow,oh   = self:getRect(other)
          local col           = rect_detectCollision(x,y,w,h, ox,oy,ow,oh, goalX, goalY)

          if col then
            col.other    = other
            col.item     = item
            col.type     = responseName

            len = len + 1
            collisions[len] = col
          end
        end
      end
    end

    table.sort(collisions, sortByTiAndDistance)

    return collisions, len
  end

  function World:countCells()
    local count = 0
    for _,row in pairs(self.rows) do
      for _,_ in pairs(row) do
        count = count + 1
      end
    end
    return count
  end

  function World:hasItem(item)
    return not not self.rects[item]
  end

  function World:getItems()
    local items, len = {}, 0
    for item,_ in pairs(self.rects) do
      len = len + 1
      items[len] = item
    end
    return items, len
  end

  function World:countItems()
    local len = 0
    for _ in pairs(self.rects) do len = len + 1 end
    return len
  end

  function World:getRect(item)
    local rect = self.rects[item]
    if not rect then
      error('Item ' .. tostring(item) .. ' must be added to the world before getting its rect. Use world:add(item, x,y,w,h) to add it first.')
    end
    return rect.x, rect.y, rect.w, rect.h
  end

  function World:toWorld(cx, cy)
    return grid_toWorld(self.cellSize, cx, cy)
  end

  function World:toCell(x,y)
    return grid_toCell(self.cellSize, x, y)
  end


  --- Query methods

  function World:queryRect(x,y,w,h, filter)

    assertIsRect(x,y,w,h)

    local cl,ct,cw,ch = grid_toCellRect(self.cellSize, x,y,w,h)
    local dictItemsInCellRect = getDictItemsInCellRect(self, cl,ct,cw,ch)

    local items, len = {}, 0

    local rect
    for item,_ in pairs(dictItemsInCellRect) do
      rect = self.rects[item]
      if (not filter or filter(item))
      and rect_isIntersecting(x,y,w,h, rect.x, rect.y, rect.w, rect.h)
      then
        len = len + 1
        items[len] = item
      end
    end

    return items, len
  end

  function World:queryPoint(x,y, filter)
    local cx,cy = self:toCell(x,y)
    local dictItemsInCellRect = getDictItemsInCellRect(self, cx,cy,1,1)

    local items, len = {}, 0

    local rect
    for item,_ in pairs(dictItemsInCellRect) do
      rect = self.rects[item]
      if (not filter or filter(item))
      and rect_containsPoint(rect.x, rect.y, rect.w, rect.h, x, y)
      then
        len = len + 1
        items[len] = item
      end
    end

    return items, len
  end

  function World:querySegment(x1, y1, x2, y2, filter)
    local itemInfo, len = getInfoAboutItemsTouchedBySegment(self, x1, y1, x2, y2, filter)
    local items = {}
    for i=1, len do
      items[i] = itemInfo[i].item
    end
    return items, len
  end

  function World:querySegmentWithCoords(x1, y1, x2, y2, filter)
    local itemInfo, len = getInfoAboutItemsTouchedBySegment(self, x1, y1, x2, y2, filter)
    local dx, dy        = x2-x1, y2-y1
    local info, ti1, ti2
    for i=1, len do
      info  = itemInfo[i]
      ti1   = info.ti1
      ti2   = info.ti2

      info.weight  = nil
      info.x1      = x1 + dx * ti1
      info.y1      = y1 + dy * ti1
      info.x2      = x1 + dx * ti2
      info.y2      = y1 + dy * ti2
    end
    return itemInfo, len
  end


  --- Main methods

  function World:add(item, x,y,w,h)
    local rect = self.rects[item]
    if rect then
      error('Item ' .. tostring(item) .. ' added to the world twice.')
    end
    assertIsRect(x,y,w,h)

    self.rects[item] = {x=x,y=y,w=w,h=h}

    local cl,ct,cw,ch = grid_toCellRect(self.cellSize, x,y,w,h)
    for cy = ct, ct+ch-1 do
      for cx = cl, cl+cw-1 do
        addItemToCell(self, item, cx, cy)
      end
    end

    return item
  end

  function World:remove(item)
    local x,y,w,h = self:getRect(item)

    self.rects[item] = nil
    local cl,ct,cw,ch = grid_toCellRect(self.cellSize, x,y,w,h)
    for cy = ct, ct+ch-1 do
      for cx = cl, cl+cw-1 do
        removeItemFromCell(self, item, cx, cy)
      end
    end
  end

  function World:update(item, x2,y2,w2,h2)
    local x1,y1,w1,h1 = self:getRect(item)
    w2,h2 = w2 or w1, h2 or h1
    assertIsRect(x2,y2,w2,h2)

    if x1 ~= x2 or y1 ~= y2 or w1 ~= w2 or h1 ~= h2 then

      local cellSize = self.cellSize
      local cl1,ct1,cw1,ch1 = grid_toCellRect(cellSize, x1,y1,w1,h1)
      local cl2,ct2,cw2,ch2 = grid_toCellRect(cellSize, x2,y2,w2,h2)

      if cl1 ~= cl2 or ct1 ~= ct2 or cw1 ~= cw2 or ch1 ~= ch2 then

        local cr1, cb1 = cl1+cw1-1, ct1+ch1-1
        local cr2, cb2 = cl2+cw2-1, ct2+ch2-1
        local cyOut

        for cy = ct1, cb1 do
          cyOut = cy < ct2 or cy > cb2
          for cx = cl1, cr1 do
            if cyOut or cx < cl2 or cx > cr2 then
              removeItemFromCell(self, item, cx, cy)
            end
          end
        end

        for cy = ct2, cb2 do
          cyOut = cy < ct1 or cy > cb1
          for cx = cl2, cr2 do
            if cyOut or cx < cl1 or cx > cr1 then
              addItemToCell(self, item, cx, cy)
            end
          end
        end

      end

      local rect = self.rects[item]
      rect.x, rect.y, rect.w, rect.h = x2,y2,w2,h2

    end
  end

  function World:move(item, goalX, goalY, filter)
    local actualX, actualY, cols, len = self:check(item, goalX, goalY, filter)

    self:update(item, actualX, actualY)

    return actualX, actualY, cols, len
  end

  function World:check(item, goalX, goalY, filter)
    filter = filter or defaultFilter

    local visited = {[item] = true}
    local visitedFilter = function(itm, other)
      if visited[other] then return false end
      return filter(itm, other)
    end

    local cols, len = {}, 0

    local x,y,w,h = self:getRect(item)

    local projected_cols, projected_len = self:project(item, x,y,w,h, goalX,goalY, visitedFilter)

    while projected_len > 0 do
      local col = projected_cols[1]
      len       = len + 1
      cols[len] = col

      visited[col.other] = true

      local response = getResponseByName(self, col.type)

      goalX, goalY, projected_cols, projected_len = response(
        self,
        col,
        x, y, w, h,
        goalX, goalY,
        visitedFilter
      )
    end

    return goalX, goalY, cols, len
  end


  -- Public library functions

  bump.newWorld = function(cellSize)
    cellSize = cellSize or 64
    assertIsPositiveNumber(cellSize, 'cellSize')
    local world = setmetatable({
      cellSize       = cellSize,
      rects          = {},
      rows           = {},
      nonEmptyCells  = {},
      responses = {}
    }, World_mt)

    world:addResponse('touch', touch)
    world:addResponse('cross', cross)
    world:addResponse('slide', slide)
    world:addResponse('bounce', bounce)

    return world
  end

  bump.rect = {
    getNearestCorner              = rect_getNearestCorner,
    getSegmentIntersectionIndices = rect_getSegmentIntersectionIndices,
    getDiff                       = rect_getDiff,
    containsPoint                 = rect_containsPoint,
    isIntersecting                = rect_isIntersecting,
    getSquareDistance             = rect_getSquareDistance,
    detectCollision               = rect_detectCollision
  }

  bump.responses = {
    touch  = touch,
    cross  = cross,
    slide  = slide,
    bounce = bounce
  }

  return bump
