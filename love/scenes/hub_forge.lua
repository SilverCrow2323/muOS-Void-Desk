local sm      = require("core.scene_manager")
local theme   = require("theme.loader")
local input   = require("core.input")
local chrome  = require("core.chrome")
local effects = require("core.effects")
local font    = require("core.font")
local bridge  = require("core.bridge")
local nodes   = require("core.nodes")
local anim    = require("core.anim")

local forge = {}
local status_msg = "Ready"
local selected = 1
local node_color = nodes.color_for(3)   -- FORGE color

local ACTIONS = {
    { name = "Install XFCE Desktop", cmd = "xfce_install" },
    { name = "Launch XFCE Desktop",  cmd = "xfce_launch" },
    { name = "Update System",        cmd = "apt_update" },
    { name = "Clean apt cache",      cmd = "" },
    { name = "Shell terminal",       cmd = "" },
    { name = "Back",                 cmd = "__back__" },
}

function forge.enter(args)
    selected = 1
    status_msg = "Ready"
    input.clear()
    input.on("press", function(action)
        if action == "up" then
            selected = math.max(1, selected - 1)
        elseif action == "down" then
            selected = math.min(#ACTIONS, selected + 1)
        elseif action == "a" then
            local a = ACTIONS[selected]
            if a.cmd == "__back__" then
                sm.switch("nexus", {})
            elseif a.cmd ~= "" then
                status_msg = "Running: " .. a.name .. "..."
                bridge.call(a.cmd, {}, function(resp)
                    if resp.ok then
                        status_msg = a.name .. " — " .. (resp.note or "done")
                    elseif resp.reason == "device-only" then
                        status_msg = "Device-only: requires handheld"
                    else
                        status_msg = resp.error or "failed"
                    end
                end)
            else
                status_msg = "Not implemented yet"
            end
        elseif action == "b" or action == "menu" then
            sm.switch("nexus", {})
        end
    end)
end

function forge.update(dt) end

function forge.draw()
    local W, H = love.graphics.getDimensions()
    local th = theme.get()
    love.graphics.clear(th.bg[1], th.bg[2], th.bg[3], 1)

    -- subtle forge-color ambient gradient
    for i = 0, 6 do
        local t = i / 6
        love.graphics.setColor(node_color[1], node_color[2], node_color[3],
                               0.03 * (1 - t))
        love.graphics.rectangle("fill", 0, H * 0.5 + i * 20, W, 20)
    end

    -- action list
    local f_item = font.regular(16) or love.graphics.newFont(16)
    love.graphics.setFont(f_item)
    local y = 70
    local pulse = anim.pulse(love.timer.getTime(), 3)
    for i, a in ipairs(ACTIONS) do
        local is_sel = (i == selected)
        if is_sel then
            pcall(effects.glow, W / 2, y + 16, (W - 40) / 2,
                  node_color, 0.7 + 0.2 * pulse, 3)
            love.graphics.setColor(node_color[1], node_color[2], node_color[3],
                                   0.16 + 0.10 * pulse)
            love.graphics.rectangle("fill", 20, y - 4, W - 40, 38, 6)
            love.graphics.setColor(node_color[1], node_color[2], node_color[3], 1)
            love.graphics.setLineWidth(2)
            love.graphics.rectangle("line", 20, y - 4, W - 40, 38, 6)
        end
        local col = is_sel and th.text or th.dim
        love.graphics.setColor(0, 0, 0, 0.6)
        love.graphics.print(a.name, 41, y + 3)
        love.graphics.setColor(col[1], col[2], col[3], 1)
        love.graphics.print(a.name, 40, y + 2)
        y = y + 46
    end

    -- status panel
    local status_y = H - chrome.FOOTER_H - 36
    love.graphics.setColor(th.panel_bg[1], th.panel_bg[2], th.panel_bg[3], 0.85)
    love.graphics.rectangle("fill", 12, status_y, W - 24, 28, 4)
    love.graphics.setColor(node_color[1], node_color[2], node_color[3], 0.6)
    love.graphics.rectangle("line", 12, status_y, W - 24, 28, 4)
    local f_small = font.regular(12) or love.graphics.newFont(12)
    love.graphics.setFont(f_small)
    love.graphics.setColor(th.text[1], th.text[2], th.text[3], 0.9)
    love.graphics.print("> " .. status_msg, 20, status_y + 7)

    -- chrome
    chrome.draw_header({
        theme = th,
        title = "Void-DESK",
        subtitle = "THE FORGE",
        status_icons = { "wifi", "battery" },
    })
    chrome.draw_footer({
        theme = th,
        hints = {
            { icon = "dpad",  label = "Select" },
            { icon = "btn_a", label = "Run" },
            { icon = "btn_b", label = "Back" },
        },
        right_text = "v10.5.1",
    })

    if th.scanlines then effects.scanlines(W, H, 0.06) end
    if th.vignette  then effects.vignette(W, H, 0.35) end
    love.graphics.setColor(1, 1, 1, 1)
end

return forge
