local font    = require("core.font")
local icon    = require("core.icon")
local effects = require("core.effects")

local chrome = {}
chrome.HEADER_H = 62
chrome.FOOTER_H = 50

local function f_bold(sz) return font.bold(sz) or love.graphics.newFont(sz) end
local function f_reg(sz)  return font.regular(sz) or love.graphics.newFont(sz) end

function chrome.draw_header(opts)
    opts = opts or {}
    local W = love.graphics.getWidth()
    local H = chrome.HEADER_H
    local th = opts.theme or {}
    local title    = opts.title    or "Void-DESK"
    local subtitle = opts.subtitle or ""
    local text_col = th.text    or { 0.9, 0.9, 0.9 }
    local accent   = th.accent  or { 0.3, 0.8, 0.9 }
    local header_bg= th.header_bg or { 0.05, 0.06, 0.08 }
    local bg_col   = th.bg      or { 0.02, 0.03, 0.05 }
    local shadow   = th.shadow  or { 0, 0, 0, 0.6 }

    love.graphics.setColor(header_bg[1], header_bg[2], header_bg[3], 1)
    love.graphics.rectangle("fill", 0, 0, W, H)
    pcall(effects.gradient_v, 0, 0, W, H, header_bg, bg_col)

    love.graphics.setColor(accent[1], accent[2], accent[3], 1)
    love.graphics.rectangle("fill", 0, H - 3, W, 3)

    local ft = f_bold(28)
    love.graphics.setFont(ft)
    love.graphics.setColor(shadow[1], shadow[2], shadow[3], shadow[4] or 0.6)
    love.graphics.print(title, 17, 15)
    love.graphics.setColor(text_col[1], text_col[2], text_col[3], 1)
    love.graphics.print(title, 16, 14)
    local tw = ft:getWidth(title)

    if subtitle ~= "" then
        love.graphics.setColor(accent[1], accent[2], accent[3], 1)
        love.graphics.print(subtitle, 16 + tw + 12, 14)
    end

    -- Right side
    local x = W - 14
    local fs = f_reg(18)
    love.graphics.setFont(fs)

    if os.getenv("VOIDDESK_PC") == "1" then
        local badge = "PC ver."
        local bw = fs:getWidth(badge) + 18
        local bh = 24
        x = x - bw
        love.graphics.setColor(accent[1], accent[2], accent[3], 0.18)
        love.graphics.rectangle("fill", x, 16, bw, bh, 10)
        love.graphics.setColor(accent[1], accent[2], accent[3], 0.9)
        love.graphics.setLineWidth(1.5)
        love.graphics.rectangle("line", x, 16, bw, bh, 10)
        love.graphics.setColor(accent[1], accent[2], accent[3], 1)
        love.graphics.print(badge, x + 9, 20)
        x = x - 8
    end

    local clock_str = os.date("%H:%M")
    love.graphics.setFont(fs)
    local cw = fs:getWidth(clock_str)
    x = x - cw
    love.graphics.setColor(text_col[1], text_col[2], text_col[3], 1)
    love.graphics.print(clock_str, x, 20)
    x = x - 12

    local sz = 22
    local icons = opts.status_icons or { "wifi", "battery" }
    for i = #icons, 1, -1 do
        local name = icons[i]
        x = x - sz
        pcall(icon.draw, name, x, 16, sz, text_col, { alpha = 0.9, fill = 0.75 })
        x = x - 6
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
    love.graphics.setColor(footer_bg[1], footer_bg[2], footer_bg[3], 1)
    love.graphics.rectangle("fill", 0, y0, W, chrome.FOOTER_H)
    pcall(effects.gradient_v, 0, y0, W, chrome.FOOTER_H, bg_col, footer_bg)

    love.graphics.setColor(accent[1], accent[2], accent[3], 1)
    love.graphics.rectangle("fill", 0, y0, W, 2)

    local f = f_reg(16)
    love.graphics.setFont(f)
    local x = 14
    local yy = y0 + 14
    local isz = 20

    for _, hint in ipairs(hints) do
        if hint.icon then
            pcall(icon.draw, hint.icon, x, yy - 3, isz, accent, { alpha = 0.95 })
            x = x + isz + 6
        end
        love.graphics.setColor(text_col[1], text_col[2], text_col[3], 0.9)
        love.graphics.print(hint.label or "", x, yy)
        x = x + f:getWidth(hint.label or "") + 18
    end

    if opts.right_text then
        love.graphics.setColor(dim_col[1], dim_col[2], dim_col[3], 1)
        local tw = f:getWidth(opts.right_text)
        love.graphics.print(opts.right_text, W - tw - 14, yy)
    end
end

return chrome
