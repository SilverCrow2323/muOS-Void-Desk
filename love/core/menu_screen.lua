local sm      = require("core.scene_manager")
local theme   = require("theme.loader")
local input   = require("core.input")
local chrome  = require("core.chrome")
local effects = require("core.effects")
local font    = require("core.font")
local nodes   = require("core.nodes")
local anim    = require("core.anim")
local bg_anim = require("core.bg_anim")

local M = {}

local function draw_badge(x, y, size, color, label, alpha)
    alpha = alpha or 1
    love.graphics.setColor(color[1]*0.18, color[2]*0.18, color[3]*0.18, 0.9 * alpha)
    love.graphics.rectangle("fill", x, y, size, size, 5)
    love.graphics.setColor(color[1], color[2], color[3], 0.95 * alpha)
    love.graphics.setLineWidth(1.5)
    love.graphics.rectangle("line", x, y, size, size, 5)
    local f = font.bold(16) or love.graphics.newFont(16)
    love.graphics.setFont(f)
    local tw = f:getWidth(label)
    local th = f:getHeight()
    love.graphics.setColor(color[1], color[2], color[3], alpha)
    love.graphics.print(label, x + (size - tw)/2, y + (size - th)/2)
end

function M.new(config)
    local scene = {}
    local selected = 1
    local node_color = nodes.color_for(config.node_idx or 0)
    local title = config.title or "HUB"
    local items = config.items or {}
    local status_msg = config.status or "Ready"
    local bg_kind = bg_anim.for_node(config.node_idx or 0)
    local t_enter = 0   -- entrance animation timer
    local item_font = font.regular(15) or love.graphics.newFont(15)
    local desc_font = font.regular(11) or love.graphics.newFont(11)
    local status_font = font.regular(12) or love.graphics.newFont(12)

    function scene.enter(args)
        selected = 1
        status_msg = config.status or "Ready"
        t_enter = 0
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

    function scene.update(dt)
        if t_enter < 1 then t_enter = math.min(1, t_enter + dt / 0.55) end
    end

    function scene.set_status(msg) status_msg = msg end

    function scene.draw()
        local W, H = love.graphics.getDimensions()
        local th = theme.get()

        -- Screen opens on BLACK
        love.graphics.clear(0, 0, 0, 1)

        -- 1. Background animation (fades in over first 300ms)
        local bg_alpha = math.min(1, t_enter * 2.5)
        if bg_alpha > 0.02 then
            bg_anim.draw(bg_kind, W, H, love.timer.getTime(),
                         node_color, bg_alpha)
        end

        -- 2. Ambient node-color gradient (fades in after bg)
        local grad_alpha = math.min(1, math.max(0, (t_enter - 0.15) * 2.5))
        if grad_alpha > 0.02 then
            for i = 0, 10 do
                local t = i / 10
                love.graphics.setColor(node_color[1], node_color[2], node_color[3],
                                       0.035 * (1 - t) * grad_alpha)
                love.graphics.rectangle("fill", 0,
                    chrome.HEADER_H + 4 + i * 32, W, 32)
            end
        end

        -- 3. Menu items (staggered entrance)
        local item_top = chrome.HEADER_H + 14
        local row_h = 44
        local pulse = anim.pulse(love.timer.getTime(), 2.5)

        for i, item in ipairs(items) do
            local delay = (i - 1) * 0.07
            local it = math.max(0, math.min(1, (t_enter - delay) / 0.30))
            if it > 0.01 then
                local y_base = item_top + (i - 1) * row_h
                local slide = (1 - it) * 25   -- slides up from below
                local y = y_base + slide
                local item_alpha = it
                local is_sel = (i == selected)

                if is_sel then
                    pcall(effects.glow, W/2, y + row_h/2, (W - 40)/2,
                          node_color, 0.55 + 0.2 * pulse, 3)
                    love.graphics.setColor(node_color[1], node_color[2],
                                           node_color[3],
                                           (0.15 + 0.08 * pulse) * item_alpha)
                    love.graphics.rectangle("fill", 18, y, W - 36, row_h - 4, 6)
                    love.graphics.setColor(node_color[1], node_color[2],
                                           node_color[3], item_alpha)
                    love.graphics.setLineWidth(2)
                    love.graphics.rectangle("line", 18, y, W - 36, row_h - 4, 6)
                end

                local badge_sz = 30
                local bx = 28
                local by = y + (row_h - badge_sz) / 2
                draw_badge(bx, by, badge_sz,
                           is_sel and node_color or th.dim,
                           item.badge or "?", item_alpha)

                love.graphics.setFont(item_font)
                love.graphics.setColor(0, 0, 0, 0.6 * item_alpha)
                love.graphics.print(item.label, 71, y + 5)
                local col = is_sel and th.text or th.dim
                love.graphics.setColor(col[1], col[2], col[3], item_alpha)
                love.graphics.print(item.label, 70, y + 4)

                if item.desc then
                    love.graphics.setFont(desc_font)
                    love.graphics.setColor(th.dim[1]*0.85, th.dim[2]*0.85,
                                           th.dim[3]*0.85, 0.9 * item_alpha)
                    love.graphics.print(item.desc, 70, y + 25)
                end
            end
        end

        -- 4. Status panel (fades in last)
        local stat_t = math.max(0, math.min(1, (t_enter - 0.5) / 0.5))
        if stat_t > 0.01 then
            local status_y = H - chrome.FOOTER_H - 38
            love.graphics.setColor(th.panel_bg[1], th.panel_bg[2], th.panel_bg[3],
                                   0.9 * stat_t)
            love.graphics.rectangle("fill", 12, status_y, W - 24, 30, 4)
            love.graphics.setColor(node_color[1], node_color[2], node_color[3],
                                   0.55 * stat_t)
            love.graphics.rectangle("line", 12, status_y, W - 24, 30, 4)
            love.graphics.setFont(status_font)
            love.graphics.setColor(th.text[1], th.text[2], th.text[3], 0.9 * stat_t)
            love.graphics.print("> " .. status_msg, 20, status_y + 8)
        end

        -- 5. Chrome (fades in with elements)
        local chrome_t = math.min(1, t_enter * 2)
        if chrome_t > 0.01 then
            -- Temporary alpha via blend doesn't exist for text, so just draw
            -- when half-way in (300ms) as a snap
            if t_enter > 0.3 then
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
            end
        end

        if th.scanlines then effects.scanlines(W, H, 0.06) end
        if th.vignette  then effects.vignette(W, H, 0.35) end
        love.graphics.setColor(1, 1, 1, 1)
    end

    return scene
end

return M
