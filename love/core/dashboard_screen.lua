local sm      = require("core.scene_manager")
local theme   = require("theme.loader")
local input   = require("core.input")
local chrome  = require("core.chrome")
local effects = require("core.effects")
local font    = require("core.font")
local nodes   = require("core.nodes")
local anim    = require("core.anim")
local bg_anim = require("core.bg_anim")
local widgets = require("core.widgets")

local M = {}

function M.new(config)
    local scene = {}
    local node_color = nodes.color_for(config.node_idx or 0)
    local title = config.title or "HUB"
    local items = config.items or {}
    local bg_kind = bg_anim.for_node(config.node_idx or 0)
    local t_enter = 0
    local selected = 1
    local status_msg = config.status or "Ready"

    local widget_h = config.widget_height or 150
    local widgets_draw = config.widgets_draw
    local on_enter = config.on_enter
    local on_update = config.on_update
    scene._data = {}

    local menu_top = chrome.HEADER_H + widget_h + 10
    local row_h = 32
    local status_font = font.regular(11) or love.graphics.newFont(11)

    function scene.enter(args)
        selected = 1
        t_enter = 0
        status_msg = config.status or "Ready"
        scene._t = 0
        if on_enter then on_enter(scene, args) end
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
            elseif action == "b" then
                sm.switch("nexus", {})
            end
        end)
    end

    function scene.update(dt)
        if t_enter < 1 then t_enter = math.min(1, t_enter + dt / 0.55) end
        if on_update then on_update(scene, dt) end
    end

    function scene.set_status(msg) status_msg = msg end
    function scene.set_data(k, v) scene._data[k] = v end
    function scene.get_data(k) return scene._data[k] end

    function scene.draw()
        local W, H = love.graphics.getDimensions()
        local th = theme.get()

        love.graphics.clear(0, 0, 0, 1)

        -- Background animation
        local bg_a = math.min(1, t_enter * 2.5)
        if bg_a > 0.02 then
            bg_anim.draw(bg_kind, W, H, love.timer.getTime(), node_color, bg_a * 0.65)
        end

        -- Widget area (entrance from 0.1 to 0.5 of t_enter)
        local w_t = math.max(0, math.min(1, (t_enter - 0.10) / 0.40))
        if w_t > 0.02 and widgets_draw then
            widgets_draw(scene, w_t)
        end

        -- Menu (staggered, starts at 0.30)
        for i, item in ipairs(items) do
            local delay = 0.30 + (i - 1) * 0.05
            local it = math.max(0, math.min(1, (t_enter - delay) / 0.25))
            if it > 0.01 then
                local y = menu_top + (i - 1) * row_h + (1 - it) * 12
                widgets.menu_row(16, y, W - 32, row_h - 2,
                                  item.badge or "?", item.label or "",
                                  item.desc, i == selected, th, node_color, it)
            end
        end

        -- Status panel
        local st = math.max(0, math.min(1, (t_enter - 0.55) / 0.30))
        if st > 0.01 then
            local sy = H - chrome.FOOTER_H - 32
            love.graphics.setColor(th.panel_bg[1], th.panel_bg[2], th.panel_bg[3], 0.92 * st)
            love.graphics.rectangle("fill", 12, sy, W - 24, 26, 4)
            love.graphics.setColor(node_color[1], node_color[2], node_color[3], 0.6 * st)
            love.graphics.rectangle("line", 12, sy, W - 24, 26, 4)
            love.graphics.setFont(status_font)
            love.graphics.setColor(th.text[1], th.text[2], th.text[3], 0.92 * st)
            love.graphics.print("> " .. status_msg, 20, sy + 7)
        end

        -- Chrome
        if t_enter > 0.25 then
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

        if th.scanlines then effects.scanlines(W, H, 0.06) end
        if th.vignette  then effects.vignette(W, H, 0.35) end
        love.graphics.setColor(1, 1, 1, 1)
    end

    return scene
end

return M
