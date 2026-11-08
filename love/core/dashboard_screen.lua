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
local layout  = require("core.layout")

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

    local widgets_draw = config.widgets_draw
    local on_enter = config.on_enter
    local on_update = config.on_update
    scene._data = {}

    local function get_live_items()
        if scene._get_items then
            local ok, res = pcall(scene._get_items)
            if ok and type(res) == "table" then return res end
        end
        return items
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
            elseif action == "down" then
                selected = math.min(#live, selected + 1)
            elseif action == "a" then
                local item = live[selected]
                if item and item.action then
                    local msg = item.action(scene)
                    if msg then status_msg = msg end
                end
            elseif action == "b" then
                sm.back()
            elseif action == "select" then
                jobs.toggle_overlay()
            end
        end)
    end

    function scene.save_state()
        return { selected = selected, scroll_offset = scroll_offset }
    end

    function scene.restore_state(state)
        if not state then return end
        selected = state.selected or 1
        scroll_offset = state.scroll_offset or 0
    end

    function scene.update(dt)
        if t_enter < 1 then t_enter = math.min(1, t_enter + dt / 0.5) end
        if on_update then on_update(scene, dt) end
    end

    function scene.set_status(msg) status_msg = msg end
    function scene.set_data(k, v) scene._data[k] = v end
    function scene.get_data(k) return scene._data[k] end

    function scene.draw()
        local L = layout
        local W, H = love.graphics.getWidth(), love.graphics.getHeight()
        local th = theme.get()

        love.graphics.clear(0, 0, 0, 1)

        -- Background animation (config.background_draw overrides bg_anim)
        local bg_a = math.min(1, t_enter * 2.5)
        if bg_a > 0.02 then
            if config.background_draw then
                config.background_draw(W, H, love.timer.getTime(), node_color, bg_a)
            else
                bg_anim.draw(bg_kind, W, H, love.timer.getTime(), node_color, bg_a * 0.55)
            end
        end

        -- Chrome header FIRST (so it doesn't cover widget cards)
        if t_enter > 0.05 then
            chrome.draw_header({
                theme = th, title = "Void-DESK", subtitle = title,
                status_icons = { "wifi", "battery" },
            })
        end

        -- Widget panel
        local w_t = math.max(0, math.min(1, (t_enter - 0.10) / 0.40))
        local has_widgets = widgets_draw ~= nil
        local widget_h = has_widgets and (config.widget_height or L.widget_h) or 0
        if w_t > 0.02 and has_widgets then
            widgets_draw(scene, w_t)
        end

        -- Menu geometry
        local menu_top = L.header_h + widget_h + math.floor(10 * L.scale)
        local running = jobs.total_running()
        local strip_h = running > 0 and L.strip_h or 0
        local menu_bottom = H - L.footer_h - L.status_h - strip_h - math.floor(8 * L.scale)
        local visible_rows = math.max(1, math.floor((menu_bottom - menu_top) / L.row_h))

        local live = get_live_items()

        -- Ensure selection is visible
        if selected < scroll_offset + 1 then
            scroll_offset = selected - 1
        elseif selected > scroll_offset + visible_rows then
            scroll_offset = selected - visible_rows
        end
        scroll_offset = math.max(0, math.min(scroll_offset, math.max(0, #live - visible_rows)))

        -- Menu items with scissor
        love.graphics.setScissor(0, menu_top - 2, W, menu_bottom - menu_top + 4)
        for i = 1, visible_rows do
            local idx = scroll_offset + i
            if idx > #live then break end
            local item = live[idx]
            local delay = 0.25 + (i - 1) * 0.03
            local it = math.max(0, math.min(1, (t_enter - delay) / 0.2))
            if it > 0.01 then
                local y = menu_top + (i - 1) * L.row_h + (1 - it) * math.floor(10 * L.scale)
                widgets.menu_row(16, y, W - 32, L.row_h - 2, {
                    icon = item.icon, badge = item.badge,
                    label = item.label or "", desc = item.desc,
                    value = item.value, value_color = item.value_color,
                    chevron = item.chevron ~= false and not item.value,
                    selected = (idx == selected), theme = th,
                    node_color = node_color, alpha = it,
                })
            end
        end
        love.graphics.setScissor()

        -- Item spinners for jobs
        for i = 1, visible_rows do
            local idx = scroll_offset + i
            if idx > #live then break end
            local item = live[idx]
            if item.label then
                local n_active = jobs.count_for_name(item.label)
                if n_active > 0 then
                    local y = menu_top + (i - 1) * L.row_h
                    local sx = W - math.floor(42 * L.scale)
                    local sy = y + L.row_h / 2
                    local t_now = love.timer.getTime()
                    local c = item.job_color or node_color
                    local rad = math.floor(6 * L.scale)
                    for k = 0, 5 do
                        local ang = t_now * 4 + k * math.pi / 3
                        local a = 0.3 + 0.7 * (1 - k / 6)
                        love.graphics.setColor(c[1], c[2], c[3], a)
                        love.graphics.circle("fill",
                            sx + math.cos(ang) * rad,
                            sy + math.sin(ang) * rad, math.max(1, rad/4))
                    end
                end
            end
        end

        -- Scroll indicators
        if scroll_offset > 0 then
            pcall(icon.draw, "arrow_up", W - math.floor(26 * L.scale),
                  menu_top - math.floor(4 * L.scale),
                  math.floor(16 * L.scale), node_color, { alpha = 0.6 })
        end
        if scroll_offset + visible_rows < #live then
            pcall(icon.draw, "arrow_down", W - math.floor(26 * L.scale),
                  menu_bottom - math.floor(14 * L.scale),
                  math.floor(16 * L.scale), node_color, { alpha = 0.6 })
        end

        -- Status strip (if jobs active)
        if running > 0 then
            local strip_y = H - L.footer_h - L.status_h - L.strip_h
            love.graphics.setColor(0.04, 0.06, 0.10, 0.95)
            love.graphics.rectangle("fill", 0, strip_y, W, L.strip_h)
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
                local f_st = font.regular(L.font_status) or love.graphics.newFont(L.font_status)
                local cy = strip_y + math.floor((L.strip_h - f_st:getHeight()) / 2)
                love.graphics.setColor(c[1], c[2], c[3], 1)
                love.graphics.circle("fill", math.floor(14 * L.scale),
                                    strip_y + L.strip_h / 2, math.floor(4 * L.scale))
                love.graphics.setFont(f_st)
                love.graphics.setColor(0.85, 0.88, 0.92, 1)
                love.graphics.print(string.format("[%d] %s  %d%%",
                    running, first.name, first.progress or 0), math.floor(24 * L.scale), cy)
                -- Inline bar
                local bw = math.floor(100 * L.scale)
                local bx = W - bw - math.floor(120 * L.scale)
                local bh = math.floor(6 * L.scale)
                local by = strip_y + math.floor((L.strip_h - bh)/2)
                love.graphics.setColor(0.10, 0.12, 0.16, 1)
                love.graphics.rectangle("fill", bx, by, bw, bh, 2)
                local fw = bw * (first.progress or 0) / 100
                if fw > 1 then
                    love.graphics.setColor(c[1], c[2], c[3], 1)
                    love.graphics.rectangle("fill", bx, by, fw, bh, 2)
                end
                love.graphics.setColor(0.55, 0.6, 0.65, 1)
                love.graphics.print("SELECT: details",
                    W - math.floor(110 * L.scale), cy)
            end
        end

        -- Status panel
        local st = math.max(0, math.min(1, (t_enter - 0.55) / 0.30))
        if st > 0.01 then
            local sy = H - L.footer_h - L.status_h - math.floor(4 * L.scale)
            love.graphics.setColor(th.panel_bg[1], th.panel_bg[2], th.panel_bg[3], 0.92 * st)
            love.graphics.rectangle("fill", 12, sy, W - 24, L.status_h, 4)
            love.graphics.setColor(node_color[1], node_color[2], node_color[3], 0.6 * st)
            love.graphics.rectangle("line", 12, sy, W - 24, L.status_h, 4)
            local fs = font.regular(L.font_status) or love.graphics.newFont(L.font_status)
            love.graphics.setFont(fs)
            love.graphics.setColor(th.text[1], th.text[2], th.text[3], 0.92 * st)
            local ty = sy + math.floor((L.status_h - fs:getHeight())/2)
            love.graphics.print("> " .. status_msg, math.floor(20 * L.scale), ty)
        end

        -- Chrome
        if t_enter > 0.20 then
            chrome.draw_footer({
                theme = th,
                hints = {
                    { icon = "dpad",  label = "Navigate" },
                    { icon = "btn_a", label = "Run" },
                    { icon = "btn_b", label = "Back" },
                },
                right_text = string.format("%d/%d", selected, #live),
            })
        end

        if th.scanlines then effects.scanlines(W, H, 0.06) end
        if th.vignette  then effects.vignette(W, H, 0.35) end
        love.graphics.setColor(1, 1, 1, 1)
    end

    return scene
end

return M
