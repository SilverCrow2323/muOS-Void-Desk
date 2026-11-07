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
local icon    = require("core.icon")
local jobs    = require("core.jobs")

local M = {}

function M.new(config)
    local scene = {}
    local node_color = nodes.color_for(config.node_idx or 0)
    local title = config.title or "HUB"
    local items = config.items or {}
    local bg_kind = bg_anim.for_node(config.node_idx or 0)
    local t_enter = 0
    local selected = 1
    local scroll_offset = 0
    local status_msg = config.status or "Ready"

    local widget_h = config.widget_height or 150
    local widgets_draw = config.widgets_draw
    local on_enter = config.on_enter
    local on_update = config.on_update
    scene._data = {}

    local menu_top = chrome.HEADER_H + widget_h + 10
    local menu_bottom = 480 - chrome.FOOTER_H - 34
    local row_h = config.row_height or 38
    local status_font = font.regular(11) or love.graphics.newFont(11)

    local function get_live_items()
        if scene._get_items then
            local ok, res = pcall(scene._get_items)
            if ok and type(res) == "table" then return res end
        end
        return items
    end

    local function ensure_visible()
        local live = get_live_items()
        local visible_rows = math.max(1, math.floor((menu_bottom - menu_top) / row_h))
        if selected < 1 then selected = 1 end
        if selected > #live then selected = #live end
        if selected < scroll_offset + 1 then
            scroll_offset = selected - 1
        elseif selected > scroll_offset + visible_rows then
            scroll_offset = selected - visible_rows
        end
        local max_offset = math.max(0, #live - visible_rows)
        scroll_offset = math.max(0, math.min(scroll_offset, max_offset))
    end

    function scene.enter(args)
        selected = 1
        scroll_offset = 0
        t_enter = 0
        status_msg = config.status or "Ready"
        scene._t = 0
        if args and args.restore_state then
            scene.restore_state(args.restore_state)
        end
        if on_enter then on_enter(scene, args) end
        input.clear()
        input.on("press", function(action)
            local live = get_live_items()
            if action == "up" then
                selected = math.max(1, selected - 1)
                ensure_visible()
            elseif action == "down" then
                selected = math.min(#live, selected + 1)
                ensure_visible()
            elseif action == "a" then
                local item = live[selected]
                if item and item.action then
                    local msg = item.action(scene)
                    if msg then status_msg = msg end
                end
            elseif action == "b" then
                sm.switch("nexus", {})
            elseif action == "select" then
                jobs.toggle_overlay()
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

        local bg_a = math.min(1, t_enter * 2.5)
        if bg_a > 0.02 then
            bg_anim.draw(bg_kind, W, H, love.timer.getTime(), node_color, bg_a * 0.55)
        end

        local w_t = math.max(0, math.min(1, (t_enter - 0.10) / 0.40))
        if w_t > 0.02 and widgets_draw then
            widgets_draw(scene, w_t)
        end

        local live = get_live_items()
        local visible_rows = math.max(1, math.floor((menu_bottom - menu_top) / row_h))

        -- Menu items (with scissor)
        love.graphics.setScissor(0, menu_top - 2, W, menu_bottom - menu_top + 4)
        for i = 1, visible_rows do
            local idx = scroll_offset + i
            if idx > #live then break end
            local item = live[idx]
            local delay = 0.30 + (i - 1) * 0.04
            local it = math.max(0, math.min(1, (t_enter - delay) / 0.25))
            if it > 0.01 then
                local y = menu_top + (i - 1) * row_h + (1 - it) * 10
                widgets.menu_row(16, y, W - 32, row_h - 2, {
                    icon = item.icon,
                    badge = item.badge,
                    label = item.label or "",
                    desc = item.desc,
                    value = item.value,
                    value_color = item.value_color,
                    chevron = item.chevron ~= false and not item.value,
                    selected = (idx == selected),
                    theme = th,
                    node_color = node_color,
                    alpha = it,
                })
            end
        end
        love.graphics.setScissor()

        -- Item job spinners (drawn OUTSIDE scissor to avoid clipping)
        for i = 1, visible_rows do
            local idx = scroll_offset + i
            if idx > #live then break end
            local item = live[idx]
            if item.label then
                local n_active = jobs.count_for_name(item.label)
                if n_active > 0 then
                    local y = menu_top + (i - 1) * row_h
                    local sx = W - 42
                    local sy = y + row_h / 2
                    local t_now = love.timer.getTime()
                    local c = item.job_color or node_color
                    for k = 0, 5 do
                        local ang = t_now * 4 + k * math.pi / 3
                        local a = 0.3 + 0.7 * (1 - k / 6)
                        love.graphics.setColor(c[1], c[2], c[3], a)
                        love.graphics.circle("fill",
                            sx + math.cos(ang) * 6,
                            sy + math.sin(ang) * 6, 1.5)
                    end
                    if n_active > 1 then
                        love.graphics.setColor(0, 0, 0, 0.9)
                        love.graphics.circle("fill", sx + 10, sy - 8, 7)
                        love.graphics.setColor(c[1], c[2], c[3], 1)
                        love.graphics.circle("line", sx + 10, sy - 8, 7)
                        local f_b = font.bold(9) or love.graphics.newFont(9)
                        love.graphics.setFont(f_b)
                        love.graphics.setColor(c[1], c[2], c[3], 1)
                        love.graphics.print(tostring(n_active), sx + 7, sy - 12)
                    end
                end
            end
        end

        -- Scroll indicators
        if scroll_offset > 0 then
            pcall(icon.draw, "arrow_up", W - 26, menu_top - 4, 16, node_color, { alpha = 0.6 })
        end
        if scroll_offset + visible_rows < #live then
            pcall(icon.draw, "arrow_down", W - 26, menu_bottom - 14, 16, node_color, { alpha = 0.6 })
        end

        -- Status strip (only if jobs active)
        local running = jobs.total_running()
        if running > 0 then
            local strip_y = H - chrome.FOOTER_H - 26
            love.graphics.setColor(0.04, 0.06, 0.10, 0.95)
            love.graphics.rectangle("fill", 0, strip_y, W, 22)
            love.graphics.setColor(node_color[1], node_color[2], node_color[3], 0.5)
            love.graphics.rectangle("fill", 0, strip_y, W, 1)
            local first = nil
            for _, j in pairs(jobs.active) do
                if j.status == "running" or j.status == "starting" then
                    first = j; break
                end
            end
            if first then
                local c = first.color or node_color
                love.graphics.setColor(c[1], c[2], c[3], 1)
                love.graphics.circle("fill", 14, strip_y + 11, 4)
                local f_st = font.regular(11) or love.graphics.newFont(11)
                love.graphics.setFont(f_st)
                love.graphics.setColor(0.85, 0.88, 0.92, 1)
                love.graphics.print(
                    string.format("[%d] %s  %d%%",
                        running, first.name, first.progress or 0),
                    24, strip_y + 5)
                local bx = W - 200
                local bw = 100
                love.graphics.setColor(0.10, 0.12, 0.16, 1)
                love.graphics.rectangle("fill", bx, strip_y + 8, bw, 6, 2)
                local fw = bw * (first.progress or 0) / 100
                if fw > 1 then
                    love.graphics.setColor(c[1], c[2], c[3], 1)
                    love.graphics.rectangle("fill", bx, strip_y + 8, fw, 6, 2)
                end
                love.graphics.setColor(0.55, 0.6, 0.65, 1)
                love.graphics.print("SELECT: details", W - 100, strip_y + 5)
            end
        end

        -- Status panel
        local st = math.max(0, math.min(1, (t_enter - 0.55) / 0.30))
        if st > 0.01 then
            local sy = H - chrome.FOOTER_H - 30 - (running > 0 and 22 or 0)
            love.graphics.setColor(th.panel_bg[1], th.panel_bg[2], th.panel_bg[3], 0.92 * st)
            love.graphics.rectangle("fill", 12, sy, W - 24, 24, 4)
            love.graphics.setColor(node_color[1], node_color[2], node_color[3], 0.6 * st)
            love.graphics.rectangle("line", 12, sy, W - 24, 24, 4)
            love.graphics.setFont(status_font)
            love.graphics.setColor(th.text[1], th.text[2], th.text[3], 0.92 * st)
            love.graphics.print("> " .. status_msg, 20, sy + 6)
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
                right_text = string.format("%d/%d  v10.5.1", selected, #live),
            })
        end

        if th.scanlines then effects.scanlines(W, H, 0.06) end
        if th.vignette  then effects.vignette(W, H, 0.35) end
        love.graphics.setColor(1, 1, 1, 1)
    end

    function scene.save_state()
        return {
            selected = selected,
            scroll_offset = scroll_offset,
        }
    end

    function scene.restore_state(state)
        if not state then return end
        if state.selected then selected = state.selected end
        if state.scroll_offset then scroll_offset = state.scroll_offset end
        ensure_visible()
    end

    return scene
end

return M
