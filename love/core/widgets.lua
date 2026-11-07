local font    = require("core.font")
local icon    = require("core.icon")
local effects = require("core.effects")
local layout  = require("core.layout")

local W = {}

function W.stat_bar(x, y, w, h, label, value_text, pct, color, alpha)
    alpha = alpha or 1
    local L = layout.get()
    local f_l = font.regular(L.font_status) or love.graphics.newFont(L.font_status)
    local f_v = font.bold(L.font_status) or love.graphics.newFont(L.font_status)
    love.graphics.setFont(f_l)
    love.graphics.setColor(0.70, 0.76, 0.82, alpha)
    love.graphics.print(label, x, y)
    if value_text then
        love.graphics.setFont(f_v)
        local tw = f_v:getWidth(value_text)
        love.graphics.setColor(color[1], color[2], color[3], alpha)
        love.graphics.print(value_text, x + w - tw, y - 1)
    end
    local bar_y = y + h - math.floor(7 * L.scale)
    local bar_h = math.floor(7 * L.scale)
    love.graphics.setColor(0.10, 0.10, 0.13, 0.95 * alpha)
    love.graphics.rectangle("fill", x, bar_y, w, bar_h, 3)
    local fill_w = w * math.max(0, math.min(100, pct or 0)) / 100
    if fill_w > 1 then
        love.graphics.setColor(color[1], color[2], color[3], alpha)
        love.graphics.rectangle("fill", x, bar_y, fill_w, bar_h, 3)
    end
    love.graphics.setColor(color[1], color[2], color[3], 0.35 * alpha)
    love.graphics.setLineWidth(1)
    love.graphics.rectangle("line", x, bar_y, w, bar_h, 3)
end

function W.status_card(x, y, w, h, icon_key, title, subtitle, state_color, state_text, alpha)
    alpha = alpha or 1
    local L = layout.get()
    love.graphics.setColor(0.06, 0.07, 0.09, 0.92 * alpha)
    love.graphics.rectangle("fill", x, y, w, h, 6)
    love.graphics.setColor(state_color[1], state_color[2], state_color[3], 0.55 * alpha)
    love.graphics.setLineWidth(math.max(1, math.floor(1.5 * L.scale)))
    love.graphics.rectangle("line", x, y, w, h, 6)
    local isz = math.floor(L.icon_size * 0.85)
    if icon_key then
        pcall(icon.draw, icon_key, x + math.floor(8 * L.scale),
              y + math.floor((h - isz)/2 - 6 * L.scale), isz, state_color,
              { alpha = alpha })
    end
    local f_t = font.bold(L.font_label) or love.graphics.newFont(L.font_label)
    love.graphics.setFont(f_t)
    love.graphics.setColor(0.95, 0.95, 0.95, alpha)
    love.graphics.print(title, x + isz + math.floor(14 * L.scale),
                       y + math.floor(6 * L.scale))
    if subtitle then
        local f_s = font.regular(L.font_desc) or love.graphics.newFont(L.font_desc)
        love.graphics.setFont(f_s)
        love.graphics.setColor(0.60, 0.66, 0.72, alpha)
        local sub = subtitle
        while sub and #sub > 3 and f_s:getWidth(sub) > w - math.floor(20 * L.scale) do
            sub = sub:sub(1, #sub - 4) .. "..."
        end
        love.graphics.print(sub or "", x + math.floor(10 * L.scale),
                           y + h - f_s:getHeight() - math.floor(8 * L.scale))
    end
    if state_text then
        local f_s = font.bold(L.font_tiny + 1) or love.graphics.newFont(L.font_tiny + 1)
        love.graphics.setFont(f_s)
        local tw = f_s:getWidth(state_text)
        love.graphics.setColor(state_color[1], state_color[2], state_color[3], alpha)
        love.graphics.print(state_text, x + w - tw - math.floor(10 * L.scale),
                           y + h - f_s:getHeight() - math.floor(6 * L.scale))
    end
end

function W.info_row(x, y, w, label, value, color, alpha)
    alpha = alpha or 1
    local L = layout.get()
    local f_l = font.regular(L.font_desc) or love.graphics.newFont(L.font_desc)
    local f_v = font.bold(L.font_status) or love.graphics.newFont(L.font_status)
    love.graphics.setFont(f_l)
    love.graphics.setColor(0.55, 0.60, 0.66, alpha)
    love.graphics.print(label, x, y)
    love.graphics.setFont(f_v)
    local tw = f_v:getWidth(value or "—")
    love.graphics.setColor(
        (color and color[1]) or 0.92,
        (color and color[2]) or 0.92,
        (color and color[3]) or 0.92, alpha)
    love.graphics.print(value or "—", x + w - tw, y)
end

function W.gauge(cx, cy, r, pct, label, color, alpha)
    alpha = alpha or 1
    local L = layout.get()
    love.graphics.setColor(0.10, 0.10, 0.13, 0.9 * alpha)
    love.graphics.setLineWidth(math.max(3, math.floor(6 * L.scale)))
    love.graphics.circle("line", cx, cy, r)
    local angle = math.rad(360 * math.max(0, math.min(100, pct or 0)) / 100)
    if angle > 0.02 then
        love.graphics.setColor(color[1], color[2], color[3], alpha)
        love.graphics.arc("line", "open", cx, cy, r, -math.pi/2, -math.pi/2 + angle)
    end
    local f_big = font.bold(L.font_label) or love.graphics.newFont(L.font_label)
    love.graphics.setFont(f_big)
    local txt = string.format("%d%%", math.floor(pct or 0))
    local tw = f_big:getWidth(txt)
    love.graphics.setColor(1, 1, 1, alpha)
    love.graphics.print(txt, cx - tw/2, cy - f_big:getHeight()/2)
    if label then
        local f_l = font.regular(L.font_tiny) or love.graphics.newFont(L.font_tiny)
        love.graphics.setFont(f_l)
        local lw = f_l:getWidth(label)
        love.graphics.setColor(0.60, 0.66, 0.72, alpha)
        love.graphics.print(label, cx - lw/2, cy + f_big:getHeight()/2 - 2)
    end
end

function W.menu_row(x, y, w, h, a1, a2, a3, a4, a5, a6, a7)
    local opts
    if type(a1) == "table" then
        opts = a1
    else
        opts = { badge = a1, label = a2, desc = a3, selected = a4,
                 theme = a5, node_color = a6, alpha = a7 }
    end
    local L = layout.get()
    local selected = opts.selected or false
    local theme    = opts.theme or {}
    local nc       = opts.node_color or { 0.3, 0.8, 0.9 }
    local alpha    = opts.alpha or 1
    local th_text  = theme.text or { 0.9, 0.9, 0.9 }
    local th_dim   = theme.dim  or { 0.55, 0.60, 0.66 }

    if selected then
        pcall(effects.glow, x + w/2, y + h/2, w/2, nc, 0.35, 3)
        love.graphics.setColor(nc[1], nc[2], nc[3], 0.17 * alpha)
        love.graphics.rectangle("fill", x, y, w, h, 5)
        love.graphics.setColor(nc[1], nc[2], nc[3], alpha)
        love.graphics.setLineWidth(math.max(1, math.floor(2 * L.scale)))
        love.graphics.rectangle("line", x, y, w, h, 5)
    end

    local isz = math.floor(L.icon_size)
    local ix = x + math.floor(8 * L.scale)
    local iy = y + math.floor((h - isz) / 2)
    local icol = selected and nc or { 0.65, 0.70, 0.75 }
    if opts.icon then
        pcall(icon.draw, opts.icon, ix, iy, isz, icol, { alpha = alpha })
    elseif opts.badge then
        love.graphics.setColor(icol[1]*0.18, icol[2]*0.18, icol[3]*0.18, alpha)
        love.graphics.rectangle("fill", ix, iy, isz, isz, 4)
        love.graphics.setColor(icol[1], icol[2], icol[3], alpha)
        love.graphics.setLineWidth(1)
        love.graphics.rectangle("line", ix, iy, isz, isz, 4)
        local f_b = font.bold(L.font_label) or love.graphics.newFont(L.font_label)
        love.graphics.setFont(f_b)
        local tw = f_b:getWidth(opts.badge)
        love.graphics.setColor(icol[1], icol[2], icol[3], alpha)
        love.graphics.print(opts.badge, ix + (isz - tw)/2,
                           iy + (isz - f_b:getHeight())/2)
    end

    local text_x = ix + isz + math.floor(12 * L.scale)
    local text_w = w - (text_x - x) - math.floor(8 * L.scale)

    -- Right value area
    local f_val = font.bold(L.font_value) or love.graphics.newFont(L.font_value)
    local right_w = 0
    if opts.value then
        love.graphics.setFont(f_val)
        right_w = f_val:getWidth(tostring(opts.value)) + math.floor(8 * L.scale)
    end
    local chev_w = opts.chevron and math.floor(16 * L.scale) or 0
    text_w = text_w - right_w - chev_w

    -- Label
    local f_l = font.bold(L.font_label) or love.graphics.newFont(L.font_label)
    love.graphics.setFont(f_l)
    local label = opts.label or ""
    while #label > 3 and f_l:getWidth(label) > text_w do
        label = label:sub(1, #label - 4) .. "..."
    end
    local lcol = selected and th_text or th_dim
    love.graphics.setColor(lcol[1], lcol[2], lcol[3], alpha)
    local label_y = y + math.floor(4 * L.scale)
    love.graphics.print(label, text_x, label_y)

    -- Description
    if opts.desc and opts.desc ~= "" then
        local f_d = font.regular(L.font_desc) or love.graphics.newFont(L.font_desc)
        love.graphics.setFont(f_d)
        love.graphics.setColor(th_dim[1]*0.8, th_dim[2]*0.8, th_dim[3]*0.8,
                               0.9 * alpha)
        local desc = opts.desc
        while #desc > 3 and f_d:getWidth(desc) > text_w do
            desc = desc:sub(1, #desc - 4) .. "..."
        end
        local desc_y = y + h - f_d:getHeight() - math.floor(5 * L.scale)
        love.graphics.print(desc, text_x, desc_y)
    end

    -- Right value
    if opts.value then
        love.graphics.setFont(f_val)
        local vt = tostring(opts.value)
        local tw = f_val:getWidth(vt)
        local vx = x + w - math.floor(8 * L.scale) - chev_w - tw
        local vc = opts.value_color or nc
        love.graphics.setColor(vc[1], vc[2], vc[3], alpha)
        love.graphics.print(vt, vx, y + (h - f_val:getHeight())/2)
    end

    -- Chevron
    if opts.chevron then
        local cx = x + w - math.floor(12 * L.scale)
        local cy = y + h / 2
        love.graphics.setColor(nc[1], nc[2], nc[3], 0.6 * alpha)
        love.graphics.setLineWidth(math.max(1, math.floor(2 * L.scale)))
        local ch = math.floor(5 * L.scale)
        love.graphics.line(cx - ch, cy - ch, cx + 2, cy)
        love.graphics.line(cx + 2, cy, cx - ch, cy + ch)
    end
end

return W
