local font    = require("core.font")
local icon    = require("core.icon")
local effects = require("core.effects")
local layout  = require("core.layout")

local chrome = {}

function chrome.draw_header(opts)
    opts = opts or {}
    local L = layout.get()
    local W = love.graphics.getWidth()
    local H = L.header_h
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

    local ft = font.bold(L.font_title) or love.graphics.newFont(L.font_title)
    love.graphics.setFont(ft)
    local title_y = math.floor((H - ft:getHeight()) / 2) - 2
    love.graphics.setColor(shadow[1], shadow[2], shadow[3], shadow[4] or 0.6)
    love.graphics.print(title, 17, title_y + 1)
    love.graphics.setColor(text_col[1], text_col[2], text_col[3], 1)
    love.graphics.print(title, 16, title_y)
    local tw = ft:getWidth(title)

    if subtitle ~= "" then
        local fsub = font.bold(L.font_subtitle) or love.graphics.newFont(L.font_subtitle)
        love.graphics.setFont(fsub)
        local sub_y = math.floor((H - fsub:getHeight()) / 2) - 1
        love.graphics.setColor(accent[1], accent[2], accent[3], 1)
        love.graphics.print(subtitle, 16 + tw + 12, sub_y)
    end

    -- Right side
    local x = W - 14
    local fs = font.regular(L.font_clock) or love.graphics.newFont(L.font_clock)
    love.graphics.setFont(fs)

    if os.getenv("VOIDDESK_PC") == "1" then
        local badge = "PC ver."
        local bw = fs:getWidth(badge) + math.floor(14 * L.scale)
        local bh = fs:getHeight() + math.floor(6 * L.scale)
        local by = math.floor((H - bh) / 2)
        x = x - bw
        love.graphics.setColor(accent[1], accent[2], accent[3], 0.18)
        love.graphics.rectangle("fill", x, by, bw, bh, math.floor(8 * L.scale))
        love.graphics.setColor(accent[1], accent[2], accent[3], 0.9)
        love.graphics.setLineWidth(math.max(1, math.floor(1.5 * L.scale)))
        love.graphics.rectangle("line", x, by, bw, bh, math.floor(8 * L.scale))
        love.graphics.setColor(accent[1], accent[2], accent[3], 1)
        love.graphics.print(badge, x + math.floor(7 * L.scale),
                            by + math.floor(3 * L.scale))
        x = x - math.floor(8 * L.scale)
    end

    local clock = os.date("%H:%M")
    local cw = fs:getWidth(clock)
    local clock_y = math.floor((H - fs:getHeight()) / 2)
    x = x - cw
    love.graphics.setColor(text_col[1], text_col[2], text_col[3], 1)
    love.graphics.print(clock, x, clock_y)
    x = x - math.floor(10 * L.scale)

    local isz = math.floor(L.icon_size * 0.85)
    local icons = opts.status_icons or { "wifi", "battery" }
    for i = #icons, 1, -1 do
        local name = icons[i]
        x = x - isz
        pcall(icon.draw, name, x, math.floor((H - isz) / 2), isz, text_col,
              { alpha = 0.9, fill = 0.75 })
        x = x - math.floor(5 * L.scale)
    end
end

function chrome.draw_footer(opts)
    opts = opts or {}
    local L = layout.get()
    local W, H = love.graphics.getWidth(), love.graphics.getHeight()
    local th = opts.theme or {}
    local hints = opts.hints or {}
    local accent   = th.accent    or { 0.3, 0.8, 0.9 }
    local text_col = th.text      or { 0.9, 0.9, 0.9 }
    local dim_col  = th.dim       or { 0.5, 0.5, 0.5 }
    local footer_bg= th.footer_bg or { 0.03, 0.04, 0.06 }
    local bg_col   = th.bg        or { 0.02, 0.03, 0.05 }

    local y0 = H - L.footer_h
    love.graphics.setColor(footer_bg[1], footer_bg[2], footer_bg[3], 1)
    love.graphics.rectangle("fill", 0, y0, W, L.footer_h)
    pcall(effects.gradient_v, 0, y0, W, L.footer_h, bg_col, footer_bg)
    love.graphics.setColor(accent[1], accent[2], accent[3], 1)
    love.graphics.rectangle("fill", 0, y0, W, 2)

    local f = font.regular(L.font_hint) or love.graphics.newFont(L.font_hint)
    love.graphics.setFont(f)
    local x = math.floor(14 * L.scale)
    local yy = y0 + math.floor((L.footer_h - f:getHeight()) / 2)
    local isz = math.floor(L.icon_size * 0.72)

    for _, hint in ipairs(hints) do
        if hint.icon then
            pcall(icon.draw, hint.icon, x, yy + math.floor((f:getHeight() - isz)/2),
                  isz, accent, { alpha = 0.95 })
            x = x + isz + math.floor(5 * L.scale)
        end
        love.graphics.setColor(text_col[1], text_col[2], text_col[3], 0.9)
        love.graphics.print(hint.label or "", x, yy)
        x = x + f:getWidth(hint.label or "") + math.floor(16 * L.scale)
    end

    if opts.right_text then
        love.graphics.setColor(dim_col[1], dim_col[2], dim_col[3], 1)
        local tw = f:getWidth(opts.right_text)
        love.graphics.print(opts.right_text, W - tw - math.floor(14 * L.scale), yy)
    end
end

return chrome
