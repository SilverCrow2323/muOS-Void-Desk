local sm = require("core.scene_manager")
local bridge = require("core.bridge")
local input = require("core.input")
local theme = require("theme.loader")
local chrome = require("core.chrome")
local font = require("core.font")
local nodes = require("core.nodes")
local effects = require("core.effects")

local scene = {}
local entries, selected, first_visible = {}, 1, 1
local path, stack = "", {}
local status = "Scanning media roots..."
local playing = ""
local loading = false
local node_color = nodes.color_for(2)
local row_h, list_top, list_bottom = 28, 112, 414

local function load_directory(target)
    if loading then return end
    loading = true
    status = "Reading library..."
    bridge.call("media_list", {path = target or ""}, function(resp)
        loading = false
        if resp.ok then
            entries = resp.items or {}
            path = resp.path or ""
            selected, first_visible = 1, 1
            status = string.format("%d entries", #entries)
        else
            status = "Library error: " .. (resp.error or "unavailable")
        end
    end)
end

local function play_selected()
    local item = entries[selected]
    if not item or item.is_dir then return end
    status = "Starting " .. item.name
    bridge.call("media_play", {path = item.path}, function(resp)
        if resp.ok then
            playing = resp.playing or item.name
            status = "Playing: " .. playing
        else
            status = "Playback failed: " .. (resp.error or "unknown")
        end
    end)
end

local function enter_selected()
    local item = entries[selected]
    if not item then return end
    if item.is_dir then
        stack[#stack + 1] = path
        load_directory(item.path)
    else
        play_selected()
    end
end

local function go_back()
    if #stack > 0 then
        local parent = table.remove(stack)
        load_directory(parent)
    else
        sm.back()
    end
end

function scene.enter()
    input.clear()
    entries, selected, first_visible = {}, 1, 1
    path, stack, playing = "", {}, ""
    load_directory("")
    input.on("press", function(action)
        if action == "up" then
            selected = math.max(1, selected - 1)
        elseif action == "down" then
            selected = math.min(#entries, selected + 1)
        elseif action == "left" then
            selected = math.max(1, selected - 8)
        elseif action == "right" then
            selected = math.min(#entries, selected + 8)
        elseif action == "a" then
            enter_selected()
        elseif action == "x" then
            bridge.call("media_stop", {}, function(resp)
                if resp.ok then playing = ""; status = "Playback stopped" end
            end)
        elseif action == "b" or action == "menu" then
            go_back()
        elseif action == "r1" then
            load_directory(path)
        end
    end)
end

function scene.update(dt)
    local visible = math.max(1, math.floor((list_bottom - list_top) / row_h))
    if selected < first_visible then first_visible = selected end
    if selected > first_visible + visible - 1 then
        first_visible = selected - visible + 1
    end
end

function scene.draw()
    local W, H = love.graphics.getDimensions()
    local th = theme.get()
    love.graphics.clear(0.015, 0.02, 0.03, 1)
    love.graphics.setColor(node_color[1], node_color[2], node_color[3], 0.12)
    love.graphics.rectangle("fill", 0, chrome.HEADER_H, W, 54)
    love.graphics.setFont(font.regular(12) or love.graphics.newFont(12))
    love.graphics.setColor(th.text[1], th.text[2], th.text[3], 0.9)
    local location = path ~= "" and path or "MEDIA ROOTS"
    if #location > 72 then location = "..." .. location:sub(-69) end
    love.graphics.print(location, 16, 76)
    love.graphics.setColor(0.55, 0.62, 0.68, 0.9)
    love.graphics.print("A: open / play    B: parent    X: stop    R1: refresh", 16, 94)

    local visible = math.max(1, math.floor((list_bottom - list_top) / row_h))
    for i = 1, visible do
        local idx = first_visible + i - 1
        local item = entries[idx]
        if not item then break end
        local y = list_top + (i - 1) * row_h
        if idx == selected then
            love.graphics.setColor(node_color[1], node_color[2], node_color[3], 0.18)
            love.graphics.rectangle("fill", 12, y, W - 24, row_h - 1, 3)
            love.graphics.setColor(node_color[1], node_color[2], node_color[3], 0.9)
            love.graphics.rectangle("line", 12, y, W - 24, row_h - 1, 3)
        end
        love.graphics.setFont(font.regular(13) or love.graphics.newFont(13))
        love.graphics.setColor(item.is_dir and 0.65 or 0.9,
                               item.is_dir and 0.78 or 0.92,
                               item.is_dir and 0.88 or 0.95, 0.95)
        local label = (item.is_dir and "[DIR] " or "      ") .. item.name
        if #label > 66 then label = label:sub(1, 63) .. "..." end
        love.graphics.print(label, 20, y + 6)
    end
    love.graphics.setColor(th.panel_bg[1], th.panel_bg[2], th.panel_bg[3], 0.95)
    love.graphics.rectangle("fill", 12, 420, W - 24, 25, 4)
    love.graphics.setColor(node_color[1], node_color[2], node_color[3], 0.6)
    love.graphics.rectangle("line", 12, 420, W - 24, 25, 4)
    love.graphics.setFont(font.regular(11) or love.graphics.newFont(11))
    love.graphics.setColor(th.text[1], th.text[2], th.text[3], 0.95)
    local msg = status
    if playing ~= "" then msg = msg .. "  //  " .. playing end
    if #msg > 92 then msg = msg:sub(1, 89) .. "..." end
    love.graphics.print("> " .. msg, 18, 427)

    chrome.draw_header({theme = th, title = "Void-DESK", subtitle = "MEDIA LIBRARY",
                        status_icons = {"wifi", "battery"}})
    chrome.draw_footer({theme = th, hints = {
        {icon = "dpad", label = "Navigate"},
        {icon = "btn_a", label = "Open / Play"},
        {icon = "btn_b", label = "Back"},
    }, right_text = "X stop  //  R1 refresh"})
    if th.scanlines then effects.scanlines(W, H, 0.05) end
    if th.vignette then effects.vignette(W, H, 0.3) end
    love.graphics.setColor(1, 1, 1, 1)
end

return scene
