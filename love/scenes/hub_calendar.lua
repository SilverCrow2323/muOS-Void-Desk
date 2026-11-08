local sm      = require("core.scene_manager")
local theme   = require("theme.loader")
local chrome  = require("core.chrome")
local effects = require("core.effects")
local font    = require("core.font")
local icon    = require("core.icon")
local input   = require("core.input")
local nodes   = require("core.nodes")
local anim    = require("core.anim")
local bridge  = require("core.bridge")
local L       = require("core.layout")

local scene = {}
local nc = nodes.color_for(4)

local today = os.date("*t")
local cur_year, cur_month = today.year, today.month
local sel_day = today.day
local today_year, today_month, today_day =
    today.year, today.month, today.day
local events = {}
local t_enter = 0
local t_month_change = 1.0     -- 0..1 animation
local month_dir = 1            -- -1 prev, +1 next
local status_msg = "Ready"
scene.set_status = function(m) status_msg = m end

-- Colors per category
local CAT_COLORS = {
    release  = {1.00, 0.35, 0.35},
    meeting  = {0.35, 0.70, 1.00},
    reminder = {1.00, 0.80, 0.30},
    personal = {0.40, 0.90, 0.55},
}

local COLS, ROWS = 7, 6
local CELL_W, CELL_H = 82, 60
local GRID_X, GRID_Y = 12, 92
local DETAIL_W = 190
local DETAIL_X = 12 + 7 * CELL_W + 14

local WEEKDAYS = {"S","M","T","W","T","F","S"}

local function days_in_month(y, m)
    return tonumber(os.date("%d", os.time{year=y, month=m+1, day=0}))
end

local function first_weekday(y, m)
    return tonumber(os.date("%w", os.time{year=y, month=m, day=1}))
end

local function refresh_events()
    bridge.call("calendar_events", { year=cur_year, month=cur_month }, function(resp)
        if resp.ok then events = resp.events or {} end
    end)
end

local function prev_month()
    cur_month = cur_month - 1
    if cur_month < 1 then cur_month = 12; cur_year = cur_year - 1 end
    month_dir = -1; t_month_change = 0
    sel_day = 1
    refresh_events()
    scene.set_status(os.date("%B %Y", os.time{year=cur_year, month=cur_month, day=1}))
end

local function next_month()
    cur_month = cur_month + 1
    if cur_month > 12 then cur_month = 1; cur_year = cur_year + 1 end
    month_dir = 1; t_month_change = 0
    sel_day = 1
    refresh_events()
    scene.set_status(os.date("%B %Y", os.time{year=cur_year, month=cur_month, day=1}))
end

local function move_day(delta)
    local max_day = days_in_month(cur_year, cur_month)
    sel_day = math.max(1, math.min(max_day, sel_day + delta))
end

function scene.enter(args)
    t_enter = 0
    t_month_change = 1.0
    scene._t = 0
    input.clear()
    refresh_events()
    scene.set_status("Use LEFT/RIGHT to select, L1/R1 for months")
    input.on("press", function(action)
        if action == "left" or action == "up" then move_day(-1)
        elseif action == "right" or action == "down" then move_day(1)
        elseif action == "l1" then prev_month()
        elseif action == "r1" then next_month()
        elseif action == "a" then
            local key = string.format("%04d-%02d-%02d", cur_year, cur_month, sel_day)
            local evs = events[key] or {}
            if #evs > 0 then
                scene.set_status(evs[1].title)
            else
                scene.set_status("No events on " .. key)
            end
        elseif action == "b" then
            sm.back()
        end
    end)
end

function scene.update(dt)
    if t_enter < 1 then t_enter = math.min(1, t_enter + dt / 0.5) end
    if t_month_change < 1 then t_month_change = math.min(1, t_month_change + dt / 0.4) end
    scene._t = (scene._t or 0) + dt
end

local function draw_cell(x, y, w, h, day, is_today, is_sel, evs, cell_alpha, t_off)
    local a = cell_alpha

    -- Selection outer ring (rotating)
    if is_sel then
        local t_now = love.timer.getTime()
        local pulse = 0.5 + 0.5 * math.sin(t_now * 3.5)
        for k = 0, 3 do
            local ang0 = t_now * 1.2 + k * math.pi / 2
            local ang1 = ang0 + math.pi / 4
            love.graphics.setColor(nc[1], nc[2], nc[3], 0.85 * a)
            love.graphics.setLineWidth(3)
            love.graphics.arc("line", "open",
                x + w/2, y + h/2,
                w/2 + 4 + pulse * 3, ang0, ang1)
        end
        love.graphics.setColor(nc[1], nc[2], nc[3], 0.20 * a)
        love.graphics.rectangle("fill", x, y, w - 6, h - 6, 8)
    end

    -- Card background
    love.graphics.setColor(0.06, 0.07, 0.10, 0.92 * a)
    love.graphics.rectangle("fill", x, y, w - 6, h - 6, 8)

    -- Today's light beam
    if is_today then
        for i = 0, 10 do
            local beam_a = (0.10 - i * 0.008) * a
            love.graphics.setColor(1, 0.85, 0.35, beam_a)
            love.graphics.rectangle("fill", x + w/2 - 8 + i * 0.3, y - 4 + t_off, 16 - i * 0.5, h)
        end
        love.graphics.setColor(1, 0.85, 0.35, 0.8 * a)
        love.graphics.rectangle("line", x, y, w - 6, h - 6, 8)
    else
        love.graphics.setColor(nc[1], nc[2], nc[3], 0.4 * a)
        love.graphics.setLineWidth(1)
        love.graphics.rectangle("line", x, y, w - 6, h - 6, 8)
    end

    -- Day number
    local f = font.bold(20) or love.graphics.newFont(20)
    love.graphics.setFont(f)
    love.graphics.setColor(is_today and {1,0.9,0.4} or {0.92,0.94,0.96})
    local txt = tostring(day)
    local tw = f:getWidth(txt)
    love.graphics.print(txt, x + (w - 6 - tw)/2, y + 8)

    -- Event indicators
    if evs and #evs > 0 then
        local pulse = 0.6 + 0.4 * math.sin((love.timer.getTime() + day) * 3)
        for i = 1, math.min(3, #evs) do
            local cat = evs[i].category or "personal"
            local c = CAT_COLORS[cat] or {0.9, 0.9, 0.9}
            local cx = x + (w - 6)/2 + (i - 2) * 12
            local cy = y + h - 16
            love.graphics.setColor(c[1], c[2], c[3], a * pulse)
            love.graphics.polygon("fill",
                cx, cy - 4, cx + 4, cy, cx, cy + 4, cx - 4, cy)
        end
    end

    -- Update status on selected cell
    if is_sel and evs and #evs > 0 then
        -- nothing (status already set on A press)
    end
end

function scene.draw()
    local W, H = love.graphics.getDimensions()
    local th = theme.get()

    love.graphics.clear(th.bg[1], th.bg[2], th.bg[3], 1)

    -- Background: subtle constellation of dates
    for i = 0, 20 do
        local x = (i * 137 + 13) % W
        local y = (i * 71 + 41) % H
        local tw = 0.3 + 0.5 * math.abs(math.sin(love.timer.getTime() + i))
        love.graphics.setColor(nc[1], nc[2], nc[3], tw * 0.08)
        love.graphics.circle("fill", x, y, 1.5)
    end

    -- Weekday header (7 columns)
    local fwd = font.bold(14) or love.graphics.newFont(14)
    love.graphics.setFont(fwd)
    for c = 0, COLS - 1 do
        local x = GRID_X + c * CELL_W
        local label = WEEKDAYS[c + 1]
        local tw = fwd:getWidth(label)
        love.graphics.setColor(nc[1], nc[2], nc[3], 0.6)
        love.graphics.print(label, x + (CELL_W - 6 - tw)/2, GRID_Y - 26)
    end

    -- Month title (big, animated)
    local title = os.date("%B %Y", os.time{year=cur_year, month=cur_month, day=1})
    local ft = font.bold(28) or love.graphics.newFont(28)
    love.graphics.setFont(ft)
    local ttw = ft:getWidth(title)
    love.graphics.setColor(nc[1], nc[2], nc[3], 0.95)
    love.graphics.print(title, DETAIL_X - 4, chrome.HEADER_H + 8)

    -- Draw day cells with stagger
    local max_day = days_in_month(cur_year, cur_month)
    local first = first_weekday(cur_year, cur_month)

    for day = 1, max_day do
        local idx = first + day - 1
        local row = math.floor(idx / COLS)
        local col = idx % COLS
        local x = GRID_X + col * CELL_W
        local y = GRID_Y + row * CELL_H
        local key = string.format("%04d-%02d-%02d", cur_year, cur_month, day)
        local evs = events[key] or {}
        local is_today = (cur_year == today_year and cur_month == today_month and day == today_day)
        local is_sel = (day == sel_day)

        -- Stagger cell entrance
        local delay = (row + col) * 0.03
        local ca = math.max(0, math.min(1, (t_enter - delay) / 0.25))
        -- Month transition: cells fade out then in with slide
        if t_month_change < 1 then
            local tt = t_month_change
            if tt < 0.5 then
                ca = ca * (1 - tt * 2)
            else
                ca = ca * (tt - 0.5) * 2
            end
            x = x + month_dir * (1 - t_month_change) * 60
        end

        if ca > 0.01 then
            draw_cell(x, y, CELL_W, CELL_H, day, is_today, is_sel, evs, ca, 0)
        end
    end

    -- Right detail panel
    local dp_a = math.min(1, t_enter * 1.5)
    if dp_a > 0.01 then
        local px, py, pw, ph = DETAIL_X, GRID_Y + 6, DETAIL_W, 420
        love.graphics.setColor(0.05, 0.06, 0.09, 0.92 * dp_a)
        love.graphics.rectangle("fill", px, py, pw, ph, 8)
        love.graphics.setColor(nc[1], nc[2], nc[3], 0.6 * dp_a)
        love.graphics.setLineWidth(1.5)
        love.graphics.rectangle("line", px, py, pw, ph, 8)

        local fh = font.bold(16) or love.graphics.newFont(16)
        love.graphics.setFont(fh)
        love.graphics.setColor(nc[1], nc[2], nc[3], dp_a)
        love.graphics.print("DAY " .. sel_day, px + 12, py + 10)

        local key = string.format("%04d-%02d-%02d", cur_year, cur_month, sel_day)
        local evs = events[key] or {}
        local fs = font.regular(13) or love.graphics.newFont(13)
        love.graphics.setFont(fs)
        love.graphics.setColor(0.6, 0.65, 0.72, dp_a)
        love.graphics.print(key, px + 12, py + 34)

        local fy = py + 64
        if #evs == 0 then
            love.graphics.setColor(0.4, 0.45, 0.5, dp_a)
            love.graphics.print("No events", px + 12, fy)
        else
            for i, ev in ipairs(evs) do
                local cat = ev.category or "personal"
                local c = CAT_COLORS[cat] or {0.9, 0.9, 0.9}
                love.graphics.setColor(c[1], c[2], c[3], dp_a)
                love.graphics.polygon("fill",
                    px + 16, fy + 6, px + 20, fy + 10, px + 16, fy + 14, px + 12, fy + 10)
                love.graphics.setColor(0.92, 0.94, 0.96, dp_a)
                local title = ev.title or "?"
                while #title > 3 and fs:getWidth(title) > pw - 40 do
                    title = title:sub(1, #title - 4) .. "..."
                end
                love.graphics.print(title, px + 26, fy)
                fy = fy + 26
            end
        end
    end

    -- Header + Footer
    chrome.draw_header({
        theme = th, title = "Void-DESK", subtitle = "CALENDAR",
        status_icons = { "wifi", "battery" },
    })
    chrome.draw_footer({
        theme = th,
        hints = {
            { icon = "dpad", label = "Day" },
            { icon = "btn_a", label = "Info" },
            { icon = "btn_b", label = "Back" },
        },
        right_text = "L1/R1 month",
    })

    -- Status strip
    local sy = H - chrome.FOOTER_H - 26
    love.graphics.setColor(0.04, 0.06, 0.10, 0.9)
    love.graphics.rectangle("fill", 0, sy, W, 22)
    love.graphics.setColor(nc[1], nc[2], nc[3], 0.5)
    love.graphics.rectangle("fill", 0, sy, W, 1)
    love.graphics.setFont(font.regular(13) or love.graphics.newFont(13))
    love.graphics.setColor(0.85, 0.88, 0.92, 1)
    love.graphics.print("> " .. status_msg, 16, sy + 5)

    if th.scanlines then effects.scanlines(W, H, 0.06) end
    if th.vignette then effects.vignette(W, H, 0.4) end
    love.graphics.setColor(1, 1, 1, 1)
end

return scene
