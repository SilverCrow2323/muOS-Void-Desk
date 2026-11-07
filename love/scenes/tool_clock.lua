local sm      = require("core.scene_manager")
local theme   = require("theme.loader")
local input   = require("core.input")
local chrome  = require("core.chrome")
local font    = require("core.font")
local nodes   = require("core.nodes")
local anim    = require("core.anim")

local scene = {}
local t_enter = 0
local nc = nodes.color_for(4)

-- Clock state
local hand_sweep = 0      -- 0..1 entrance animation
local trail = { hour = {}, min = {}, sec = {} }   -- motion trails
local TRAIL_LEN = 12

-- 60 particles orbiting (each = 1 second)
local particles = {}
local function init_particles()
    particles = {}
    for i = 1, 60 do
        particles[i] = {
            angle = (i / 60) * math.pi * 2 - math.pi / 2,
            life = 0,
        }
    end
end

function scene.enter(args)
    t_enter = 0
    hand_sweep = 0
    init_particles()
    input.clear()
    input.on("press", function(action)
        if action == "b" or action == "menu" then
            sm.switch("hub_toolbox", {})
        end
    end)
end

function scene.update(dt)
    if t_enter < 1 then t_enter = math.min(1, t_enter + dt / 1.2) end
    hand_sweep = math.min(1, hand_sweep + dt / 0.9)

    local now = os.time()
    local t = os.date("*t", now)
    -- Compute hand angles
    local sec_a = (t.sec + os.clock() % 1) / 60 * math.pi * 2 - math.pi / 2
    local min_a = (t.min + t.sec / 60) / 60 * math.pi * 2 - math.pi / 2
    local hour_a = ((t.hour % 12) + t.min / 60) / 12 * math.pi * 2 - math.pi / 2

    -- Entrance: hands sweep in fast then settle
    if hand_sweep < 1 then
        local e = anim.ease_out_cubic(hand_sweep)
        sec_a = sec_a + (1 - e) * math.pi * 4
        min_a = min_a + (1 - e) * math.pi * 2
        hour_a = hour_a + (1 - e) * math.pi
    end

    -- Trails
    for _, list in pairs(trail) do
        for i = #list, 1, -1 do
            list[i].t = list[i].t + dt / 0.4
            if list[i].t >= 1 then table.remove(list, i) end
        end
    end
    table.insert(trail.sec, {a = sec_a, t = 0})
    table.insert(trail.min, {a = min_a, t = 0})
    table.insert(trail.hour, {a = hour_a, t = 0})
    for _, list in pairs(trail) do
        while #list > TRAIL_LEN do table.remove(list, 1) end
    end

    -- Particles: 60 dots, each lights up when second matches
    for i = 1, 60 do
        local p = particles[i]
        if i == t.sec then
            p.life = 1.0
        else
            p.life = math.max(0, p.life - dt * 2)
        end
    end
end

local function draw_hand(cx, cy, angle, length, width, col, alpha)
    local ex = cx + math.cos(angle) * length
    local ey = cy + math.sin(angle) * length
    love.graphics.setColor(col[1], col[2], col[3], alpha or 1)
    love.graphics.setLineWidth(width)
    love.graphics.line(cx, cy, ex, ey)
    return ex, ey
end

local function draw_trail(cx, cy, list, length, width, col)
    for i, entry in ipairs(list) do
        local a = 1 - entry.t
        local len = length * (1 - entry.t * 0.3)
        local ex = cx + math.cos(entry.a) * len
        local ey = cy + math.sin(entry.a) * len
        love.graphics.setColor(col[1], col[2], col[3], a * 0.4)
        love.graphics.setLineWidth(width * a)
        love.graphics.line(cx, cy, ex, ey)
    end
end

function scene.draw()
    local W, H = love.graphics.getDimensions()
    local th = theme.get()
    love.graphics.clear(0, 0, 0, 1)

    local content_y = chrome.HEADER_H
    local content_h = H - chrome.FOOTER_H - content_y

    -- Center for analog clock
    local cx = W / 2
    local cy = content_y + content_h * 0.42
    local radius = math.min(W, content_h) * 0.30

    -- Ambient glow behind clock
    local pulse = 0.85 + 0.15 * math.sin(love.timer.getTime() * 1.5)
    for k = 5, 1, -1 do
        love.graphics.setColor(nc[1], nc[2], nc[3], 0.03 / k * pulse)
        love.graphics.circle("fill", cx, cy, radius * (1 + k * 0.25))
    end

    -- Outer ring
    love.graphics.setColor(nc[1], nc[2], nc[3], 0.75)
    love.graphics.setLineWidth(2)
    love.graphics.circle("line", cx, cy, radius)
    -- Inner ring
    love.graphics.setColor(nc[1], nc[2], nc[3], 0.25)
    love.graphics.setLineWidth(1)
    love.graphics.circle("line", cx, cy, radius * 0.94)

    -- 60 particles orbitali (1 per secondo)
    local now = os.date("*t", os.time())
    for i = 1, 60 do
        local p = particles[i]
        local r = radius * 0.94
        local px = cx + math.cos(p.angle) * r
        local py = cy + math.sin(p.angle) * r
        local is_current = (i == now.sec)
        if is_current then
            love.graphics.setColor(nc[1], nc[2], nc[3], 0.9)
            love.graphics.circle("fill", px, py, 4)
            -- pulse ring around current
            local pr = radius + 6 + math.sin(love.timer.getTime() * 8) * 4
            love.graphics.setColor(nc[1], nc[2], nc[3], 0.35)
            love.graphics.setLineWidth(2)
            love.graphics.circle("line", cx, cy, pr)
        else
            local a = 0.25 + p.life * 0.65
            love.graphics.setColor(nc[1], nc[2], nc[3], a)
            love.graphics.circle("fill", px, py, 2 + p.life * 2)
        end
    end

    -- Tick marks (12)
    for i = 0, 11 do
        local a = (i / 12) * math.pi * 2 - math.pi / 2
        local x1 = cx + math.cos(a) * (radius * 0.88)
        local y1 = cy + math.sin(a) * (radius * 0.88)
        local x2 = cx + math.cos(a) * radius
        local y2 = cy + math.sin(a) * radius
        love.graphics.setColor(0.85, 0.90, 0.95, 0.65)
        love.graphics.setLineWidth(i % 3 == 0 and 2 or 1)
        love.graphics.line(x1, y1, x2, y2)
    end

    -- Hands with trails
    local sec_a, min_a, hour_a
    local t = os.date("*t", os.time())
    sec_a = (t.sec) / 60 * math.pi * 2 - math.pi / 2
    min_a = (t.min + t.sec / 60) / 60 * math.pi * 2 - math.pi / 2
    hour_a = ((t.hour % 12) + t.min / 60) / 12 * math.pi * 2 - math.pi / 2

    if hand_sweep < 1 then
        local e = anim.ease_out_cubic(hand_sweep)
        sec_a = sec_a + (1 - e) * math.pi * 4
        min_a = min_a + (1 - e) * math.pi * 2
        hour_a = hour_a + (1 - e) * math.pi
    end

    draw_trail(cx, cy, trail.hour, radius * 0.5, 5, nc)
    draw_trail(cx, cy, trail.min, radius * 0.72, 4, nc)
    draw_trail(cx, cy, trail.sec, radius * 0.85, 2, nc)

    -- Hour hand (thick)
    draw_hand(cx, cy, hour_a, radius * 0.5, 5,
        {nc[1] * 0.9, nc[2] * 0.9, nc[3] * 0.9}, 1)
    -- Minute hand
    draw_hand(cx, cy, min_a, radius * 0.72, 4,
        {nc[1], nc[2], nc[3]}, 1)
    -- Second hand (thin, glowing)
    love.graphics.setColor(nc[1], nc[2], nc[3], 0.3)
    love.graphics.setLineWidth(4)
    love.graphics.line(cx, cy,
        cx + math.cos(sec_a) * radius * 0.85,
        cy + math.sin(sec_a) * radius * 0.85)
    draw_hand(cx, cy, sec_a, radius * 0.85, 1.5, nc, 1)

    -- Center hub
    love.graphics.setColor(0.05, 0.06, 0.09, 1)
    love.graphics.circle("fill", cx, cy, 8)
    love.graphics.setColor(nc[1], nc[2], nc[3], 1)
    love.graphics.setLineWidth(2)
    love.graphics.circle("line", cx, cy, 8)
    love.graphics.circle("fill", cx, cy, 2)

    -- Digital clock (bottom, mono large)
    local f_dig = font.mono(36) or love.graphics.newFont(36)
    love.graphics.setFont(f_dig)
    local dtext = os.date("%H:%M:%S")
    local tw = f_dig:getWidth(dtext)
    local dig_y = cy + radius + 24
    love.graphics.setColor(0, 0, 0, 0.6)
    love.graphics.print(dtext, cx - tw/2 + 2, dig_y + 2)
    love.graphics.setColor(nc[1], nc[2], nc[3], 1)
    love.graphics.print(dtext, cx - tw/2, dig_y)

    -- Date (small, below)
    local f_date = font.regular(14) or love.graphics.newFont(14)
    love.graphics.setFont(f_date)
    local dtext2 = os.date("%A, %d %B %Y")
    local tw2 = f_date:getWidth(dtext2)
    love.graphics.setColor(0.6, 0.7, 0.8, 1)
    love.graphics.print(dtext2, cx - tw2/2, dig_y + 46)

    chrome.draw_header({theme = th, title = "Void-DESK", subtitle = "CLOCK",
                       status_icons = {"clock", "battery"}})
    chrome.draw_footer({theme = th,
        hints = {{icon = "btn_b", label = "Back"}},
        right_text = "v10.5.1"})
end

return scene
