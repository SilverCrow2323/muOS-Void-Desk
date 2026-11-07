local font    = require("core.font")
local icon    = require("core.icon")
local effects = require("core.effects")

local chrome = {}
chrome.HEADER_H = 42
chrome.FOOTER_H = 32

-- Safe font getters (never return nil)
local function f_bold(sz)
    local f = font.bold(sz)
    return f or love.graphics.newFont(sz)
end
local function f_reg(sz)
    local f = font.regular(sz)
    return f or love.graphics.newFont(sz)
end

function chrome.draw_header(opts)
    opts = opts or {}
    local W = love.graphics.getWidth()
    local H = chrome.HEADER_H
    local th = opts.theme or {}
    local title    = opts.title    or "Void-DESK"
    local subtitle = opts.subtitle or ""
    local text_col = th.text       or { 0.9, 0.9, 0.9 }
    local accent   = th.accent     or { 0.3, 0.8, 0.9 }
    local dim_col  = th.dim        or { 0.5, 0.5, 0.5 }
    local shadow   = th.shadow     or { 0, 0, 0, 0.6 }
    local header_bg= th.header_bg  or { 0.05, 0.06, 0.08 }
    local bg_col   = th.bg         or { 0.02, 0.03, 0.05 }

    -- 1. solid background (guarantees visibility even if gradient fails)
    love.graphics.setColor(header_bg[1], header_bg[2], header_bg[3], 1)
    love.graphics.rectangle("fill", 0, 0, W, H)

    -- 2. subtle gradient top → bottom
    pcall(effects.gradient_v, 0, 0, W, H, header_bg, bg_col)

    -- 3. accent underline
    love.graphics.setColor(accent[1], accent[2], accent[3], 1)
    love.graphics.rectangle("fill", 0, H - 2, W, 2)

    -- 4. title
    local ft = f_bold(18)
    love.graphics.setFont(ft)
    -- shadow
    love.graphics.setColor(shadow[1], shadow[2], shadow[3], shadow[4] or 0.6)
    love.graphics.print(title, 13, 9)
    -- main text
    love.graphics.setColor(text_col[1], text_col[2], text_col[3], 1)
    love.graphics.print(title, 12, 8)
    local tw = ft:getWidth(title)

    -- 5. subtitle
    if subtitle ~= "" then
        love.graphics.setColor(accent[1], accent[2], accent[3], 1)
        love.graphics.print(subtitle, 12 + tw + 10, 8)
    end

    -- 6. right-side icons + clock
    local x = W - 12
    local fs = f_reg(11)
    love.graphics.setFont(fs)

    -- PC ver. badge (shown only when VOIDDESK_PC=1 is set by the launcher)
    if os.getenv("VOIDDESK_PC") == "1" then
        local badge_text = "PC ver."
        local bw = fs:getWidth(badge_text) + 14
        local bh = 18
        x = x - bw
        -- pill background
        love.graphics.setColor(accent[1], accent[2], accent[3], 0.18)
        love.graphics.rectangle("fill", x, 12, bw, bh, 8)
        -- pill border
        love.graphics.setColor(accent[1], accent[2], accent[3], 0.9)
        love.graphics.setLineWidth(1.5)
        love.graphics.rectangle("line", x, 12, bw, bh, 8)
        -- pill text
        love.graphics.setColor(accent[1], accent[2], accent[3], 1)
        love.graphics.print(badge_text, x + 7, 14)
        x = x - 6
    end

    local clock_str = os.date("%H:%M")
    local cw = fs:getWidth(clock_str)
    x = x - cw
    love.graphics.setColor(text_col[1], text_col[2], text_col[3], 1)
    love.graphics.print(clock_str, x, 15)
    x = x - 10

    local sz = 18
    local icons_to_draw = opts.status_icons or { "wifi", "battery" }
    for i = #icons_to_draw, 1, -1 do
        local name = icons_to_draw[i]
        x = x - sz
        pcall(icon.draw, name, x, 12, sz, text_col, { alpha = 0.9, fill = 0.75 })
        x = x - 4
    end
end

function chrome.draw_footer(opts)
    opts = opts or {}
    local W, H = love.graphics.getWidth(), love.graphics.getHeight()
    local th = opts.theme or {}
    local hints = opts.hints or {}
    local accent   = th.accent    or { 0.3, 0.8, 0.9 }
    local text_col = th.text      or { 0.9, 0.9, 0.9 }
    local dim_col  = th.dim       or { 0.5, 0.5, 0.5 }
    local footer_bg= th.footer_bg or { 0.03, 0.04, 0.06 }
    local bg_col   = th.bg        or { 0.02, 0.03, 0.05 }

    local y0 = H - chrome.FOOTER_H

    -- background
    love.graphics.setColor(footer_bg[1], footer_bg[2], footer_bg[3], 1)
    love.graphics.rectangle("fill", 0, y0, W, chrome.FOOTER_H)
    pcall(effects.gradient_v, 0, y0, W, chrome.FOOTER_H, bg_col, footer_bg)

    -- accent line
    love.graphics.setColor(accent[1], accent[2], accent[3], 1)
    love.graphics.rectangle("fill", 0, y0, W, 2)

    -- hints
    local f = f_reg(11)
    love.graphics.setFont(f)
    local x = 12
    local yy = y0 + 11
    local isz = 16

    for _, hint in ipairs(hints) do
        if hint.icon then
            pcall(icon.draw, hint.icon, x, yy - 2, isz, accent, { alpha = 0.95 })
            x = x + isz + 4
        end
        love.graphics.setColor(text_col[1], text_col[2], text_col[3], 0.9)
        love.graphics.print(hint.label or "", x, yy)
        x = x + f:getWidth(hint.label or "") + 14
    end

    if opts.right_text then
        love.graphics.setColor(dim_col[1], dim_col[2], dim_col[3], 1)
        local tw = f:getWidth(opts.right_text)
        love.graphics.print(opts.right_text, W - tw - 12, yy)
    end
end

return chrome
