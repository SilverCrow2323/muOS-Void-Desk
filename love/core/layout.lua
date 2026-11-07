-- Centralized layout for VoidDesk LÖVE frontend.
-- Base design: 640x480. Everything scales with window size
-- (and with OS DPI via t.window.highdpi=true in conf.lua).
--
-- To tweak: edit the base_* numbers below. All scenes and widgets
-- pull from layout.get() at draw time, so changes apply instantly.

local layout = {}

local BASE_W, BASE_H = 640, 480

-- Base sizes at 640x480 (what we DESIGN for)
local base = {
    -- Chrome
    header_h    = 56,
    footer_h    = 42,
    -- Menu
    row_h       = 46,
    icon_size   = 28,
    -- Widgets panel
    widget_h    = 110,
    status_h    = 26,
    strip_h     = 22,
    -- Fonts
    font_title    = 26,
    font_subtitle = 18,
    font_clock    = 16,
    font_hint     = 14,
    font_label    = 18,
    font_desc     = 13,
    font_value    = 15,
    font_status   = 14,
    font_tiny     = 11,
    font_small    = 14,
}

local cache, cache_key = nil, ""

function layout.reset()
    cache, cache_key = nil, ""
end

function layout.get()
    local W, H = love.graphics.getDimensions()
    local key = W .. "x" .. H
    if cache and cache_key == key then return cache end

    -- Uniform scale: fit 640x480 into current window
    local scale = math.min(W / BASE_W, H / BASE_H)
    scale = math.max(0.5, math.min(4.0, scale))

    local function px(n) return math.floor(n * scale + 0.5) end
    local function fs(n) return math.max(8,  math.floor(n * scale + 0.5)) end

    cache = { scale = scale, W = px(BASE_W), H = px(BASE_H) }
    for k, v in pairs(base) do
        if k:sub(1, 5) == "font_" then
            cache[k] = fs(v)
        else
            cache[k] = px(v)
        end
    end
    cache_key = key
    return cache
end

-- Reset cache on window resize
function layout.on_resize()
    layout.reset()
end

return layout
