local sm = require("core.scene_manager")
local theme = require("theme.loader")
local input = require("core.input")
local chrome = require("core.chrome")
local effects = require("core.effects")
local font = require("core.font")
local nodes = require("core.nodes")
local bridge = require("core.bridge")

local scene = {}
local tabs = {"all", "italia", "tekno", "preferiti", "recenti"}
local tab_labels = {all="ALL", italia="ITALY", tekno="TEKNO", preferiti="FAVOURITES", recenti="RECENT"}
local tab_index = 1
local stations = {}
local selected = 1
local first_visible = 1
local loading = false
local message = "Loading curated stations..."
local playing = nil
local player_status = {}
local poll_t = 0
local enter_t = 0
local node_color = nodes.color_for(2)

local function current_tab() return tabs[tab_index] end

local function load_stations()
    loading = true
    message = "Loading " .. (tab_labels[current_tab()] or "ALL") .. " stations..."
    bridge.call("radio_list", {tab = current_tab()}, function(resp)
        loading = false
        if resp.ok then
            stations = resp.stations or {}
            selected = math.max(1, math.min(selected, math.max(1, #stations)))
            first_visible = math.min(first_visible, math.max(1, #stations))
            message = string.format("%d stations", resp.count or #stations)
        else
            stations = {}
            message = "Catalog unavailable: " .. (resp.error or "unknown error")
        end
    end)
end

local function change_tab(delta)
    tab_index = ((tab_index - 1 + delta) % #tabs) + 1
    selected = 1
    first_visible = 1
    load_stations()
end

local function refresh_status(silent)
    bridge.call("radio_status", {}, function(resp)
        if resp.ok then
            player_status = resp
            playing = resp.current
            if not silent and resp.playing then
                message = "Playing: " .. ((resp.current and resp.current.name) or "Radio")
            elseif not silent and not resp.playing then
                message = "Player idle"
            end
        elseif not silent then
            message = resp.error or "Player status unavailable"
        end
    end)
end

local function play_selected()
    local station = stations[selected]
    if not station then message = "Select a station first"; return end
    message = "Connecting to " .. station.name .. "..."
    bridge.call("radio_play", {station_id = station.id}, function(resp)
        if resp.ok then
            message = "Playing: " .. (resp.name or station.name)
            refresh_status(true)
        else
            message = "Playback failed: " .. (resp.error or "unknown error")
        end
    end)
end

local function toggle_favorite()
    local station = stations[selected]
    if not station then return end
    bridge.call("radio_toggle_favorite", {station_id = station.id}, function(resp)
        if resp.ok then
            message = resp.favorite and ("★ Added: " .. station.name)
                or ("☆ Removed: " .. station.name)
            station.favorite = resp.favorite
            if current_tab() == "preferiti" and not resp.favorite then
                load_stations()
            end
        else
            message = "Favourite update failed: " .. (resp.error or "?")
        end
    end)
end

local function stop_playback()
    bridge.call("radio_stop", {}, function(resp)
        if resp.ok then
            playing = nil
            player_status = {}
            message = "Radio stopped"
        else
            message = "Stop failed: " .. (resp.error or "?")
        end
    end)
end

function scene.enter(args)
    enter_t = 0
    poll_t = 0
    tab_index = 1
    selected = 1
    first_visible = 1
    stations = {}
    message = "Ready"
    input.clear()
    load_stations()
    refresh_status(true)
    input.on("press", function(action)
        if action == "up" then
            selected = math.max(1, selected - 1)
        elseif action == "down" then
            selected = math.min(#stations, selected + 1)
        elseif action == "left" or action == "l1" then
            change_tab(-1)
        elseif action == "right" or action == "r1" then
            change_tab(1)
        elseif action == "a" then
            play_selected()
        elseif action == "y" then
            toggle_favorite()
        elseif action == "x" then
            stop_playback()
        elseif action == "select" then
            load_stations()
            refresh_status(true)
        elseif action == "b" or action == "menu" then
            sm.back()
        end
    end)
end

function scene.update(dt)
    enter_t = math.min(1, enter_t + dt / 0.55)
    poll_t = poll_t + dt
    if poll_t >= 3 then
        poll_t = 0
        refresh_status(true)
    end
    local visible = math.max(1, math.floor((love.graphics.getHeight() - 220) / 34))
    if selected < first_visible then first_visible = selected end
    if selected > first_visible + visible - 1 then
        first_visible = selected - visible + 1
    end
end

function scene.draw()
    local W, H = love.graphics.getDimensions()
    local th = theme.get()
    local a = math.min(1, enter_t * 2.5)
    love.graphics.clear(0, 0, 0, 1)

    love.graphics.setColor(0.035, 0.055, 0.055, 0.96 * a)
    love.graphics.rectangle("fill", 10, 60, W - 20, H - 112, 6)
    love.graphics.setColor(node_color[1], node_color[2], node_color[3], 0.35 * a)
    love.graphics.rectangle("line", 10, 60, W - 20, H - 112, 6)

    local f = font.regular(11) or love.graphics.newFont(11)
    love.graphics.setFont(f)
    local tab_w = (W - 36) / #tabs
    for i, tab in ipairs(tabs) do
        local x = 14 + (i - 1) * tab_w
        local active = i == tab_index
        love.graphics.setColor(active and node_color[1] or 0.13,
            active and node_color[2] or 0.16, active and node_color[3] or 0.17,
            active and 0.22 * a or 0.75 * a)
        love.graphics.rectangle("fill", x, 68, tab_w - 3, 22, 4)
        love.graphics.setColor(active and node_color[1] or 0.55,
            active and node_color[2] or 0.60, active and node_color[3] or 0.62, a)
        love.graphics.printf(tab_labels[tab] or tab, x, 74, tab_w - 3, "center")
    end

    local top = 102
    local row_h = 34
    local visible = math.max(1, math.floor((H - 220) / row_h))
    for i = 1, visible do
        local idx = first_visible + i - 1
        local station = stations[idx]
        if not station then break end
        local y = top + (i - 1) * row_h
        local active = playing and playing.kind == "radio" and playing.id == station.id
        if idx == selected then
            love.graphics.setColor(node_color[1], node_color[2], node_color[3], 0.16 * a)
            love.graphics.rectangle("fill", 16, y, W - 32, row_h - 2, 4)
            love.graphics.setColor(node_color[1], node_color[2], node_color[3], a)
            love.graphics.rectangle("line", 16, y, W - 32, row_h - 2, 4)
        end
        love.graphics.setColor(active and node_color[1] or th.text[1],
            active and node_color[2] or th.text[2], active and node_color[3] or th.text[3], a)
        love.graphics.print(station.name or "Unknown station", 26, y + 4)
        love.graphics.setColor(0.55, 0.61, 0.66, 0.9 * a)
        love.graphics.print((station.country or "--") .. "  " .. (station.tags or ""), 26, y + 19)
        if station.favorite then
            love.graphics.setColor(1, 0.82, 0.28, a)
            love.graphics.print("★", W - 34, y + 8)
        end
        if active then
            love.graphics.setColor(node_color[1], node_color[2], node_color[3], a)
            love.graphics.print("LIVE", W - 78, y + 8)
        end
    end

    if #stations == 0 then
        love.graphics.setColor(0.62, 0.67, 0.72, a)
        love.graphics.printf(loading and "Loading station catalogue..." or "No stations in this list",
            20, 210, W - 40, "center")
    end

    local status_y = H - chrome.FOOTER_H - 28
    love.graphics.setColor(0.05, 0.08, 0.08, 0.95)
    love.graphics.rectangle("fill", 12, status_y, W - 24, 22, 4)
    love.graphics.setColor(node_color[1], node_color[2], node_color[3], 0.55)
    love.graphics.rectangle("line", 12, status_y, W - 24, 22, 4)
    love.graphics.setFont(font.regular(10) or love.graphics.newFont(10))
    love.graphics.setColor(th.text[1], th.text[2], th.text[3], 1)
    local detail = player_status.icy_title and player_status.icy_title ~= ""
        and player_status.icy_title or message
    love.graphics.print("> " .. tostring(detail):sub(1, 76), 20, status_y + 6)

    chrome.draw_header({theme = th, title = "Void-DESK", subtitle = "VOID RADIO",
        status_icons = {"wifi", "battery"}})
    chrome.draw_footer({theme = th, hints = {
        {icon = "dpad", label = "Navigate"},
        {icon = "btn_a", label = "Play"},
        {icon = "btn_y", label = "Favourite"},
        {icon = "btn_x", label = "Stop"},
        {icon = "btn_b", label = "Back"},
    }, right_text = "L1/R1 tabs"})
    if th.scanlines then effects.scanlines(W, H, 0.05) end
    if th.vignette then effects.vignette(W, H, 0.3) end
    love.graphics.setColor(1, 1, 1, 1)
end

return scene
