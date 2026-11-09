-- Small QR Code generator: byte mode, error correction level M, versions 1-10
-- (up to 213 bytes: plenty for a Tailscale login URL).
-- Needs LuaJIT's `bit` module (LÖVE ships LuaJIT).
--
--   local qr = require("lib.qr")
--   local ok, modules, size, info = qr.encode("https://example.com")
--   -- modules[y][x] == true  ->  dark module (1-based indices, y = row)
--
-- The algorithm follows the QR Code (ISO/IEC 18004) layout rules; it is verified in
-- tests/test_qr.sh against python-qrcode (identical matrices) and OpenCV (decoding).
local bit = require("bit")
local band, bxor, lshift, rshift = bit.band, bit.bxor, bit.lshift, bit.rshift

local qr = {}

-- ------------------------------------------------------------ GF(256) / RS
local EXP, LOG = {}, {}
do
  local x = 1
  for i = 0, 254 do
    EXP[i] = x
    LOG[x] = i
    x = lshift(x, 1)
    if x >= 256 then x = bxor(x, 0x11D) end
  end
  for i = 255, 510 do EXP[i] = EXP[i - 255] end
end

local function gmul(a, b)
  if a == 0 or b == 0 then return 0 end
  return EXP[LOG[a] + LOG[b]]
end

local generators = {}
local function generator(n)
  if generators[n] then return generators[n] end
  local g = { 1 }
  for i = 0, n - 1 do
    local ng = {}
    for k = 1, #g + 1 do ng[k] = 0 end
    for k = 1, #g do
      ng[k] = bxor(ng[k], g[k])
      ng[k + 1] = bxor(ng[k + 1], gmul(g[k], EXP[i]))
    end
    g = ng
  end
  generators[n] = g
  return g
end

local function rs_remainder(data, n)
  local g = generator(n)
  local res = {}
  for i = 1, n do res[i] = 0 end
  for _, d in ipairs(data) do
    local factor = bxor(d, res[1])
    table.remove(res, 1)
    res[n] = 0
    for i = 1, n do res[i] = bxor(res[i], gmul(g[i + 1], factor)) end
  end
  return res
end

-- ------------------------------------------------------------ tables (level M)
-- [version] = { total codewords, ec codewords per block, { {blocks, data codewords per block}, ... } }
local EC_M = {
  [1] = { 26, 10, { { 1, 16 } } },
  [2] = { 44, 16, { { 1, 28 } } },
  [3] = { 70, 26, { { 1, 44 } } },
  [4] = { 100, 18, { { 2, 32 } } },
  [5] = { 134, 24, { { 2, 43 } } },
  [6] = { 172, 16, { { 4, 27 } } },
  [7] = { 196, 18, { { 4, 31 } } },
  [8] = { 242, 22, { { 2, 38 }, { 2, 39 } } },
  [9] = { 292, 22, { { 3, 36 }, { 2, 37 } } },
  [10] = { 346, 26, { { 4, 43 }, { 1, 44 } } },
}
local ALIGN = {
  [1] = {}, [2] = { 6, 18 }, [3] = { 6, 22 }, [4] = { 6, 26 }, [5] = { 6, 30 },
  [6] = { 6, 34 }, [7] = { 6, 22, 38 }, [8] = { 6, 24, 42 }, [9] = { 6, 26, 46 }, [10] = { 6, 28, 50 },
}
local EC_BITS_M = 0 -- format-info indicator for level M

local function data_capacity(v)
  local n = 0
  for _, grp in ipairs(EC_M[v][3]) do n = n + grp[1] * grp[2] end
  return n
end

-- ------------------------------------------------------------ bit helpers
local function getbit(x, i) return band(rshift(x, i), 1) == 1 end

-- ------------------------------------------------------------ matrix
local function new_matrix(size, fill)
  local m = {}
  for y = 1, size do
    local row = {}
    for x = 1, size do row[x] = fill end
    m[y] = row
  end
  return m
end

local function build_function_patterns(v)
  local size = 17 + 4 * v
  local mod, isfn = new_matrix(size, false), new_matrix(size, false)

  local function setfn(x, y, dark) -- x,y 0-based
    mod[y + 1][x + 1] = dark
    isfn[y + 1][x + 1] = true
  end

  for i = 0, size - 1 do -- timing
    setfn(6, i, i % 2 == 0)
    setfn(i, 6, i % 2 == 0)
  end
  local function finder(cx, cy)
    for dy = -4, 4 do
      for dx = -4, 4 do
        local dist = math.max(math.abs(dx), math.abs(dy))
        local xx, yy = cx + dx, cy + dy
        if xx >= 0 and xx < size and yy >= 0 and yy < size then
          setfn(xx, yy, dist ~= 2 and dist ~= 4)
        end
      end
    end
  end
  finder(3, 3)
  finder(size - 4, 3)
  finder(3, size - 4)

  local pos = ALIGN[v]
  local n = #pos
  for i = 1, n do
    for j = 1, n do
      if not ((i == 1 and j == 1) or (i == 1 and j == n) or (i == n and j == 1)) then
        local cx, cy = pos[i], pos[j]
        for dy = -2, 2 do
          for dx = -2, 2 do
            setfn(cx + dx, cy + dy, math.max(math.abs(dx), math.abs(dy)) ~= 1)
          end
        end
      end
    end
  end

  -- reserve the format areas (real bits are drawn per mask)
  for i = 0, 8 do
    if not isfn[9][i + 1] then setfn(i, 8, false) end
    if not isfn[i + 1][9] then setfn(8, i, false) end
  end
  for i = 0, 7 do
    setfn(size - 1 - i, 8, false)
    setfn(8, size - 1 - i, false)
  end
  setfn(8, size - 8, true) -- the always-dark module

  if v >= 7 then
    local rem = v
    for _ = 1, 12 do rem = bxor(lshift(rem, 1), (rshift(rem, 11)) * 0x1F25) end
    local bits = bit.bor(lshift(v, 12), rem)
    for i = 0, 17 do
      local a, b = size - 11 + i % 3, math.floor(i / 3)
      setfn(a, b, getbit(bits, i))
      setfn(b, a, getbit(bits, i))
    end
  end
  return mod, isfn, size
end

local function draw_format(mod, size, mask)
  local data = bit.bor(lshift(EC_BITS_M, 3), mask)
  local rem = data
  for _ = 1, 10 do rem = bxor(lshift(rem, 1), (rshift(rem, 9)) * 0x537) end
  local bits = bxor(bit.bor(lshift(data, 10), rem), 0x5412)
  local function set(x, y, d) mod[y + 1][x + 1] = d end
  for i = 0, 5 do set(8, i, getbit(bits, i)) end
  set(8, 7, getbit(bits, 6))
  set(8, 8, getbit(bits, 7))
  set(7, 8, getbit(bits, 8))
  for i = 9, 14 do set(14 - i, 8, getbit(bits, i)) end
  for i = 0, 7 do set(size - 1 - i, 8, getbit(bits, i)) end
  for i = 8, 14 do set(8, size - 15 + i, getbit(bits, i)) end
  set(8, size - 8, true)
end

local MASKS = {
  [0] = function(x, y) return (x + y) % 2 == 0 end,
  [1] = function(x, y) return y % 2 == 0 end,
  [2] = function(x, y) return x % 3 == 0 end,
  [3] = function(x, y) return (x + y) % 3 == 0 end,
  [4] = function(x, y) return (math.floor(x / 3) + math.floor(y / 2)) % 2 == 0 end,
  [5] = function(x, y) return x * y % 2 + x * y % 3 == 0 end,
  [6] = function(x, y) return (x * y % 2 + x * y % 3) % 2 == 0 end,
  [7] = function(x, y) return ((x + y) % 2 + x * y % 3) % 2 == 0 end,
}

local function penalty(mod, size)
  local score = 0
  local function line_score(get)
    for a = 1, size do
      local run, last = 0, nil
      local hist = {}
      for b = 1, size do
        local c = get(a, b)
        hist[b] = c and 1 or 0
        if c == last then
          run = run + 1
          if run == 5 then score = score + 3 elseif run > 5 then score = score + 1 end
        else
          run, last = 1, c
        end
      end
      -- finder-like pattern 1011101 with 4 light modules on a side
      for b = 1, size - 6 do
        if hist[b] == 1 and hist[b + 1] == 0 and hist[b + 2] == 1 and hist[b + 3] == 1 and
           hist[b + 4] == 1 and hist[b + 5] == 0 and hist[b + 6] == 1 then
          local before, after = true, true
          for k = 1, 4 do
            if b - k >= 1 and hist[b - k] == 1 then before = false end
            if b + 6 + k <= size and hist[b + 6 + k] == 1 then after = false end
          end
          if (before and b - 4 >= 1) or (after and b + 10 <= size) then score = score + 40 end
        end
      end
    end
  end
  line_score(function(a, b) return mod[a][b] end)
  line_score(function(a, b) return mod[b][a] end)
  for y = 1, size - 1 do
    for x = 1, size - 1 do
      local c = mod[y][x]
      if c == mod[y][x + 1] and c == mod[y + 1][x] and c == mod[y + 1][x + 1] then score = score + 3 end
    end
  end
  local dark = 0
  for y = 1, size do for x = 1, size do if mod[y][x] then dark = dark + 1 end end end
  local total = size * size
  local k = math.ceil(math.abs(dark * 20 - total * 10) / total) - 1
  return score + math.max(k, 0) * 10
end

-- ------------------------------------------------------------ encoding
local function make_codewords(bytes, v)
  local cap = data_capacity(v)
  local bits = {}
  local function put(val, len)
    for i = len - 1, 0, -1 do bits[#bits + 1] = band(rshift(val, i), 1) end
  end
  put(4, 4) -- byte mode
  put(#bytes, v < 10 and 8 or 16)
  for _, b in ipairs(bytes) do put(b, 8) end
  local maxbits = cap * 8
  for _ = 1, math.min(4, maxbits - #bits) do bits[#bits + 1] = 0 end
  while #bits % 8 ~= 0 do bits[#bits + 1] = 0 end
  local data = {}
  for i = 1, #bits, 8 do
    local b = 0
    for k = 0, 7 do b = b * 2 + bits[i + k] end
    data[#data + 1] = b
  end
  local pad = { 0xEC, 0x11 }
  local pi = 1
  while #data < cap do
    data[#data + 1] = pad[pi]
    pi = 3 - pi
  end

  -- split into blocks, add EC, interleave
  local blocks, pos = {}, 1
  local ecn = EC_M[v][2]
  for _, grp in ipairs(EC_M[v][3]) do
    for _ = 1, grp[1] do
      local d = {}
      for k = 0, grp[2] - 1 do d[#d + 1] = data[pos + k] end
      pos = pos + grp[2]
      blocks[#blocks + 1] = { data = d, ec = rs_remainder(d, ecn) }
    end
  end
  local out, maxlen = {}, 0
  for _, b in ipairs(blocks) do maxlen = math.max(maxlen, #b.data) end
  for i = 1, maxlen do
    for _, b in ipairs(blocks) do if b.data[i] then out[#out + 1] = b.data[i] end end
  end
  for i = 1, ecn do
    for _, b in ipairs(blocks) do out[#out + 1] = b.ec[i] end
  end
  return out
end

--- Encode `text`. Returns ok, modules, size, info{version=, mask=}   (or false, errmsg)
function qr.encode(text, forced_mask)
  local bytes = { text:byte(1, -1) }
  local v
  for ver = 1, 10 do
    local head = 4 + (ver < 10 and 8 or 16)
    if head + 8 * #bytes <= data_capacity(ver) * 8 then v = ver; break end
  end
  if not v then return false, "text too long for QR version 10-M (max 213 bytes)" end

  local words = make_codewords(bytes, v)
  local base, isfn, size = build_function_patterns(v)

  -- place codewords
  local i, total = 0, #words * 8
  local right = size - 1
  while right >= 1 do
    if right == 6 then right = 5 end
    for vert = 0, size - 1 do
      for j = 0, 1 do
        local x = right - j
        local upward = band(right + 1, 2) == 0
        local y = upward and (size - 1 - vert) or vert
        if not isfn[y + 1][x + 1] and i < total then
          base[y + 1][x + 1] = getbit(words[rshift(i, 3) + 1], 7 - band(i, 7))
          i = i + 1
        end
      end
    end
    right = right - 2
  end

  local best, best_score, best_mask
  for mask = 0, 7 do
    if forced_mask == nil or forced_mask == mask then
      local m = {}
      for y = 1, size do
        local row = {}
        for x = 1, size do
          local d = base[y][x]
          if not isfn[y][x] and MASKS[mask](x - 1, y - 1) then d = not d end
          row[x] = d
        end
        m[y] = row
      end
      draw_format(m, size, mask)
      local s = penalty(m, size)
      if not best_score or s < best_score then best, best_score, best_mask = m, s, mask end
    end
  end
  return true, best, size, { version = v, mask = best_mask }
end

return qr
