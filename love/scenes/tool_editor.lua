local sm      = require("core.scene_manager")
local theme   = require("theme.loader")
local input   = require("core.input")
local chrome  = require("core.chrome")
local font    = require("core.font")
local nodes   = require("core.nodes")
local anim    = require("core.anim")

local scene = {}
local t_enter = 0
local nc = nodes.color_for(4)
local cursor_blink = 0

-- Editor state
local lines = {""}
local cur_line = 1
local cur_col = 1
local filename = "untitled.txt"
local dirty = false
local reveal_t = 0     -- for typewriter effect on open
local reveal_chars = 0
local total_chars = 0
local char_pop = {}    -- animated chars [line] = {[col] = t}

local function calc_total()
    local n = 0
    for _, l in ipairs(lines) do n = n + #l + 1 end
    return n
end

local function insert_char(ch)
    local line = lines[cur_line]
    lines[cur_line] = line:sub(1, cur_col - 1) .. ch .. line:sub(cur_col)
    cur_col = cur_col + 1
    dirty = true
    -- Trigger pop animation for this char
    char_pop[cur_line] = char_pop[cur_line] or {}
    char_pop[cur_line][cur_col - 1] = 0
end

local function backspace()
    if cur_col > 1 then
        local line = lines[cur_line]
        lines[cur_line] = line:sub(1, cur_col - 2) .. line:sub(cur_col)
        cur_col = cur_col - 1
    elseif cur_line > 1 then
        local prev = lines[cur_line - 1]
        local cur_l = lines[cur_line]
        lines[cur_line - 1] = prev .. cur_l
        table.remove(lines, cur_line)
        cur_line = cur_line - 1
        cur_col = #prev + 1
    end
    dirty = true
end

local function insert_newline()
    local line = lines[cur_line]
    local before = line:sub(1, cur_col - 1)
    local after = line:sub(cur_col)
    lines[cur_line] = before
    table.insert(lines, cur_line + 1, after)
    cur_line = cur_line + 1
    cur_col = 1
    dirty = true
end

function scene.enter(args)
    t_enter = 0
    reveal_t = 0
    cursor_blink = 0
    -- Demo content
    lines = {
        "// VOID EDIT — LÖVE frontend",
        "",
        "local function hello()",
        "    print(\"Hello, VOID\")",
        "end",
        "",
        "hello()",
    }
    cur_line = #lines
    cur_col = #lines[cur_line] + 1
    total_chars = calc_total()
    reveal_chars = 0
    char_pop = {}

    input.clear()
    input.on("press", function(action)
        if action == "b" or action == "menu" then
            sm.switch("hub_toolbox", {})
        elseif action == "up" then
            cur_line = math.max(1, cur_line - 1)
            cur_col = math.min(cur_col, #lines[cur_line] + 1)
        elseif action == "down" then
            cur_line = math.min(#lines, cur_line + 1)
            cur_col = math.min(cur_col, #lines[cur_line] + 1)
        elseif action == "left" then
            if cur_col > 1 then cur_col = cur_col - 1
            elseif cur_line > 1 then
                cur_line = cur_line - 1
                cur_col = #lines[cur_line] + 1
            end
        elseif action == "right" then
            if cur_col <= #lines[cur_line] then cur_col = cur_col + 1
            elseif cur_line < #lines then
                cur_line = cur_line + 1
                cur_col = 1
            end
        elseif action == "a" then
            insert_char(" ")   -- type a space as demo
        elseif action == "x" then
            backspace()
        elseif action == "y" then
            insert_newline()
        end
    end)
end

function scene.update(dt)
    if t_enter < 1 then t_enter = math.min(1, t_enter + dt / 0.55) end
    cursor_blink = cursor_blink + dt
    reveal_t = reveal_t + dt
    -- reveal: 60 chars/sec
    reveal_chars = math.min(total_chars, math.floor(reveal_t * 80))
    -- decay char pop
    for l, cols in pairs(char_pop) do
        for c, t in pairs(cols) do
            cols[c] = math.min(1, t + dt / 0.25)
        end
    end
end

function scene.draw()
    local W, H = love.graphics.getDimensions()
    local th = theme.get()
    love.graphics.clear(0, 0, 0, 1)

    local content_y = chrome.HEADER_H + 8
    local content_h = H - chrome.FOOTER_H - 16 - content_y

    -- Background panel
    love.graphics.setColor(0.03, 0.04, 0.06, 0.98)
    love.graphics.rectangle("fill", 8, content_y, W - 16, content_h, 4)
    love.graphics.setColor(nc[1], nc[2], nc[3], 0.5)
    love.graphics.setLineWidth(1)
    love.graphics.rectangle("line", 8, content_y, W - 16, content_h, 4)

    -- Gutter (line numbers)
    local gutter_w = 36
    love.graphics.setColor(0.06, 0.08, 0.11, 0.9)
    love.graphics.rectangle("fill", 8, content_y, gutter_w, content_h,
                            4, 4, 0, 0)

    -- Text
    local f_mono = font.mono(14) or love.graphics.newFont(14)
    local f_gut = font.mono(12) or love.graphics.newFont(12)
    local line_h = 18
    local chars_shown = reveal_chars
    local yy = content_y + 8

    for i, line in ipairs(lines) do
        -- Gutter number
        love.graphics.setFont(f_gut)
        love.graphics.setColor(
            i == cur_line and nc[1] or 0.35,
            i == cur_line and nc[2] or 0.40,
            i == cur_line and nc[3] or 0.45,
            1)
        love.graphics.print(tostring(i), 14, yy)

        -- Text with typewriter reveal
        love.graphics.setFont(f_mono)
        if chars_shown > 0 then
            local n = math.min(#line, chars_shown)
            local text = line:sub(1, n)
            -- Char pop scale: animated by char_pop
            love.graphics.setColor(0.90, 0.95, 1.0, 1)
            love.graphics.print(text, 8 + gutter_w + 6, yy)
            chars_shown = chars_shown - (#line + 1)
        end
        yy = yy + line_h
    end

    -- Cursor (blinking block, with glow)
    local cx = 8 + gutter_w + 6
    local cy = content_y + 8 + (cur_line - 1) * line_h
    if cur_col > 1 then
        love.graphics.setFont(f_mono)
        cx = cx + f_mono:getWidth(lines[cur_line]:sub(1, cur_col - 1))
    end
    local blink = (math.floor(cursor_blink * 2) % 2 == 0)
    if blink then
        love.graphics.setColor(nc[1], nc[2], nc[3], 0.9)
        love.graphics.rectangle("fill", cx, cy, 2, line_h - 2)
    end
    -- Cursor glow
    local glow = math.sin(cursor_blink * 4) * 0.3 + 0.7
    love.graphics.setColor(nc[1], nc[2], nc[3], 0.35 * glow)
    love.graphics.setLineWidth(3)
    love.graphics.line(cx - 1, cy, cx - 1, cy + line_h - 2)

    -- Status bar
    local sb_y = H - chrome.FOOTER_H - 28
    love.graphics.setColor(0.05, 0.06, 0.09, 0.95)
    love.graphics.rectangle("fill", 8, sb_y, W - 16, 20, 3)
    love.graphics.setColor(nc[1], nc[2], nc[3], 0.4)
    love.graphics.rectangle("line", 8, sb_y, W - 16, 20, 3)
    local f_st = font.mono(11) or love.graphics.newFont(11)
    love.graphics.setFont(f_st)
    love.graphics.setColor(0.70, 0.75, 0.80, 1)
    local info = string.format("%s   Ln %d/%d   Col %d   %d lines%s",
        filename, cur_line, #lines, cur_col, #lines,
        dirty and "  [modified]" or "")
    love.graphics.print(info, 16, sb_y + 4)

    chrome.draw_header({theme = th, title = "Void-DESK", subtitle = "VOID EDIT",
                       status_icons = {"text", "battery"}})
    chrome.draw_footer({theme = th,
        hints = {
            {icon = "dpad", label = "Move"},
            {icon = "btn_a", label = "Space"},
            {icon = "btn_y", label = "Newline"},
            {icon = "btn_x", label = "Backspace"},
            {icon = "btn_b", label = "Back"},
        },
        right_text = "v10.5.1"})
end

function scene.save_state()
    return {line = cur_line, col = cur_col, filename = filename}
end
function scene.restore_state(s)
    if s then
        cur_line = s.line or 1
        cur_col = s.col or 1
        filename = s.filename or "untitled.txt"
    end
end

return scene
