local font    = require("core.font")
local icon    = require("core.icon")
local effects = require("core.effects")

local W = {}

-- Horizontal stat bar
function W.stat_bar(x, y, w, h, label, value_text, pct, color, alpha)
    alpha = alpha or 1
    local f_l = font.regular(11) or love.graphics.newFont(11)
    local f_v = font.bold(11) or love.graphics.newFont(11)

    love.graphics.setFont(f_l)
    love.graphics.setColor(0.70, 0.76, 0.82, alpha)
    love.graphics.print(label, x, y)

    if value_text then
        love.graphics.setFont(f_v)
        local tw = f_v:getWidth(value_text)
        love.graphics.setColor(color[1], color[2], color[3], alpha)
        love.graphics.print(value_text, x + w - tw, y - 1)
    end

    local bar_y = y + h - 5
    love.graphics.setColor(0.10, 0.10, 0.13, 0.95 * alpha)
    love.graphics.rectangle("fill", x, bar_y, w, 7, 3)
    local fill_w = w * math.max(0, math.min(100, pct or 0)) / 100
    if fill_w > 1 then
        love.graphics.setColor(color[1], color[2], color[3], alpha)
        love.graphics.rectangle("fill", x, bar_y, fill_w, 7, 3)
    end
    love.graphics.setColor(color[1], color[2], color[3], 0.35 * alpha)
    love.graphics.setLineWidth(1)
    love.graphics.rectangle("line", x, bar_y, w, 7, 3)
end

-- Status card (icon + title + subtitle + state)
function W.status_card(x, y, w, h, icon_key, title, subtitle, state_color, state_text, alpha)
    alpha = alpha or 1
    love.graphics.setColor(0.06, 0.07, 0.09, 0.92 * alpha)
    love.graphics.rectangle("fill", x, y, w, h, 6)
    love.graphics.setColor(state_color[1], state_color[2], state_color[3], 0.55 * alpha)
    love.graphics.setLineWidth(1.5)
    love.graphics.rectangle("line", x, y, w, h, 6)

    if icon_key then
        pcall(icon.draw, icon_key, x + 8, y + 8, 22, state_color, { alpha = alpha })
    end

    local f_t = font.bold(12) or love.graphics.newFont(12)
    love.graphics.setFont(f_t)
    love.graphics.setColor(0.95, 0.95, 0.95, alpha)
    love.graphics.print(title, x + 36, y + 7)

    if subtitle then
        local f_s = font.regular(10) or love.graphics.newFont(10)
        love.graphics.setFont(f_s)
        love.graphics.setColor(0.60, 0.66, 0.72, alpha)
        local sub = subtitle
        while sub and #sub > 3 and f_s:getWidth(sub) > w - 20 do
            sub = sub:sub(1, #sub - 4) .. "..."
        end
        love.graphics.print(sub or "", x + 8, y + h - 32)
    end

    if state_text then
        local f_s = font.bold(10) or love.graphics.newFont(10)
        love.graphics.setFont(f_s)
        local tw = f_s:getWidth(state_text)
        love.graphics.setColor(state_color[1], state_color[2], state_color[3], alpha)
        love.graphics.print(state_text, x + w - tw - 8, y + h - 14)
    end
end

-- Info row (label left, value right)
function W.info_row(x, y, w, label, value, color, alpha)
    alpha = alpha or 1
    local f_l = font.regular(10) or love.graphics.newFont(10)
    local f_v = font.bold(11) or love.graphics.newFont(11)
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

-- Circular gauge
function W.gauge(cx, cy, r, pct, label, color, alpha)
    alpha = alpha or 1
    love.graphics.setColor(0.10, 0.10, 0.13, 0.9 * alpha)
    love.graphics.setLineWidth(6)
    love.graphics.circle("line", cx, cy, r)

    local angle = math.rad(360 * math.max(0, math.min(100, pct or 0)) / 100)
    if angle > 0.02 then
        love.graphics.setColor(color[1], color[2], color[3], alpha)
        love.graphics.arc("line", "open", cx, cy, r, -math.pi/2, -math.pi/2 + angle)
    end

    local f_big = font.bold(16) or love.graphics.newFont(16)
    love.graphics.setFont(f_big)
    local txt = string.format("%d%%", math.floor(pct or 0))
    local tw = f_big:getWidth(txt)
    love.graphics.setColor(1, 1, 1, alpha)
    love.graphics.print(txt, cx - tw/2, cy - 9)

    if label then
        local f_l = font.regular(9) or love.graphics.newFont(9)
        love.graphics.setFont(f_l)
        local lw = f_l:getWidth(label)
        love.graphics.setColor(0.60, 0.66, 0.72, alpha)
        love.graphics.print(label, cx - lw/2, cy + 4)
    end
end

-- Menu row (selectable)
function W.menu_row(x, y, w, h, badge, label, desc, selected, theme, node_color, alpha)
    alpha = alpha or 1
    if selected then
        pcall(effects.glow, x + w/2, y + h/2, w/2, node_color, 0.35, 3)
        love.graphics.setColor(node_color[1], node_color[2], node_color[3], 0.17 * alpha)
        love.graphics.rectangle("fill", x, y, w, h, 5)
        love.graphics.setColor(node_color[1], node_color[2], node_color[3], alpha)
        love.graphics.setLineWidth(2)
        love.graphics.rectangle("line", x, y, w, h, 5)
    end

    local bs = math.min(24, h - 8)
    local bx = x + 6
    local by = y + (h - bs)/2
    local bc = selected and node_color or { 0.5, 0.55, 0.60 }
    love.graphics.setColor(bc[1]*0.18, bc[2]*0.18, bc[3]*0.18, alpha)
    love.graphics.rectangle("fill", bx, by, bs, bs, 3)
    love.graphics.setColor(bc[1], bc[2], bc[3], alpha)
    love.graphics.setLineWidth(1)
    love.graphics.rectangle("line", bx, by, bs, bs, 3)

    local f_b = font.bold(12) or love.graphics.newFont(12)
    love.graphics.setFont(f_b)
    local tw = f_b:getWidth(badge)
    love.graphics.setColor(bc[1], bc[2], bc[3], alpha)
    love.graphics.print(badge, bx + (bs - tw)/2, by + (bs - f_b:getHeight())/2)

    local f_l = font.bold(13) or love.graphics.newFont(13)
    love.graphics.setFont(f_l)
    local col = selected and theme.text or theme.dim
    love.graphics.setColor(col[1], col[2], col[3], alpha)
    love.graphics.print(label, x + bs + 14, y + 3)

    if desc then
        local f_d = font.regular(10) or love.graphics.newFont(10)
        love.graphics.setFont(f_d)
        love.graphics.setColor(theme.dim[1]*0.8, theme.dim[2]*0.8, theme.dim[3]*0.8, 0.9 * alpha)
        love.graphics.print(desc, x + bs + 14, y + h - 13)
    end
end

return W
