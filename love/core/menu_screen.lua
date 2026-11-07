local sm = require("core.scene_manager")
local theme = require("theme.loader")
local input = require("core.input")
local chrome = require("core.chrome")
local effects = require("core.effects")
local font = require("core.font")
local nodes = require("core.nodes")
local anim = require("core.anim")

local M = {}

local function draw_badge(x, y, size, color, label)
    love.graphics.setColor(color[1]*0.20, color[2]*0.20, color[3]*0.20, 0.9)
    love.graphics.rectangle("fill", x, y, size, size, 5)
    love.graphics.setColor(color[1], color[2], color[3], 0.95)
    love.graphics.setLineWidth(1.5)
    love.graphics.rectangle("line", x, y, size, size, 5)
    local f = font.bold(16) or love.graphics.newFont(16)
    love.graphics.setFont(f)
    local tw = f:getWidth(label)
    local th = f:getHeight()
    love.graphics.setColor(color[1], color[2], color[3], 1)
    love.graphics.print(label, x + (size - tw)/2, y + (size - th)/2)
end

function M.new(config)
    local scene = {}
    local selected = 1
    local node_color = nodes.color_for(config.node_idx or 0)
    local title = config.title or "HUB"
    local items = config.items or {}
    local status_msg = config.status or "Ready"
    local item_font = font.regular(15) or love.graphics.newFont(15)
    local desc_font = font.regular(11) or love.graphics.newFont(11)
    local status_font = font.regular(12) or love.graphics.newFont(12)

    function scene.enter(args)
        selected = 1
        status_msg = config.status or "Ready"
        input.clear()
        input.on("press", function(action)
            if action == "up" then
                selected = math.max(1, selected - 1)
            elseif action == "down" then
                selected = math.min(#items, selected + 1)
            elseif action == "a" then
                local item = items[selected]
                if item and item.action then
                    local msg = item.action(scene)
                    if msg then status_msg = msg end
                end
            elseif action == "b" or action == "menu" then
                sm.switch("nexus", {})
            end
        end)
    end

    function scene.update(dt) end
    function scene.set_status(msg) status_msg = msg end

    function scene.draw()
        local W, H = love.graphics.getDimensions()
        local th = theme.get()
        love.graphics.clear(th.bg[1], th.bg[2], th.bg[3], 1)

        -- Ambient node-color gradient
        for i = 0, 10 do
            local t = i / 10
            love.graphics.setColor(node_color[1], node_color[2], node_color[3],
                                   0.03 * (1 - t))
            love.graphics.rectangle("fill", 0, 44 + i * 32, W, 32)
        end

        local y = 58
        local row_h = 42
        local pulse = anim.pulse(love.timer.getTime(), 2.5)

        for i, item in ipairs(items) do
            local is_sel = (i == selected)

            if is_sel then
                pcall(effects.glow, W/2, y + row_h/2, (W - 40)/2,
                      node_color, 0.55 + 0.2 * pulse, 3)
                love.graphics.setColor(node_color[1], node_color[2], node_color[3],
                                       0.15 + 0.08 * pulse)
                love.graphics.rectangle("fill", 18, y, W - 36, row_h - 4, 6)
                love.graphics.setColor(node_color[1], node_color[2], node_color[3], 1)
                love.graphics.setLineWidth(2)
                love.graphics.rectangle("line", 18, y, W - 36, row_h - 4, 6)
            end

            local badge_sz = 28
            local bx = 28
            local by = y + (row_h - badge_sz)/2
            draw_badge(bx, by, badge_sz,
                       is_sel and node_color or th.dim,
                       item.badge or "?")

            love.graphics.setFont(item_font)
            love.graphics.setColor(0, 0, 0, 0.6)
            love.graphics.print(item.label, 69, y + 5)
            local col = is_sel and th.text or th.dim
            love.graphics.setColor(col[1], col[2], col[3], 1)
            love.graphics.print(item.label, 68, y + 4)

            if item.desc then
                love.graphics.setFont(desc_font)
                love.graphics.setColor(th.dim[1]*0.85, th.dim[2]*0.85, th.dim[3]*0.85, 0.9)
                love.graphics.print(item.desc, 68, y + 24)
            end

            y = y + row_h
        end

        -- Status panel
        local status_y = H - chrome.FOOTER_H - 36
        love.graphics.setColor(th.panel_bg[1], th.panel_bg[2], th.panel_bg[3], 0.9)
        love.graphics.rectangle("fill", 12, status_y, W - 24, 28, 4)
        love.graphics.setColor(node_color[1], node_color[2], node_color[3], 0.55)
        love.graphics.rectangle("line", 12, status_y, W - 24, 28, 4)
        love.graphics.setFont(status_font)
        love.graphics.setColor(th.text[1], th.text[2], th.text[3], 0.9)
        love.graphics.print("> " .. status_msg, 20, status_y + 7)

        -- Chrome
        chrome.draw_header({
            theme = th, title = "Void-DESK", subtitle = title,
            status_icons = { "wifi", "battery" },
        })
        chrome.draw_footer({
            theme = th,
            hints = {
                { icon = "dpad",  label = "Navigate" },
                { icon = "btn_a", label = "Run" },
                { icon = "btn_b", label = "Back" },
            },
            right_text = "v10.5.1",
        })

        if th.scanlines then effects.scanlines(W, H, 0.06) end
        if th.vignette  then effects.vignette(W, H, 0.35) end
        love.graphics.setColor(1, 1, 1, 1)
    end

    return scene
end

return M
