local sm      = require("core.scene_manager")
local theme   = require("theme.loader")
local input   = require("core.input")
local chrome  = require("core.chrome")
local effects = require("core.effects")
local font    = require("core.font")
local nodes   = require("core.nodes")
local anim    = require("core.anim")

local stub = {}
local node = nil
local color = { 0.5, 0.5, 0.5 }
local icon = nil
local start_t = 0

function stub.enter(args)
    local idx = args and args.idx or 0
    node = nodes.get(idx) or { name = "Unknown", icon = "start", idx = 0 }
    color = nodes.color_for(idx)
    icon = nodes.image_for(node.icon)
    start_t = love.timer.getTime()
    input.clear()
    input.on("press", function(action)
        if action == "b" or action == "menu" then
            sm.switch("nexus", {})
        end
    end)
end

function stub.update(dt) end

function stub.draw()
    local W, H = love.graphics.getDimensions()
    local th = theme.get()
    love.graphics.clear(th.bg[1], th.bg[2], th.bg[3], 1)

    -- ambient node-color gradient from top
    for i = 0, 12 do
        local t = i / 12
        love.graphics.setColor(color[1], color[2], color[3], 0.05 * (1 - t))
        love.graphics.rectangle("fill", 0, 50 + i * 30, W, 30)
    end

    -- subtle animated pulse ring around icon
    local pulse = anim.pulse(love.timer.getTime(), 2)
    local cx, cy = W / 2, 210
    for k = 3, 1, -1 do
        love.graphics.setColor(color[1], color[2], color[3],
                               0.10 * pulse / k)
        love.graphics.setLineWidth(2)
        love.graphics.circle("line", cx, cy, 80 + k * 8 + pulse * 6)
    end

    -- big icon
    if icon then
        local sz = 160
        local s = sz / math.max(icon:getWidth(), icon:getHeight())
        love.graphics.setColor(1, 1, 1, 1)
        love.graphics.draw(icon,
            cx - icon:getWidth() * s / 2,
            cy - icon:getHeight() * s / 2, 0, s, s)
    end

    -- title
    local f_big = font.bold(26) or love.graphics.newFont(26)
    love.graphics.setFont(f_big)
    local title = node.name
    local tw = f_big:getWidth(title)
    love.graphics.setColor(0, 0, 0, 0.65)
    love.graphics.print(title, cx - tw / 2 + 1, 341)
    love.graphics.setColor(color[1], color[2], color[3], 1)
    love.graphics.print(title, cx - tw / 2, 340)

    -- "coming soon" subtitle
    local f_med = font.regular(14) or love.graphics.newFont(14)
    love.graphics.setFont(f_med)
    local sub = "Screen under construction"
    local sw = f_med:getWidth(sub)
    love.graphics.setColor(th.dim[1], th.dim[2], th.dim[3], 0.9)
    love.graphics.print(sub, cx - sw / 2, 380)

    local sub2 = "Press B to return to Nexus"
    local sw2 = f_med:getWidth(sub2)
    love.graphics.setColor(th.dim[1] * 0.7, th.dim[2] * 0.7, th.dim[3] * 0.7, 1)
    love.graphics.print(sub2, cx - sw2 / 2, 402)

    -- chrome
    chrome.draw_header({
        theme = th,
        title = "Void-DESK",
        subtitle = node.name,
        status_icons = { "wifi", "battery" },
    })
    chrome.draw_footer({
        theme = th,
        hints = {
            { icon = "btn_b", label = "Back" },
        },
        right_text = "v10.5.1",
    })

    if th.scanlines then effects.scanlines(W, H, 0.06) end
    if th.vignette  then effects.vignette(W, H, 0.4) end
    love.graphics.setColor(1, 1, 1, 1)
end

return stub
