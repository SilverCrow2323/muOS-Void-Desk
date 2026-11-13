local sm      = require("core.scene_manager")
local theme   = require("theme.loader")
local chrome  = require("core.chrome")
local effects = require("core.effects")
local font    = require("core.font")
local input   = require("core.input")
local nodes   = require("core.nodes")
local bridge  = require("core.bridge")
local shell   = require("core.shell_client")
local L       = require("core.layout")

local scene = {}
local nc = nodes.color_for(4)

local t_enter = 0
local status_msg = "Initializing PTY..."
local python_repl = false
local boot_t = 0
local BOOT_DUR = 1.4

-- Quick commands
local QUICK = {
    { label = "ls",        cmd = "ls -la" },
    { label = "pwd",       cmd = "pwd" },
    { label = "df -h",     cmd = "df -h" },
    { label = "free -m",   cmd = "free -m" },
    { label = "uptime",    cmd = "uptime" },
    { label = "clear",     cmd = "clear" },
    { label = "neofetch",  cmd = "uname -a" },
    { label = "top",       cmd = "top -n 1 | head -20" },
}
local sel_quick = 1
local mode = "quick"     -- quick | osk
local osk_buf = ""
local osk_page = 0
local osk_sel = 0

local OSK_PAGES = {
    {"q","w","e","r","t","y","u","i","o","p"},
    {"a","s","d","f","g","h","j","k","l","-"},
    {"z","x","c","v","b","n","m",".","_","/"},
    {"1","2","3","4","5","6","7","8","9","0"},
}
local OSK_SPECIAL = {"SHIFT", "SPACE", "DEL", "ENTER"}

scene.set_status = function(m) status_msg = m end

local function draw_output(y0, y1)
    -- Split into wrapped lines using the mono font
    local fm = font.mono(L.FONT.mono) or love.graphics.newFont(L.FONT.mono)
    love.graphics.setFont(fm)
    local cw = fm:getWidth("M")
    local lh = fm:getHeight() + 2
    local max_cols = math.floor((love.graphics.getWidth() - 32) / cw)

    -- Split output by newline, then wrap long lines
    local lines = {}
    for line in (shell.output or ""):gmatch("[^\n]*") do
        if #line <= max_cols then
            table.insert(lines, line)
        else
            local i = 1
            while i <= #line do
                table.insert(lines, line:sub(i, i + max_cols - 1))
                i = i + max_cols
            end
        end
    end

    local visible = math.floor((y1 - y0) / lh)
    local start = math.max(1, #lines - visible + 1)
    local yy = y0
    for i = start, #lines do
        love.graphics.setColor(0.85, 0.92, 0.80, 0.95)
        love.graphics.print(lines[i], 16, yy)
        yy = yy + lh
    end
end

local function draw_quick_bar(y0)
    local f = font.bold(14) or love.graphics.newFont(14)
    love.graphics.setFont(f)
    local btn_w = 76
    local btn_h = 34
    local gap = 6
    local x = 16
    for i, q in ipairs(QUICK) do
        local sel = (i == sel_quick)
        if sel then
            love.graphics.setColor(nc[1], nc[2], nc[3], 0.35)
            love.graphics.rectangle("fill", x, y0, btn_w, btn_h, 6)
            love.graphics.setColor(nc[1], nc[2], nc[3], 1)
            love.graphics.setLineWidth(2)
            love.graphics.rectangle("line", x, y0, btn_w, btn_h, 6)
        else
            love.graphics.setColor(0.10, 0.12, 0.16, 0.9)
            love.graphics.rectangle("fill", x, y0, btn_w, btn_h, 6)
            love.graphics.setColor(0.4, 0.45, 0.5, 1)
            love.graphics.setLineWidth(1)
            love.graphics.rectangle("line", x, y0, btn_w, btn_h, 6)
        end
        love.graphics.setColor(sel and {1,1,1} or {0.75, 0.80, 0.85})
        local tw = f:getWidth(q.label)
        love.graphics.print(q.label, x + (btn_w - tw)/2, y0 + 10)
        x = x + btn_w + gap
        if x + btn_w > love.graphics.getWidth() - 16 then
            x = 16
            y0 = y0 + btn_h + gap
        end
    end
end

local function draw_osk(y0)
    local f = font.bold(18) or love.graphics.newFont(18)
    love.graphics.setFont(f)

    -- Input preview
    love.graphics.setColor(0.05, 0.06, 0.10, 0.95)
    love.graphics.rectangle("fill", 16, y0, love.graphics.getWidth() - 32, 36, 6)
    love.graphics.setColor(nc[1], nc[2], nc[3], 0.6)
    love.graphics.setLineWidth(1)
    love.graphics.rectangle("line", 16, y0, love.graphics.getWidth() - 32, 36, 6)
    love.graphics.setColor(0.9, 0.92, 0.95, 1)
    love.graphics.print("> " .. osk_buf .. "_", 24, y0 + 8)

    -- Pages
    local page = OSK_PAGES[osk_page + 1]
    local COLS = 10
    local key_w, key_h = 56, 42
    local px = 16
    local py = y0 + 46

    for i, k in ipairs(page) do
        local col = (i - 1) % COLS
        local row = math.floor((i - 1) / COLS)
        local x = px + col * (key_w + 4)
        local y = py + row * (key_h + 4)
        local sel = (i - 1 == osk_sel)
        if sel then
            love.graphics.setColor(nc[1], nc[2], nc[3], 0.4)
            love.graphics.rectangle("fill", x, y, key_w, key_h, 6)
            love.graphics.setColor(nc[1], nc[2], nc[3], 1)
            love.graphics.setLineWidth(2)
            love.graphics.rectangle("line", x, y, key_w, key_h, 6)
        else
            love.graphics.setColor(0.10, 0.12, 0.16, 0.9)
            love.graphics.rectangle("fill", x, y, key_w, key_h, 6)
        end
        love.graphics.setColor(sel and {1,1,1} or {0.85, 0.88, 0.92})
        local tw = f:getWidth(k)
        love.graphics.print(k, x + (key_w - tw)/2, y + 8)
    end

    -- Specials row
    local sy = py + 4 * (key_h + 4)
    local sx = 16
    for i, s in ipairs(OSK_SPECIAL) do
        local w = 90
        love.graphics.setColor(0.15, 0.17, 0.22, 0.9)
        love.graphics.rectangle("fill", sx, sy, w, key_h - 6, 6)
        love.graphics.setColor(nc[1], nc[2], nc[3], 0.6)
        love.graphics.setLineWidth(1)
        love.graphics.rectangle("line", sx, sy, w, key_h - 6, 6)
        love.graphics.setColor(0.85, 0.88, 0.92)
        local tw = f:getWidth(s)
        love.graphics.print(s, sx + (w - tw)/2, sy + 6)
        sx = sx + w + 6
    end
end

function scene.enter(args)
    t_enter = 0
    boot_t = 0
    mode = "quick"
    sel_quick = 1
    osk_buf = ""
    osk_page = 0
    osk_sel = 0
    python_repl = args and args.python_repl == true
    status_msg = python_repl and "Starting Python REPL..." or "Initializing PTY..."
    shell.output = ""
    shell.start(function(resp)
        if resp.ok and python_repl then
            shell.exec("python3 -q")
            scene.set_status("Python interactive console")
        elseif not resp.ok then
            scene.set_status("Terminal unavailable: " .. tostring(resp.error or "start failed"))
        end
    end)
    input.clear()
    input.on("press", function(action)
        if boot_t < BOOT_DUR then return end
        if mode == "quick" then
            if action == "left" then
                sel_quick = math.max(1, sel_quick - 1)
            elseif action == "right" then
                sel_quick = math.min(#QUICK, sel_quick + 1)
            elseif action == "a" then
                local cmd = QUICK[sel_quick].cmd
                scene.set_status("Running: " .. cmd)
                shell.exec(cmd)
            elseif action == "y" then
                mode = "osk"
                osk_buf = ""
                osk_sel = 0
                scene.set_status("Type a command")
            elseif action == "b" then
                shell.stop()
                sm.back()
            end
        elseif mode == "osk" then
            local page = OSK_PAGES[osk_page + 1]
            local cols = 10
            if action == "left" then
                osk_sel = math.max(0, osk_sel - 1)
            elseif action == "right" then
                osk_sel = math.min(#page - 1, osk_sel + 1)
            elseif action == "up" then
                osk_sel = math.max(0, osk_sel - cols)
            elseif action == "down" then
                osk_sel = math.min(#page - 1, osk_sel + cols)
            elseif action == "l1" then
                osk_page = (osk_page - 1) % #OSK_PAGES
                osk_sel = 0
            elseif action == "r1" then
                osk_page = (osk_page + 1) % #OSK_PAGES
                osk_sel = 0
            elseif action == "a" then
                local k = page[osk_sel + 1]
                if k then osk_buf = osk_buf .. k end
            elseif action == "x" then
                osk_buf = osk_buf:sub(1, -2)
            elseif action == "start" then
                if osk_buf ~= "" then
                    scene.set_status("Running: " .. osk_buf)
                    shell.exec(osk_buf)
                    osk_buf = ""
                end
                mode = "quick"
            elseif action == "b" then
                mode = "quick"
                osk_buf = ""
            end
        end
    end)
end

function scene.update(dt)
    if t_enter < 1 then t_enter = math.min(1, t_enter + dt / 0.4) end
    if boot_t < BOOT_DUR then
        boot_t = boot_t + dt
        if boot_t >= BOOT_DUR then
            scene.set_status("Ready")
        end
    else
        shell.poll(dt)
    end
end

function scene.draw()
    local W, H = love.graphics.getDimensions()
    local th = theme.get()

    love.graphics.clear(0.01, 0.02, 0.02, 1)

    -- Data stream background
    for i = 0, 24 do
        local y = (i * 23 + (love.timer.getTime() * 30) % H) % H
        love.graphics.setColor(0.20, 0.40, 0.35, 0.05)
        love.graphics.rectangle("fill", 0, y, W, 1)
    end

    -- Boot sequence
    if boot_t < BOOT_DUR then
        local txt = "INITIALIZING PTY"
        local shown = math.floor(#txt * (boot_t / BOOT_DUR))
        local f = font.bold(24) or love.graphics.newFont(24)
        love.graphics.setFont(f)
        love.graphics.setColor(0.4, 0.9, 0.5, 0.9)
        local s = txt:sub(1, shown) .. "_"
        local tw = f:getWidth(s)
        love.graphics.print(s, (W - tw)/2, H/2 - 12)
        -- Glitch
        if math.random() < 0.15 then
            local gx = math.random(-8, 8)
            love.graphics.setColor(1, 0.3, 0.3, 0.3)
            love.graphics.print(s, (W - tw)/2 + gx, H/2 - 12)
        end
    else
        -- Output area
        local y_top = chrome.HEADER_H + 8
        local y_bottom = (mode == "osk") and (H - 300) or (H - chrome.FOOTER_H - 60)
        draw_output(y_top, y_bottom)

        -- Quick bar / OSK
        if mode == "quick" then
            draw_quick_bar(H - chrome.FOOTER_H - 52)
        else
            draw_osk(H - 330)
        end
    end

    -- Header
    chrome.draw_header({
        theme = th, title = "Void-DESK", subtitle = (python_repl and "PYTHON CONSOLE" or "SHELL"),
        status_icons = { "wifi", "battery" },
    })

    -- Footer
    if mode == "quick" then
        chrome.draw_footer({
            theme = th,
            hints = {
                { icon = "dpad", label = "Cmd" },
                { icon = "btn_a", label = "Run" },
                { icon = "btn_b", label = "Back" },
                { icon = "btn_y", label = "Type" },
            },
            right_text = "pid " .. tostring(shell.ready and "ready" or "—"),
        })
    else
        chrome.draw_footer({
            theme = th,
            hints = {
                { icon = "dpad", label = "Key" },
                { icon = "btn_a", label = "Type" },
                { icon = "btn_x", label = "Del" },
                { icon = "btn_b", label = "Close" },
            },
            right_text = "L1/R1 page",
        })
    end

    if th.scanlines then effects.scanlines(W, H, 0.10) end
    if th.vignette then effects.vignette(W, H, 0.5) end
    love.graphics.setColor(1, 1, 1, 1)
end

return scene
