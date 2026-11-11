local sm = require("core.scene_manager")
local bridge = require("core.bridge")
local input = require("core.input")
local theme = require("theme.loader")
local chrome = require("core.chrome")
local font = require("core.font")
local nodes = require("core.nodes")
local effects = require("core.effects")

local scene = {}
local filters = {
    {label = "ALL", args = {}},
    {label = "ITALY", args = {country = "Italy"}},
    {label = "ROCK", args = {tag = "rock"}},
    {label = "JAZZ", args = {tag = "jazz"}},
    {label = "NEWS", args = {tag = "news"}},
    {label = "CLASSIC", args = {tag = "classical"}},
    {label = "FAVS", favorites = true},
}
local keyboard = {"QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM", " 0123456789"}
local filter_index, entries, selected = 1, {}, 1
local query, status, now_playing, icy_title = "", "Connecting to Radio Browser...", "", ""
local keyboard_mode, key_row, key_col = false, 1, 1
local busy, poll_timer = false, 0
local favorite_ids = {}
local accent = nodes.color_for(2)

local function is_favorite(id)
    return favorite_ids[id] == true
end

local function load_favorites()
    bridge.call("radio_favorites", {}, function(resp)
        if resp.ok then
            favorite_ids = {}
            for _, station in ipairs(resp.stations or {}) do
                favorite_ids[station.stationuuid] = true
            end
        end
    end)
end

local function load_stations()
    if busy then return end
    busy = true
    status = "Querying station catalogue..."
    local filter = filters[filter_index]
    if filter.favorites then
        bridge.call("radio_favorites", {}, function(resp)
            busy = false
            if resp.ok then
                entries = resp.stations or {}
                selected = math.min(selected, math.max(1, #entries))
                status = string.format("%d favourite stations", #entries)
            else
                status = "Favourites: " .. (resp.error or "unavailable")
            end
        end)
        return
    end
    local args = {}
    for k, v in pairs(filter.args) do args[k] = v end
    if query ~= "" then args.name = query end
    args.limit = 40
    bridge.call("radio_search", args, function(resp)
        busy = false
        if resp.ok then
            entries = resp.stations or {}
            selected = math.min(selected, math.max(1, #entries))
            status = string.format("%d stations // Radio Browser", #entries)
        else
            status = "Catalogue error: " .. (resp.error or "offline")
        end
    end)
end

local function play_selected()
    local station = entries[selected]
    if not station then return end
    status = "Opening stream: " .. station.name
    bridge.call("radio_play", {stationuuid = station.stationuuid}, function(resp)
        if resp.ok then
            now_playing = resp.playing or station.name
            status = "STREAM ONLINE // " .. now_playing
        else
            status = "STREAM ERROR // " .. (resp.error or "unknown")
        end
    end)
end

local function toggle_favorite()
    local station = entries[selected]
    if not station then return end
    bridge.call("radio_favorite_toggle", {stationuuid = station.stationuuid},
        function(resp)
            if resp.ok then
                favorite_ids[station.stationuuid] = resp.favorite or nil
                status = resp.favorite and "Added to favourites" or "Removed from favourites"
                if filters[filter_index].favorites then load_stations() end
            else
                status = "Favourite error: " .. (resp.error or "unknown")
            end
        end)
end

local function radio_action(action)
    bridge.call("radio_action", {action = action}, function(resp)
        if resp.ok then
            if action == "stop" then
                now_playing, icy_title = "", ""
                status = "Stream stopped"
            elseif action == "toggle_pause" then
                status = resp.pause and "Stream paused" or "Stream resumed"
            end
        else
            status = resp.error or "Radio control failed"
        end
    end)
end

local function poll_status()
    bridge.call("radio_status", {}, function(resp)
        if resp.ok and resp.status then
            local s = resp.status
            if not s.running then
                now_playing = ""
                icy_title = ""
            else
                icy_title = s.icy_title or s.icy_name or ""
            end
        end
    end)
end

local function cycle_filter(delta)
    filter_index = ((filter_index - 1 + delta) % #filters) + 1
    selected = 1
    load_stations()
end

local function append_key()
    local row = keyboard[key_row]
    local ch = row:sub(key_col, key_col)
    if ch and ch ~= "" then query = query .. ch end
end

function scene.enter()
    input.clear()
    entries, selected, query = {}, 1, ""
    filter_index, keyboard_mode = 1, false
    status, now_playing, icy_title = "Connecting to Radio Browser...", "", ""
    load_favorites()
    load_stations()
    input.on("press", function(action)
        if keyboard_mode then
            if action == "up" then
                key_row = math.max(1, key_row - 1)
                key_col = math.min(key_col, #keyboard[key_row])
            elseif action == "down" then
                key_row = math.min(#keyboard, key_row + 1)
                key_col = math.min(key_col, #keyboard[key_row])
            elseif action == "left" then
                key_col = math.max(1, key_col - 1)
            elseif action == "right" then
                key_col = math.min(#keyboard[key_row], key_col + 1)
            elseif action == "a" then
                append_key()
            elseif action == "x" then
                query = query:sub(1, -2)
            elseif action == "r1" then
                keyboard_mode = false
                selected = 1
                load_stations()
            elseif action == "b" or action == "y" then
                keyboard_mode = false
            end
            return
        end
        if action == "up" then
            selected = math.max(1, selected - 1)
        elseif action == "down" then
            selected = math.min(#entries, selected + 1)
        elseif action == "left" or action == "l1" then
            cycle_filter(-1)
        elseif action == "right" or action == "r1" then
            if action == "r1" then load_stations() else cycle_filter(1) end
        elseif action == "a" then
            play_selected()
        elseif action == "x" then
            toggle_favorite()
        elseif action == "y" then
            keyboard_mode = true
            key_row, key_col = 1, 1
        elseif action == "select" then
            radio_action("toggle_pause")
        elseif action == "start" then
            radio_action("stop")
        elseif action == "b" or action == "menu" then
            sm.back()
        end
    end)
end

function scene.update(dt)
    poll_timer = poll_timer + dt
    if poll_timer >= 5 then
        poll_timer = 0
        poll_status()
    end
end

function scene.draw()
    local W, H = love.graphics.getDimensions()
    local th = theme.get()
    love.graphics.clear(0.015, 0.02, 0.03, 1)
    love.graphics.setFont(font.regular(12) or love.graphics.newFont(12))
    love.graphics.setColor(th.text[1], th.text[2], th.text[3], 0.95)
    love.graphics.print("FILTER", 16, 72)
    local x = 72
    for i, filter in ipairs(filters) do
        local label = filter.label
        local width = love.graphics.getFont():getWidth(label) + 14
        if i == filter_index then
            love.graphics.setColor(accent[1], accent[2], accent[3], 0.2)
            love.graphics.rectangle("fill", x - 5, 68, width, 22, 3)
            love.graphics.setColor(accent[1], accent[2], accent[3], 1)
        else
            love.graphics.setColor(0.58, 0.63, 0.69, 0.9)
        end
        love.graphics.print(label, x + 2, 72)
        x = x + width + 3
    end

    love.graphics.setColor(0.55, 0.62, 0.68, 0.9)
    love.graphics.print("SEARCH: " .. (query ~= "" and query or "[Y] open keyboard"), 16, 96)
    local top, row_h = 124, 29
    local visible = 8
    local first = math.max(1, math.min(selected - 4, math.max(1, #entries - visible + 1)))
    for i = 1, visible do
        local idx = first + i - 1
        local station = entries[idx]
        if not station then break end
        local y = top + (i - 1) * row_h
        if idx == selected then
            love.graphics.setColor(accent[1], accent[2], accent[3], 0.18)
            love.graphics.rectangle("fill", 12, y, W - 24, row_h - 1, 3)
            love.graphics.setColor(accent[1], accent[2], accent[3], 0.9)
            love.graphics.rectangle("line", 12, y, W - 24, row_h - 1, 3)
        end
        love.graphics.setFont(font.regular(12) or love.graphics.newFont(12))
        love.graphics.setColor(0.9, 0.92, 0.95, 0.95)
        local mark = is_favorite(station.stationuuid) and "* " or "  "
        local label = mark .. station.name
        local detail = station.country or station.codec or ""
        if #label > 55 then label = label:sub(1, 52) .. "..." end
        love.graphics.print(label, 20, y + 2)
        love.graphics.setColor(0.52, 0.59, 0.66, 0.9)
        love.graphics.printf(detail, W - 145, y + 3, 125, "right")
    end

    love.graphics.setColor(th.panel_bg[1], th.panel_bg[2], th.panel_bg[3], 0.96)
    love.graphics.rectangle("fill", 12, 366, W - 24, 48, 4)
    love.graphics.setColor(accent[1], accent[2], accent[3], 0.65)
    love.graphics.rectangle("line", 12, 366, W - 24, 48, 4)
    love.graphics.setFont(font.regular(11) or love.graphics.newFont(11))
    love.graphics.setColor(th.text[1], th.text[2], th.text[3], 0.95)
    love.graphics.print("> " .. status:sub(1, 88), 20, 373)
    love.graphics.setColor(0.62, 0.72, 0.78, 0.9)
    love.graphics.print("ICY: " .. (icy_title ~= "" and icy_title or now_playing), 20, 393)

    if keyboard_mode then
        love.graphics.setColor(0.01, 0.015, 0.025, 0.98)
        love.graphics.rectangle("fill", 8, 300, W - 16, 150, 5)
        love.graphics.setColor(accent[1], accent[2], accent[3], 0.9)
        love.graphics.rectangle("line", 8, 300, W - 16, 150, 5)
        love.graphics.setFont(font.regular(15) or love.graphics.newFont(15))
        love.graphics.setColor(th.text[1], th.text[2], th.text[3], 1)
        love.graphics.print("QUERY: " .. query .. "_", 20, 309)
        for r, row in ipairs(keyboard) do
            local y = 336 + (r - 1) * 25
            local char_w = math.min(40, (W - 48) / #row)
            local start_x = (W - char_w * #row) / 2
            for col = 1, #row do
                local xx = start_x + (col - 1) * char_w
                if r == key_row and col == key_col then
                    love.graphics.setColor(accent[1], accent[2], accent[3], 0.28)
                    love.graphics.rectangle("fill", xx, y, char_w - 2, 22, 2)
                end
                love.graphics.setColor(th.text[1], th.text[2], th.text[3], 1)
                local key_label = (r == 4 and col == 1) and "SPC" or row:sub(col, col)
                love.graphics.printf(key_label, xx, y + 3, char_w - 2, "center")
            end
        end
        love.graphics.setFont(font.regular(10) or love.graphics.newFont(10))
        love.graphics.setColor(0.62, 0.72, 0.78, 0.9)
        love.graphics.print("A add   X delete   R1 search   B close", 20, 437)
    end

    chrome.draw_header({theme = th, title = "Void-DESK", subtitle = "VOID RADIO",
                        status_icons = {"wifi", "battery"}})
    chrome.draw_footer({theme = th, hints = {
        {icon = "dpad", label = "Navigate"},
        {icon = "btn_a", label = "Play"},
        {icon = "btn_b", label = "Back"},
    }, right_text = "X fav  SELECT pause  START stop"})
    if th.scanlines then effects.scanlines(W, H, 0.05) end
    if th.vignette then effects.vignette(W, H, 0.3) end
    love.graphics.setColor(1, 1, 1, 1)
end

return scene
