local sm      = require("core.scene_manager")
local theme   = require("theme.loader")
local input   = require("core.input")
local chrome  = require("core.chrome")
local font    = require("core.font")
local nodes   = require("core.nodes")
local anim    = require("core.anim")
local icon    = require("core.icon")

local scene = {}
local t_enter = 0
local nc = nodes.color_for(4)

-- Calculator state
local KEYS = {
    {"7","8","9","/"}, {"4","5","6","*"},
    {"1","2","3","-"}, {"0",".","C","+"},
    {"sin","cos","sqrt","="},
}
local key_anim = {}   -- per-key press animation [1..5][1..4] = {t, pressed}
local cur = ""
local history = {}    -- {expr, result, t}
local result_text = ""
local result_t = 0
local status_msg = "Enter expression"

local function eval_expr(e)
    -- Safe evaluator: only digits, ops, .() and a few funcs
    if not e or e == "" then return "" end
    -- Replace known tokens
    e = e:gsub("sqrt", "math.sqrt")
    e = e:gsub("sin", "math.sin")
    e = e:gsub("cos", "math.cos")
    e = e:gsub("pi", "math.pi")
    -- Reject anything not in whitelist
    if e:match("[^%d%.%+%-%*/%(%)%s%a_]") then
        return "?"
    end
    if e:match("[^%d%.%+%-%*/%(%)%s%a_]") then return "?" end
    local ok, res = pcall(function()
        local f = loadstring and loadstring("return " .. e) or load("return " .. e)
        return f()
    end)
    if not ok or res == nil then return "?" end
    if type(res) == "number" then
        if res == math.floor(res) then
            return tostring(math.floor(res))
        end
        return string.format("%.6g", res)
    end
    return "?"
end

local function press_key(ch)
    if ch == "C" then
        cur = ""
        status_msg = "Cleared"
    elseif ch == "=" then
        local r = eval_expr(cur)
        if r ~= "?" then
            table.insert(history, {expr = cur, result = r, t = love.timer.getTime()})
            if #history > 8 then table.remove(history, 1) end
            result_text = r
            result_t = love.timer.getTime()
            cur = r
            status_msg = "=" .. r
        else
            status_msg = "Invalid expression"
        end
    elseif ch == "sin" or ch == "cos" or ch == "sqrt" then
        cur = cur .. ch .. "("
    else
        cur = cur .. ch
    end
end

function scene.enter(args)
    t_enter = 0
    cur = ""
    result_text = ""
    key_anim = {}
    for r = 1, 5 do
        key_anim[r] = {}
        for c = 1, 4 do
            key_anim[r][c] = {t = 1.0, pressed = false}
        end
    end
    input.clear()
    input.on("press", function(action)
        if action == "b" or action == "menu" then
            sm.switch("hub_toolbox", {})
            return
        end
        -- Directions navigate a virtual cursor (grid 4x5)
        if scene._cursor == nil then scene._cursor = {r = 1, c = 1} end
        local cr, cc = scene._cursor.r, scene._cursor.c
        if action == "up" then cr = math.max(1, cr - 1)
        elseif action == "down" then cr = math.min(5, cr + 1)
        elseif action == "left" then cc = math.max(1, cc - 1)
        elseif action == "right" then cc = math.min(4, cc + 1)
        elseif action == "a" then
            local ch = KEYS[cr][cc]
            if ch then
                key_anim[cr][cc] = {t = 0, pressed = true}
                press_key(ch)
            end
        end
        scene._cursor = {r = cr, c = cc}
    end)
    scene._cursor = {r = 1, c = 1}
end

function scene.update(dt)
    if t_enter < 1 then t_enter = math.min(1, t_enter + dt / 0.55) end
    -- Animate keys
    for r = 1, 5 do
        for c = 1, 4 do
            local k = key_anim[r] and key_anim[r][c]
            if k and k.t < 1 then
                k.t = math.min(1, k.t + dt / 0.25)
            end
        end
    end
end

function scene.draw()
    local W, H = love.graphics.getDimensions()
    local th = theme.get()
    love.graphics.clear(0, 0, 0, 1)

    -- Ambient grid pulse
    for i = 0, 10 do
        local a = 0.05 * (1 - i/10) * math.min(1, t_enter * 2)
        love.graphics.setColor(nc[1], nc[2], nc[3], a)
        love.graphics.rectangle("fill", 0, chrome.HEADER_H + i * 38, W, 38)
    end

    local content_y = chrome.HEADER_H + 12
    local content_h = H - chrome.FOOTER_H - 12 - content_y

    -- Display area (top)
    local disp_h = 88
    love.graphics.setColor(0.05, 0.06, 0.09, 0.95)
    love.graphics.rectangle("fill", 12, content_y, W - 24, disp_h, 6)
    love.graphics.setColor(nc[1], nc[2], nc[3], 0.55)
    love.graphics.setLineWidth(2)
    love.graphics.rectangle("line", 12, content_y, W - 24, disp_h, 6)

    -- Expression
    local f_expr = font.mono(20) or love.graphics.newFont(20)
    love.graphics.setFont(f_expr)
    love.graphics.setColor(0.55, 0.65, 0.75, 1)
    love.graphics.print(cur .. (math.floor(love.timer.getTime() * 2) % 2 == 0 and "_" or ""),
        24, content_y + 12)

    -- Result (with fade pop)
    if result_text ~= "" then
        local age = love.timer.getTime() - result_t
        local alpha = math.min(1, age / 0.4)
        local pop = 1 + 0.15 * math.max(0, 1 - age / 0.3)
        local f_res = font.bold(math.floor(32 * pop)) or love.graphics.newFont(32)
        love.graphics.setFont(f_res)
        love.graphics.setColor(nc[1], nc[2], nc[3], alpha)
        love.graphics.print("= " .. result_text, 24, content_y + 48)
    end

    -- History (right side)
    if #history > 0 then
        local hx = W - 200
        local hy = content_y + 12
        local f_hist = font.mono(11) or love.graphics.newFont(11)
        love.graphics.setFont(f_hist)
        for i = math.max(1, #history - 4), #history do
            local h = history[i]
            local age = love.timer.getTime() - h.t
            local a = math.min(1, age / 0.3)
            love.graphics.setColor(0.45, 0.55, 0.65, 0.7 * a)
            love.graphics.print(h.expr:sub(1, 18) .. " = " .. h.result:sub(1, 8),
                hx, hy)
            hy = hy + 14
        end
    end

    -- Keypad
    local ky = content_y + disp_h + 12
    local kgap = 6
    local cols, rows = 4, 5
    local total_w = W - 24
    local kw = math.floor((total_w - (cols - 1) * kgap) / cols)
    local kh = math.floor((H - chrome.FOOTER_H - ky - 12 - (rows - 1) * kgap) / rows)

    for r = 1, rows do
        for c = 1, cols do
            local kx = 12 + (c - 1) * (kw + kgap)
            local kyy = ky + (r - 1) * (kh + kgap)
            local is_sel = scene._cursor and scene._cursor.r == r and scene._cursor.c == c
            local ka = key_anim[r] and key_anim[r][c] or {t = 1}
            local scale = 1 - 0.15 * math.sin(ka.t * math.pi)
            local w = kw * scale
            local h = kh * scale
            local ox = (kw - w) / 2
            local oy = (kh - h) / 2

            -- Tile
            if is_sel then
                love.graphics.setColor(nc[1], nc[2], nc[3], 0.30)
            else
                love.graphics.setColor(0.08, 0.09, 0.12, 0.95)
            end
            love.graphics.rectangle("fill", kx + ox, kyy + oy, w, h, 5)
            love.graphics.setColor(nc[1], nc[2], nc[3], is_sel and 1.0 or 0.4)
            love.graphics.setLineWidth(is_sel and 2 or 1)
            love.graphics.rectangle("line", kx + ox, kyy + oy, w, h, 5)

            -- Label
            local label = KEYS[r][c]
            local f_k = font.bold(18) or love.graphics.newFont(18)
            love.graphics.setFont(f_k)
            local tw = f_k:getWidth(label)
            love.graphics.setColor(0.9, 0.95, 1.0, 1)
            love.graphics.print(label,
                kx + (kw - tw) / 2, kyy + (kh - f_k:getHeight()) / 2)

            -- Press ripple
            if ka.t < 1 then
                local ring_r = kw * 0.6 * (1 + ka.t * 0.8)
                love.graphics.setColor(nc[1], nc[2], nc[3], (1 - ka.t) * 0.7)
                love.graphics.setLineWidth(2)
                love.graphics.circle("line",
                    kx + kw / 2, kyy + kh / 2, ring_r)
            end
        end
    end

    -- Status
    local f_st = font.regular(13) or love.graphics.newFont(13)
    love.graphics.setFont(f_st)
    love.graphics.setColor(0.5, 0.55, 0.6, 1)
    love.graphics.print(status_msg, 16, H - chrome.FOOTER_H - 16)

    chrome.draw_header({theme = th, title = "Void-DESK", subtitle = "CALCULATOR",
                       status_icons = {"gear", "battery"}})
    chrome.draw_footer({theme = th,
        hints = {
            {icon = "dpad", label = "Navigate"},
            {icon = "btn_a", label = "Press"},
            {icon = "btn_b", label = "Back"},
        },
        right_text = "v10.5.1"})
end

function scene.save_state() return {cursor = scene._cursor} end
function scene.restore_state(s) if s and s.cursor then scene._cursor = s.cursor end end

return scene
