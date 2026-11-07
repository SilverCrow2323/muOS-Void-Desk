local font    = require("core.font")
local icon    = require("core.icon")
local effects = require("core.effects")

local W = {}

function W.stat_bar(x, y, w, h, label, value_text, pct, color, alpha)
    alpha = alpha or 1
    local f_l = font.regular(14) or love.graphics.newFont(11)
    local f_v = font.bold(14) or love.graphics.newFont(11)
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
    local f_t = font.bold(15) or love.graphics.newFont(12)
    love.graphics.setFont(f_t)
    love.graphics.setColor(0.95, 0.95, 0.95, alpha)
    love.graphics.print(title, x + 36, y + 7)
    if subtitle then
        local f_s = font.regular(13) or love.graphics.newFont(10)
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

function W.info_row(x, y, w, label, value, color, alpha)
    alpha = alpha or 1
    local f_l = font.regular(13) or love.graphics.newFont(10)
    local f_v = font.bold(14) or love.graphics.newFont(11)
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
        local f_l = font.regular(12) or love.graphics.newFont(9)
        love.graphics.setFont(f_l)
        local lw = f_l:getWidth(label)
        love.graphics.setColor(0.60, 0.66, 0.72, alpha)
        love.graphics.print(label, cx - lw/2, cy + 4)
    end
end

-- menu_row: supports BOTH old positional API and new table API
-- Old: menu_row(x, y, w, h, badge, label, desc, selected, theme, node_color, alpha)
-- New: menu_row(x, y, w, h, { icon=..., label=..., desc=..., value=..., ... })
function W.menu_row(x, y, w, h, a1, a2, a3, a4, a5, a6, a7)
    local opts
    if type(a1) == "table" then
        opts = a1
    else
        -- Legacy positional
        opts = {
            badge = a1, label = a2, desc = a3,
            selected = a4, theme = a5, node_color = a6, alpha = a7,
        }
    end

    local selected = opts.selected or false
    local theme    = opts.theme or {}
    local nc       = opts.node_color or { 0.3, 0.8, 0.9 }
    local alpha    = opts.alpha or 1
    local th_text  = theme.text or { 0.9, 0.9, 0.9 }
    local th_dim   = theme.dim  or { 0.55, 0.60, 0.66 }

    -- selection background
    if selected then
        pcall(effects.glow, x + w/2, y + h/2, w/2, nc, 0.35, 3)
        love.graphics.setColor(nc[1], nc[2], nc[3], 0.17 * alpha)
        love.graphics.rectangle("fill", x, y, w, h, 5)
        love.graphics.setColor(nc[1], nc[2], nc[3], alpha)
        love.graphics.setLineWidth(2)
        love.graphics.rectangle("line", x, y, w, h, 5)
    end

    -- icon (24x24, vertically centered)
    local isz = math.min(26, h - 8)
    local ix = x + 6
    local iy = y + (h - isz) / 2
    local icol = selected and nc or { 0.65, 0.70, 0.75 }
    if opts.icon then
        pcall(icon.draw, opts.icon, ix, iy, isz, icol, { alpha = alpha })
    elseif opts.badge then
        -- legacy: badge letter in a rounded square
        love.graphics.setColor(icol[1]*0.18, icol[2]*0.18, icol[3]*0.18, alpha)
        love.graphics.rectangle("fill", ix, iy, isz, isz, 3)
        love.graphics.setColor(icol[1], icol[2], icol[3], alpha)
        love.graphics.setLineWidth(1)
        love.graphics.rectangle("line", ix, iy, isz, isz, 3)
        local f_b = font.bold(15) or love.graphics.newFont(12)
        love.graphics.setFont(f_b)
        local tw = f_b:getWidth(opts.badge)
        love.graphics.setColor(icol[1], icol[2], icol[3], alpha)
        love.graphics.print(opts.badge, ix + (isz - tw)/2,
                            iy + (isz - f_b:getHeight())/2)
    end

    local text_x = ix + isz + 10
    local text_w = w - (text_x - x) - 8

    -- Right side: value + chevron
    local right_w = 0
    local f_val = font.bold(15) or love.graphics.newFont(12)
    local val_text = opts.value
    local val_color = opts.value_color or nc
    if val_text then
        love.graphics.setFont(f_val)
        right_w = f_val:getWidth(tostring(val_text)) + 8
    end
    local chev_w = 0
    if opts.chevron then
        chev_w = 16
    end
    if opts.chevron or val_text then
        text_w = text_w - right_w - chev_w
    end

    -- label (bold, top)
    local f_l = font.bold(16) or love.graphics.newFont(13)
    love.graphics.setFont(f_l)
    local label = opts.label or ""
    while #label > 3 and f_l:getWidth(label) > text_w do
        label = label:sub(1, #label - 4) .. "..."
    end
    local lcol = selected and th_text or th_dim
    love.graphics.setColor(lcol[1], lcol[2], lcol[3], alpha)
    love.graphics.print(label, text_x, y + 3)

    -- description (small, bottom)
    if opts.desc and opts.desc ~= "" then
        local f_d = font.regular(13) or love.graphics.newFont(10)
        love.graphics.setFont(f_d)
        love.graphics.setColor(th_dim[1]*0.8, th_dim[2]*0.8, th_dim[3]*0.8,
                               0.9 * alpha)
        local desc = opts.desc
        while #desc > 3 and f_d:getWidth(desc) > text_w do
            desc = desc:sub(1, #desc - 4) .. "..."
        end
        love.graphics.print(desc, text_x, y + h - 13)
    end

    -- right value
    if val_text then
        love.graphics.setFont(f_val)
        local vt = tostring(val_text)
        local tw = f_val:getWidth(vt)
        local vx = x + w - 8 - chev_w - tw
        love.graphics.setColor(val_color[1], val_color[2], val_color[3], alpha)
        love.graphics.print(vt, vx, y + (h - f_val:getHeight()) / 2)
    end

    -- chevron
    if opts.chevron then
        local cx = x + w - 8 - 8
        local cy = y + h / 2
        love.graphics.setColor(nc[1], nc[2], nc[3], 0.6 * alpha)
        love.graphics.setLineWidth(2)
        love.graphics.line(cx - 3, cy - 5, cx + 2, cy)
        love.graphics.line(cx + 2, cy, cx - 3, cy + 5)
    end
end

return W
