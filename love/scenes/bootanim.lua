local sm     = require("core.scene_manager")
local theme  = require("theme.loader")
local font   = require("core.font")
local anim   = require("core.anim")

local scene = {}
local t, dur = 0, 3.0
local next_scene = "nexus"
local display_name = "VOID-DESK"
local on_complete = nil

function scene.enter(args)
    args = args or {}
    t = 0
    dur = args.duration or 3.0
    next_scene = args.next or "nexus"
    display_name = args.name or "VOID-DESK"
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
    local th = theme.get()
    local acc = th.accent
    local cx, cy = W/2, H/2

    love.graphics.clear(0.015, 0.015, 0.02, 1)

    -- tunnel rings
    for i = 1, 26 do
        local phase = ((t * 0.75 + i * 0.10) % 1.0)
        local r = phase * 520
        if r > 6 then
            local alpha = (1 - phase) * 0.55
            love.graphics.setColor(acc[1], acc[2], acc[3], alpha)
            love.graphics.setLineWidth(2)
            love.graphics.circle("line", cx, cy, r)
        end
    end

    -- rotating arcs
    for k = 0, 5 do
        local rot = t * 1.3 + k * (math.pi / 3)
        love.graphics.setColor(acc[1], acc[2], acc[3], 0.35)
        love.graphics.setLineWidth(3)
        love.graphics.arc("line", "open", cx, cy, 90 + k * 22,
                          rot, rot + math.pi / 4)
    end

    -- center glow
    local pulse = 0.5 + 0.5 * math.sin(t * 3)
    for g = 3, 1, -1 do
        love.graphics.setColor(acc[1], acc[2], acc[3], 0.055 / g * (1 + pulse))
        love.graphics.circle("fill", cx, cy, 70 * g)
    end

    -- Title
    local fade = math.min(1, math.max(0, (t - 0.4) / 0.8))
    if fade > 0 then
        local f = font.bold(44) or love.graphics.newFont(44)
        love.graphics.setFont(f)
        local tw = f:getWidth(display_name)
        love.graphics.setColor(0, 0, 0, 0.7 * fade)
        love.graphics.print(display_name, cx - tw/2 + 2, cy - 26)
        love.graphics.setColor(1, 1, 1, fade)
        love.graphics.print(display_name, cx - tw/2, cy - 28)
    end

    -- Subtitle
    local subfade = math.min(1, math.max(0, (t - 1.5) / 0.8))
    if subfade > 0 then
        local f = font.regular(15) or love.graphics.newFont(15)
        love.graphics.setFont(f)
        local sub = "SPDW FACTORY"
        local sw = f:getWidth(sub)
        love.graphics.setColor(acc[1], acc[2], acc[3], subfade * 0.95)
        love.graphics.print(sub, cx - sw/2, cy + 34)
    end

    -- Progress bar
    local pct = math.min(1, t / dur)
    love.graphics.setColor(0.10, 0.12, 0.15, 1)
    love.graphics.rectangle("fill", cx - 110, H - 44, 220, 3, 2)
    love.graphics.setColor(acc[1], acc[2], acc[3], 1)
    love.graphics.rectangle("fill", cx - 110, H - 44, 220 * pct, 3, 2)

    -- Hint
    if t < dur - 0.5 then
        local f = font.regular(10) or love.graphics.newFont(10)
        love.graphics.setFont(f)
        love.graphics.setColor(0.5, 0.55, 0.6, 0.7)
        love.graphics.print("Press ESC to skip", cx - 50, H - 22)
    end
end

return scene
