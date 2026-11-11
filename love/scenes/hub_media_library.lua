local sm = require("core.scene_manager")
local theme = require("theme.loader")
local input = require("core.input")
local chrome = require("core.chrome")
local effects = require("core.effects")
local font = require("core.font")
local nodes = require("core.nodes")
local bridge = require("core.bridge")

local scene = {}
local roots = {}
local entries = {}
local path_stack = {}
local selected = 1
local first_visible = 1
local loading = false
local message = "Choose an SD card or Void Desk Data"
local playback = {}
local poll_t = 0
local enter_t = 0
local node_color = nodes.color_for(2)

local function load_roots()
    loading = true
    message = "Discovering media roots..."
    bridge.call("media_roots", {}, function(resp)
        loading = false
        if resp.ok then
            roots = resp.roots or {}
            entries = {}
            path_stack = {}
            for _, root in ipairs(roots) do
                table.insert(entries, {name = root.label, type = "dir", path = root.path, size = 0, root = true})
            end
            selected = 1
            first_visible = 1
            message = #roots .. " media roots available"
        else
            roots = {}
            entries = {}
            message = "Cannot discover media roots: " .. (resp.error or "unknown error")
        end
    end)
end

local function load_path(path, label)
    loading = true
    message = "Scanning folder..."
    bridge.call("media_list", {path = path}, function(resp)
        loading = false
        if resp.ok then
            entries = resp.entries or {}
            selected = 1
            first_visible = 1
            message = string.format("%d supported items", #entries)
            if label then path_stack[#path_stack].label = label end
        else
            message = "Folder unavailable: " .. (resp.error or "unknown error")
        end
    end)
end

local function enter_selected()
    local entry = entries[selected]
    if not entry then return end
    if entry.type == "dir" then
        table.insert(path_stack, {path = entry.path, label = entry.name})
        load_path(entry.path, entry.name)
    elseif entry.type == "audio" or entry.type == "video" then
        message = "Opening " .. entry.name .. "..."
        bridge.call("media_play_file", {path = entry.path}, function(resp)
            if resp.ok then
                message = (entry.type == "audio" and "Playing audio: " or "Playing video: ") .. entry.name
                playback.current = {name = entry.name, kind = entry.type}
            else
                message = "Playback failed: " .. (resp.error or "unknown error")
            end
        end)
    elseif entry.type == "playlist" then
        message = "M3U playlist: open IPTV to load a configured feed"
    end
end

local function go_back()
    if #path_stack > 0 then
        table.remove(path_stack)
        if #path_stack == 0 then
            load_roots()
        else
            local parent = path_stack[#path_stack]
            load_path(parent.path, parent.label)
        end
    else
        sm.back()
    end
end

local function stop_playback()
    bridge.call("media_stop", {}, function(resp)
        if resp.ok then
            playback.current = nil
            message = "Playback stopped"
        else
            message = "Stop failed: " .. (resp.error or "?")
        end
    end)
end

local function refresh_status()
    bridge.call("media_playback_status", {}, function(resp)
        if resp.ok then playback = resp
        else playback.error = resp.error end
    end)
end

function scene.enter(args)
    enter_t = 0
    poll_t = 0
    roots, entries, path_stack = {}, {}, {}
    selected = 1
    first_visible = 1
    playback = {}
    input.clear()
    load_roots()
    refresh_status()
    input.on("press", function(action)
        if action == "up" then
            selected = math.max(1, selected - 1)
        elseif action == "down" then
            selected = math.min(#entries, selected + 1)
        elseif action == "a" then
            enter_selected()
        elseif action == "x" then
            stop_playback()
        elseif action == "y" or action == "select" then
            if #path_stack > 0 then load_path(path_stack[#path_stack].path) else load_roots() end
            refresh_status()
        elseif action == "b" or action == "menu" then
            go_back()
        end
    end)
end

function scene.update(dt)
    enter_t = math.min(1, enter_t + dt / 0.55)
    poll_t = poll_t + dt
    if poll_t >= 3 then poll_t = 0; refresh_status() end
    local H = love.graphics.getHeight()
    local visible = math.max(1, math.floor((H - 200) / 33))
    if selected < first_visible then first_visible = selected end
    if selected > first_visible + visible - 1 then first_visible = selected - visible + 1 end
end

function scene.draw()
    local W, H = love.graphics.getDimensions()
    local th = theme.get()
    local a = math.min(1, enter_t * 2.5)
    love.graphics.clear(0, 0, 0, 1)

    love.graphics.setColor(0.035, 0.045, 0.065, 0.96 * a)
    love.graphics.rectangle("fill", 10, 60, W - 20, H - 112, 6)
    love.graphics.setColor(node_color[1], node_color[2], node_color[3], 0.35 * a)
    love.graphics.rectangle("line", 10, 60, W - 20, H - 112, 6)

    local title = #path_stack == 0 and "MEDIA ROOTS" or path_stack[#path_stack].label
    local f = font.regular(11) or love.graphics.newFont(11)
    love.graphics.setFont(f)
    love.graphics.setColor(node_color[1], node_color[2], node_color[3], a)
    love.graphics.print(title, 18, 69)
    local path_text = #path_stack > 0 and path_stack[#path_stack].path or "SD1  /  SD2  /  VOID DATA"
    love.graphics.setColor(0.55, 0.62, 0.68, a)
    love.graphics.printf(path_text, 18, 87, W - 36, "left")

    local top, row_h = 112, 33
    local visible = math.max(1, math.floor((H - 200) / row_h))
    for i = 1, visible do
        local idx = first_visible + i - 1
        local entry = entries[idx]
        if not entry then break end
        local y = top + (i - 1) * row_h
        if idx == selected then
            love.graphics.setColor(node_color[1], node_color[2], node_color[3], 0.16 * a)
            love.graphics.rectangle("fill", 16, y, W - 32, row_h - 2, 4)
            love.graphics.setColor(node_color[1], node_color[2], node_color[3], a)
            love.graphics.rectangle("line", 16, y, W - 32, row_h - 2, 4)
        end
        local kind = entry.type == "dir" and "DIR" or entry.type == "audio" and "AUD" or entry.type == "video" and "VID" or "M3U"
        love.graphics.setColor(entry.type == "dir" and node_color[1] or 0.68,
            entry.type == "dir" and node_color[2] or 0.75, entry.type == "dir" and node_color[3] or 0.82, a)
        love.graphics.print(kind, 24, y + 8)
        love.graphics.setColor(th.text[1], th.text[2], th.text[3], a)
        love.graphics.print(entry.name or "?", 66, y + 8)
        if entry.size and entry.size > 0 then
            local size = entry.size < 1048576 and string.format("%.0f KB", entry.size / 1024)
                or string.format("%.1f MB", entry.size / 1048576)
            love.graphics.setColor(0.55, 0.62, 0.68, a)
            love.graphics.printf(size, W - 106, y + 8, 80, "right")
        end
    end

    if #entries == 0 then
        love.graphics.setColor(0.62, 0.67, 0.72, a)
        love.graphics.printf(loading and "Scanning media..." or "No supported media files here", 20, 230, W - 40, "center")
    end

    local status_y = H - chrome.FOOTER_H - 28
    love.graphics.setColor(0.05, 0.06, 0.08, 0.95)
    love.graphics.rectangle("fill", 12, status_y, W - 24, 22, 4)
    love.graphics.setColor(node_color[1], node_color[2], node_color[3], 0.55)
    love.graphics.rectangle("line", 12, status_y, W - 24, 22, 4)
    love.graphics.setFont(font.regular(10) or love.graphics.newFont(10))
    love.graphics.setColor(th.text[1], th.text[2], th.text[3], 1)
    local detail = playback.current and (playback.current.name .. "  ·  " .. playback.current.kind) or message
    love.graphics.print("> " .. tostring(detail):sub(1, 76), 20, status_y + 6)

    chrome.draw_header({theme = th, title = "Void-DESK", subtitle = "MEDIA LIBRARY", status_icons = {"storage", "battery"}})
    chrome.draw_footer({theme = th, hints = {
        {icon = "dpad", label = "Navigate"},
        {icon = "btn_a", label = "Open / Play"},
        {icon = "btn_x", label = "Stop"},
        {icon = "btn_y", label = "Refresh"},
        {icon = "btn_b", label = "Back"},
    }})
    if th.scanlines then effects.scanlines(W, H, 0.05) end
    if th.vignette then effects.vignette(W, H, 0.28) end
    love.graphics.setColor(1, 1, 1, 1)
end

return scene