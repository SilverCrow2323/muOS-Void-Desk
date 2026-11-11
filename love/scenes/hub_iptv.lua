local sm      = require("core.scene_manager")
local theme   = require("theme.loader")
local input   = require("core.input")
local chrome  = require("core.chrome")
local effects = require("core.effects")
local font    = require("core.font")
local nodes   = require("core.nodes")
local anim    = require("core.anim")
local widgets = require("core.widgets")
local iptv    = require("core.iptv")

local scene = {}
local t_enter = 0
local node_color = nodes.color_for(2)   -- MEDIA VAULT color
local status_msg = "Loading..."; scene.set_status = function(m) status_msg = m end

local menu_top = chrome.HEADER_H + 92
local menu_bottom = 480 - chrome.FOOTER_H - 36
local row_h = 30
local first_visible = 1
local current_programme = nil
local next_programme = nil

local function refresh_epg_for_selection()
    local channel = iptv.current_channel()
    if not channel then
        current_programme, next_programme = nil, nil
        return
    end
    iptv.epg_for(channel, function(now, nxt)
        current_programme, next_programme = now, nxt
    end)
end

local function ensure_loaded()
    if iptv.state.loaded or iptv.state.loading then return end
    status_msg = "Loading playlist..."
    iptv.get_default_playlist(function(url, cfg)
        iptv.load_playlist(url, function(ok, resp)
            if ok then
                status_msg = string.format("%d channels loaded", resp.count or 0)
                -- then try to load EPG
                local urls = iptv.select_epg_urls(
                    cfg and cfg.epg_urls, resp and resp.epg_urls)
                if #urls > 0 then
                    status_msg = "Loading EPG..."
                    iptv.load_epg(urls, function(r)
                        if r.ok then
                            status_msg = string.format("EPG: %d channels", r.channels_with_epg or 0)
                            refresh_epg_for_selection()
                        else
                            status_msg = "EPG: " .. (r.error or "no data")
                        end
                    end)
                end
            else
                status_msg = "Error: " .. (resp.error or "load failed")
            end
        end)
    end)
end

local function play_selected()
    local ch = iptv.current_channel()
    if not ch then return "No channel selected" end
    status_msg = "Launching: " .. ch.name
    iptv.play(ch, function(resp)
        if resp.ok then
            status_msg = "Playing: " .. ch.name
            if resp.handoff then love.event.quit() end
        else
            status_msg = "Failed: " .. (resp.error or "unknown")
        end
    end)
    return "Playing " .. ch.name
end

function scene.enter(args)
    t_enter = 0
    status_msg = "Ready"
    input.clear()
    ensure_loaded()
    input.on("press", function(action)
        if action == "up" then
            iptv.move_selection(-1); refresh_epg_for_selection()
        elseif action == "down" then
            iptv.move_selection(1); refresh_epg_for_selection()
        elseif action == "left" then
            iptv.move_selection(-10); refresh_epg_for_selection()
        elseif action == "right" then
            iptv.move_selection(10); refresh_epg_for_selection()
        elseif action == "l1" then
            iptv.next_group(-1); refresh_epg_for_selection()
        elseif action == "r1" then
            iptv.next_group(1); refresh_epg_for_selection()
        elseif action == "a" then
            play_selected()
        elseif action == "y" then
            local ch = iptv.current_channel()
            if ch then
                local fav = iptv.toggle_favorite(ch.url)
                status_msg = (fav and "★ Added: " or "☆ Removed: ") .. ch.name
            end
        elseif action == "b" or action == "menu" then
            sm.switch("nexus", {})
        end
    end)
end

function scene.update(dt)
    if t_enter < 1 then t_enter = math.min(1, t_enter + dt / 0.55) end
    -- scroll selected into view
    local visible_rows = math.max(1, math.floor((menu_bottom - menu_top) / row_h))
    if iptv.state.selected > 0 then
        if iptv.state.selected < first_visible then
            first_visible = iptv.state.selected
        elseif iptv.state.selected > first_visible + visible_rows - 1 then
            first_visible = iptv.state.selected - visible_rows + 1
        end
    end
end

function scene.draw()
    local W, H = love.graphics.getDimensions()
    local th = theme.get()
    love.graphics.clear(0, 0, 0, 1)

    -- subtle animated background
    local bg_a = math.min(1, t_enter * 2.5)
    for i = 0, 10 do
        local tt = i / 10
        love.graphics.setColor(node_color[1], node_color[2], node_color[3],
                               0.03 * (1 - tt) * bg_a)
        love.graphics.rectangle("fill", 0, chrome.HEADER_H + i * 32, W, 32)
    end

    local st = iptv.state
    local cy, ch_h = chrome.HEADER_H + 8, 76

    -- Status card (top)
    if st.loaded then
        widgets.status_card(12, cy, (W - 40) / 2, ch_h, "video",
            "Channels", string.format("%d total", #st.channels),
            (st.loaded and {0.4, 0.9, 0.5} or {0.55, 0.58, 0.62}), "OK", bg_a)
        widgets.status_card(12 + (W - 40)/2 + 8, cy, (W - 40) / 2, ch_h, "doc",
            "EPG", st.epg_loaded and "loaded" or (st.epg_loading and "loading..." or "none"),
            (st.epg_loaded and {0.4, 0.9, 0.5} or {0.55, 0.58, 0.62}),
            st.epg_loaded and "OK" or "—", bg_a)
    else
        widgets.status_card(12, cy, W - 24, ch_h, "video",
            "Loading playlist", status_msg,
            {0.85, 0.75, 0.30}, "WAIT", bg_a)
    end

    -- Group filter bar
    local gy = cy + ch_h + 4
    love.graphics.setColor(0.05, 0.06, 0.08, 0.92 * bg_a)
    love.graphics.rectangle("fill", 12, gy, W - 24, 20, 4)
    love.graphics.setColor(node_color[1], node_color[2], node_color[3], 0.5 * bg_a)
    love.graphics.setLineWidth(1)
    love.graphics.rectangle("line", 12, gy, W - 24, 20, 4)
    local f_grp = font.regular(11) or love.graphics.newFont(11)
    love.graphics.setFont(f_grp)
    love.graphics.setColor(0.75, 0.80, 0.85, bg_a)
    local grp_label = st.group_filter == "*" and "ALL GROUPS"
        or (st.group_filter or "?")
    love.graphics.print("L1/R1: " .. grp_label, 20, gy + 4)
    local right_txt = string.format("%d/%d", st.selected, #st.filtered)
    local rw = f_grp:getWidth(right_txt)
    love.graphics.setColor(node_color[1], node_color[2], node_color[3], bg_a)
    love.graphics.print(right_txt, W - rw - 20, gy + 4)

    -- Channel list
    if st.loaded and #st.filtered > 0 then
        local visible = math.max(1, math.floor((menu_bottom - menu_top) / row_h))
        for i = 1, visible do
            local idx = first_visible + i - 1
            if idx > #st.filtered then break end
            local ch = st.filtered[idx]
            local y = menu_top + (i - 1) * row_h
            local item_t = math.min(1, math.max(0, (t_enter - 0.3 - (i - 1) * 0.02) / 0.2))
            local is_sel = (idx == st.selected)
            local is_fav = iptv.is_favorite(ch.url)

            if is_sel then
                love.graphics.setColor(node_color[1], node_color[2], node_color[3],
                                       0.16 * item_t)
                love.graphics.rectangle("fill", 16, y, W - 32, row_h - 2, 4)
                love.graphics.setColor(node_color[1], node_color[2], node_color[3],
                                       item_t)
                love.graphics.setLineWidth(1.5)
                love.graphics.rectangle("line", 16, y, W - 32, row_h - 2, 4)
            end
            local f_ch = font.regular(13) or love.graphics.newFont(13)
            love.graphics.setFont(f_ch)
            love.graphics.setColor(0.92, 0.94, 0.96, item_t)
            local name = ch.name or "?"
            if #name > 34 then name = name:sub(1, 31) .. "..." end
            love.graphics.print(name, 26, y + 6)

            if is_fav then
                love.graphics.setColor(1, 0.85, 0.30, item_t)
                love.graphics.print("★", W - 32, y + 6)
            end
        end
        -- Scroll indicator
        if #st.filtered > 0 then
            local track_h = menu_bottom - menu_top
            local bar_h = math.max(12, track_h * math.min(1, (menu_bottom - menu_top) / (row_h * #st.filtered)))
            local frac = (first_visible - 1) / math.max(1, #st.filtered - (menu_bottom - menu_top) / row_h)
            local bar_y = menu_top + (track_h - bar_h) * math.max(0, math.min(1, frac))
            love.graphics.setColor(0.30, 0.35, 0.40, bg_a)
            love.graphics.rectangle("fill", W - 6, bar_y, 3, bar_h)
        end
    elseif st.loaded then
        love.graphics.setFont(font.regular(14) or love.graphics.newFont(14))
        love.graphics.setColor(0.55, 0.60, 0.66, bg_a)
        love.graphics.print("No channels in this group", W/2 - 90, 260)
    end

    -- Status panel
    local sy = H - chrome.FOOTER_H - 30
    love.graphics.setColor(th.panel_bg[1], th.panel_bg[2], th.panel_bg[3], 0.9)
    love.graphics.rectangle("fill", 12, sy, W - 24, 24, 4)
    love.graphics.setColor(node_color[1], node_color[2], node_color[3], 0.5)
    love.graphics.rectangle("line", 12, sy, W - 24, 24, 4)
    love.graphics.setFont(font.regular(11) or love.graphics.newFont(11))
    love.graphics.setColor(th.text[1], th.text[2], th.text[3], 0.9)
    local selected_epg = status_msg
    if current_programme and current_programme.title then
        selected_epg = "NOW: " .. tostring(current_programme.title)
        if next_programme and next_programme.title then
            selected_epg = selected_epg .. " | NEXT: " .. tostring(next_programme.title)
        end
    end
    if #selected_epg > 94 then selected_epg = selected_epg:sub(1, 91) .. "..." end
    love.graphics.print("> " .. selected_epg, 20, sy + 6)

    -- Chrome
    if t_enter > 0.2 then
        chrome.draw_header({
            theme = th, title = "Void-DESK", subtitle = "IPTV",
            status_icons = { "wifi", "battery" },
        })
        chrome.draw_footer({
            theme = th,
            hints = {
                { icon = "dpad",  label = "Navigate" },
                { icon = "btn_a", label = "Play" },
                { icon = "btn_y", label = "Fav" },
                { icon = "btn_b", label = "Back" },
            },
            right_text = "L1/R1 group",
        })
    end

    if th.scanlines then effects.scanlines(W, H, 0.06) end
    if th.vignette then effects.vignette(W, H, 0.35) end
    love.graphics.setColor(1, 1, 1, 1)
end

return scene
