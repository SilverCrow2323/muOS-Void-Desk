-- VOID DESK // LÖVE / LUA ENGINE
-- Mirrored companion to vd_bootanim.py:
-- optical nucleus on the left, distorted spiral expands to the right.
local sm = require("core.scene_manager")
local font = require("core.font")

local scene = {}
local t, dur = 0, 3.0
local next_scene = "nexus"
local display_name = "DESKTOP"
local on_complete = nil

local BG = { 0.006, 0.009, 0.016 }
local ACCENT = { 1.000, 0.390, 0.145 }
local HOT = { 1.000, 0.735, 0.390 }
local MID = { 0.560, 0.145, 0.070 }
local DIM = { 0.105, 0.035, 0.025 }
local WHITE = { 0.985, 0.950, 0.900 }

local function clamp(v, lo, hi)
    return math.max(lo, math.min(hi, v))
end

local function set_rgb(c, alpha)
    love.graphics.setColor(c[1], c[2], c[3], alpha or 1)
end

local function mix(a, b, q)
    return {
        a[1] + (b[1] - a[1]) * q,
        a[2] + (b[2] - a[2]) * q,
        a[3] + (b[3] - a[3]) * q,
    }
end

local function draw_background(W, H, now)
    love.graphics.clear(BG[1], BG[2], BG[3], 1)
    love.graphics.setLineWidth(1)
    set_rgb({ 0.035, 0.045, 0.058 }, 0.75)
    for x = W * 0.25 + 20, W - 12, 42 do
        local dx = math.sin(x * 0.025 + now) * 4
        love.graphics.line(x + dx, 0, x + dx, H)
    end
    for y = 34, H, 48 do
        love.graphics.line(W * 0.25, y, W, y)
    end
end

local function draw_reflection(W, H, now)
    -- Quarto sinistro specchiante: rifrazione verticale e righe d'interferenza.
    local edge = W * 0.25
    love.graphics.setColor(0.012, 0.012, 0.020, 1)
    love.graphics.rectangle("fill", 0, 0, edge, H)
    for i = 0, 18 do
        local base = i * (edge / 18)
        local phase = i * 0.47
        local points = {}
        for j = 0, 32 do
            local y = j * H / 32
            local wave = math.sin(y * 0.031 + now * 2.1 + phase) * 7
            wave = wave + math.sin(y * 0.012 - now * 1.3 + phase) * 4
            points[#points + 1] = base + wave
            points[#points + 1] = y
        end
        set_rgb((i % 4 == 0) and MID or { 0.040, 0.070, 0.085 },
                (i % 4 == 0) and 0.75 or 0.66)
        love.graphics.line(points)
    end
    love.graphics.setColor(0.055, 0.110, 0.125, 0.55)
    for y = 20, H, 31 do
        local shift = math.sin(y * 0.04 + now * 2.5) * 12
        love.graphics.line(shift, y, edge, y)
    end
    love.graphics.setColor(ACCENT[1], ACCENT[2], ACCENT[3], 0.34)
    love.graphics.line(edge, 0, edge, H)
end

local function spiral_points(cx, cy, max_r, phase, extent, now)
    local points = {}
    local turns = math.pi * 8.6
    for i = 0, 180 do
        local u = (i / 180) * extent
        local radius = 9 + max_r * u
        local angle = turns * u + phase + math.sin(u * 17 + now * 2.0) * 0.13
        local warp = math.sin(angle * 1.9 - now * 3.2 + phase) * (3 + 19 * u)
        local x = cx + radius * math.cos(angle) + warp * 0.62
        local y = cy + radius * 0.64 * math.sin(angle) + warp
        points[#points + 1] = x
        points[#points + 1] = y
    end
    return points
end

local function draw_spiral(W, H, now, extent)
    local cx, cy = W * 0.18, H * 0.5
    local max_r = W * 0.91
    local strands = {
        { 0.00, ACCENT, 2.2, 0.92 },
        { 0.15, MID, 2.0, 0.84 },
        { -0.15, HOT, 1.0, 0.88 },
    }
    for _, strand in ipairs(strands) do
        local pts = spiral_points(cx, cy, max_r, strand[1], extent, now)
        set_rgb(strand[2], strand[4])
        love.graphics.setLineWidth(strand[3])
        if #pts >= 4 then love.graphics.line(pts) end
    end
end

local function draw_core(W, H, now)
    local cx, cy = W * 0.18, H * 0.5
    local pulse = 1 + 0.035 * math.sin(now * 5)
    love.graphics.setLineWidth(2)
    set_rgb(DIM, 0.9)
    love.graphics.ellipse("line", cx, cy, 49 * pulse, 49 * pulse * 0.74)
    set_rgb(MID, 0.95)
    love.graphics.ellipse("line", cx, cy, 39, 39 * 0.74)
    love.graphics.setColor(0.020, 0.025, 0.034, 1)
    love.graphics.circle("fill", cx, cy, 31)
    love.graphics.setColor(0, 0, 0, 1)
    love.graphics.circle("fill", cx, cy, 25)
    set_rgb(ACCENT, 0.75)
    love.graphics.setLineWidth(1)
    love.graphics.arc("line", "open", cx, cy, 29, now * 1.7,
                      now * 1.7 + math.pi * 0.72)
    set_rgb(HOT, 0.86)
    love.graphics.rectangle("fill", cx - 2, cy - 37, 4, 10)
    set_rgb(ACCENT, 0.8)
    love.graphics.rectangle("fill", cx - 2, cy + 27, 4, 10)
end

local function draw_logo(W, H, progress, target)
    -- La tavola di marca occupa i 3/4 destri ed è allineata a destra:
    -- è la specchiatura intenzionale della composizione Python.
    local px, py = W * 0.305, (H - 154) * 0.5
    local pw, ph = W * 0.64, 154
    love.graphics.setColor(0.010, 0.020, 0.030, 0.965)
    love.graphics.rectangle("fill", px, py, pw, ph, 7, 7)
    set_rgb(MID, 0.9)
    love.graphics.setLineWidth(2)
    love.graphics.rectangle("line", px, py, pw, ph, 7, 7)
    set_rgb(ACCENT, 0.94)
    love.graphics.rectangle("fill", px + pw - 16, py + 15, 3, ph - 30)
    love.graphics.setColor(0.30, 0.085, 0.045, 0.9)
    love.graphics.rectangle("fill", px + pw - 22, py + 15, 1, ph - 30)

    local small = font.regular(12)
    local brand = "SPDW FACTORY  //  QWASAR ENV"
    font.print_shadow(brand, px + pw - 24 - small:getWidth(brand), py + 18,
                      small, HOT, { 0, 0, 0, 0.7 })

    local title_font = font.bold(46)
    love.graphics.setFont(title_font)
    local title = "VOID DESK"
    local tw = title_font:getWidth(title)
    font.print_shadow(title, px + pw - 29 - tw, py + 54, title_font,
                      WHITE, { 0, 0, 0, 0.9 })

    local tag = "LOVE / LUA ENGINE"
    local tag_font = font.mono(11)
    local tag_w = tag_font:getWidth(tag) + 20
    local tag_x, tag_y = px + pw - 25 - tag_w, py + 119
    love.graphics.setColor(0.17, 0.045, 0.022, 1)
    love.graphics.rectangle("fill", tag_x, tag_y, tag_w, 23, 3, 3)
    set_rgb(ACCENT, 0.95)
    love.graphics.rectangle("line", tag_x, tag_y, tag_w, 23, 3, 3)
    love.graphics.setFont(tag_font)
    love.graphics.print(tag, tag_x + 10, tag_y + 5)

    local target_text = "TARGET // " .. tostring(target or "DESKTOP"):upper()
    local target_font = font.mono(10)
    love.graphics.setFont(target_font)
    set_rgb(mix({ 0.18, 0.13, 0.11 }, HOT, 0.45), 0.9)
    love.graphics.print(target_text,
                        px + pw - 25 - target_font:getWidth(target_text),
                        tag_y + 6)

    love.graphics.setColor(0.18, 0.055, 0.032, 1)
    love.graphics.rectangle("fill", px + 25, py + ph - 8, pw - 50, 2)
    set_rgb(ACCENT, 0.95)
    love.graphics.rectangle("fill", px + 25, py + ph - 8,
                            (pw - 50) * progress, 2)
end

function scene.enter(args)
    args = args or {}
    t = 0
    dur = args.duration or 3.0
    next_scene = args.next or "nexus"
    display_name = args.name or "DESKTOP"
    on_complete = args.on_complete
end

function scene.update(dt)
    t = t + dt
    if t >= dur then
        if on_complete then pcall(on_complete) end
        sm.switch(next_scene, {})
    end
end

function scene.keypressed(k)
    if k == "escape" or k == "space" or k == "return" then
        if on_complete then pcall(on_complete) end
        sm.switch(next_scene, {})
    end
end

function scene.draw()
    local W, H = love.graphics.getDimensions()
    local now = t
    local progress = clamp(t / math.max(0.1, dur), 0, 1)
    local extent = clamp(t / 1.85, 0, 1)
    extent = extent * extent * (3 - 2 * extent)
    local fade = clamp((t - 0.28) / 0.8, 0, 1)

    draw_background(W, H, now)
    draw_reflection(W, H, now)
    draw_spiral(W, H, now, extent)
    draw_core(W, H, now)
    draw_logo(W, H, progress, display_name)

    love.graphics.setColor(ACCENT[1], ACCENT[2], ACCENT[3], 0.28 * fade)
    for i = 0, 4 do
        local y = H * 0.20 + i * H * 0.15
        love.graphics.rectangle("fill", 10, y, 2 + (i % 2), 13)
    end

    if t < dur - 0.35 then
        local hint = font.regular(10)
        love.graphics.setFont(hint)
        love.graphics.setColor(0.54, 0.47, 0.42, 0.78)
        love.graphics.printf("PRESS ESC TO SKIP", W * 0.25, H - 21,
                             W * 0.70, "center")
    end
end

return scene
