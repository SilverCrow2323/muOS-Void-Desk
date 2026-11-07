-- Procedural vector icons (no external assets).
-- draw(name, x, y, size, color, opts)
--   opts = { alpha=1, fill=0..1 (battery), charging=bool }
local icon = {}

local function C(c, a) love.graphics.setColor(c[1], c[2], c[3], a or 1) end

function icon.draw(name, x, y, sz, col, opts)
    opts = opts or {}
    local a = opts.alpha or 1
    local u = sz / 24.0
    local lw = math.max(1, math.floor(1.6 * u + 0.5))
    local cx, cy = x + 12 * u, y + 12 * u
    C(col, a)
    love.graphics.setLineWidth(lw)

    if name == "wifi" then
        love.graphics.circle("fill", cx, cy + 6 * u, 1.6 * u)
        for i, r in ipairs({6, 10, 14}) do
            love.graphics.arc("line", "open", cx, cy + 6 * u, r * u,
                -math.pi * 0.85, -math.pi * 0.15)
        end

    elseif name == "signal" then
        for i = 0, 3 do
            local h = (i + 1) * 4 * u
            love.graphics.rectangle("fill", x + (4 + i * 4) * u,
                y + 18 * u - h, 2 * u, h)
        end

    elseif name == "bluetooth" then
        love.graphics.line(
            cx, y + 3 * u,
            x + 17 * u, y + 8 * u,
            x + 7 * u,  y + 16 * u,
            x + 17 * u, y + 16 * u,
            cx, y + 21 * u,
            cx, y + 3 * u)

    elseif name == "battery" then
        love.graphics.rectangle("line", x + 2 * u, y + 6 * u, 18 * u, 12 * u, 2 * u)
        love.graphics.rectangle("fill", x + 20 * u, y + 10 * u, 2.5 * u, 4 * u)
        local lvl = opts.fill or 0
        if lvl > 0 then
            local inner_w = 16 * u * lvl
            C({0.45, 0.90, 0.50}, a)
            love.graphics.rectangle("fill", x + 3 * u, y + 7 * u, inner_w, 10 * u, 1 * u)
            C(col, a)
        end
        if opts.charging then
            love.graphics.polygon("fill",
                x + 11 * u, y + 7 * u,
                x + 8 * u,  y + 12 * u,
                x + 11 * u, y + 12 * u,
                x + 9 * u,  y + 17 * u,
                x + 14 * u, y + 11 * u,
                x + 11 * u, y + 11 * u)
        end

    elseif name == "volume" then
        love.graphics.polygon("fill",
            x + 3 * u,  y + 9 * u,
            x + 7 * u,  y + 9 * u,
            x + 11 * u, y + 5 * u,
            x + 11 * u, y + 19 * u,
            x + 7 * u,  y + 15 * u,
            x + 3 * u,  y + 15 * u)
        love.graphics.arc("line", "open", x + 11 * u, cy, 5 * u, -math.pi/3, math.pi/3)
        love.graphics.arc("line", "open", x + 11 * u, cy, 9 * u, -math.pi/3, math.pi/3)

    elseif name == "clock" then
        love.graphics.circle("line", cx, cy, 9 * u)
        love.graphics.line(cx, cy, cx, y + 6 * u)
        love.graphics.line(cx, cy, x + 17 * u, cy)

    elseif name == "dpad" then
        local w = 4 * u
        love.graphics.polygon("fill",
            cx - w,   y + 4 * u,   cx + w,   y + 4 * u,
            cx + w,   cy - w,      x + 20 * u, cy - w,
            x + 20 * u, cy + w,    cx + w,   cy + w,
            cx + w,   y + 20 * u,  cx - w,   y + 20 * u,
            cx - w,   cy + w,      x + 4 * u,  cy + w,
            x + 4 * u,  cy - w,    cx - w,   cy - w)

    elseif name == "btn_a" or name == "btn_b"
        or name == "btn_x" or name == "btn_y" then
        local label = string.upper(name:sub(5, 5))
        love.graphics.circle("line", cx, cy, 9 * u)
        local fnt = love.graphics.getFont()
        local tw = fnt:getWidth(label)
        love.graphics.print(label, cx - tw/2, cy - fnt:getHeight()/2)

    elseif name == "menu" then
        for i = 0, 2 do
            love.graphics.rectangle("fill", x + 5 * u, y + (9 + i * 3) * u, 14 * u, 1.5 * u)
        end

    elseif name == "start" or name == "select" then
        love.graphics.rectangle("line", x + 6 * u, y + 10 * u, 12 * u, 4 * u, 2 * u)

    elseif name == "l1" or name == "r1" then
        local dir = (name == "l1") and 1 or -1
        local sx = (dir == 1) and x + 2 * u or x + 22 * u
        love.graphics.polygon("line",
            sx,                 y + 8 * u,
            sx + dir * 6 * u,   y + 8 * u,
            sx + dir * 6 * u,   y + 14 * u,
            sx + dir * 12 * u,  y + 14 * u,
            sx + dir * 12 * u,  y + 18 * u,
            sx,                 y + 18 * u)

    elseif name == "usb" then
        love.graphics.line(cx, y + 3 * u, cx, y + 20 * u)
        love.graphics.circle("fill", cx, y + 3 * u, 1.5 * u)
        love.graphics.rectangle("fill", x + 9 * u, y + 20 * u, 6 * u, 2 * u)
    end

    love.graphics.setLineWidth(1)
    love.graphics.setColor(1, 1, 1, 1)
end

return icon
