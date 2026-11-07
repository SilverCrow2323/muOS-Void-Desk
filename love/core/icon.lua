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
    elseif name == "folder" then
        -- folder
        love.graphics.polygon("fill",
            x + 3 * u, y + 8 * u,
            x + 10 * u, y + 8 * u,
            x + 12 * u, y + 10 * u,
            x + 21 * u, y + 10 * u,
            x + 21 * u, y + 19 * u,
            x + 3 * u, y + 19 * u)
        love.graphics.setColor(1, 1, 1, 0.3 * a)
        love.graphics.rectangle("fill", x + 5 * u, y + 13 * u, 14 * u, 1.5 * u)
        C(col, a)

    elseif name == "calc" then
        love.graphics.rectangle("line", x + 5 * u, y + 3 * u, 14 * u, 18 * u, 2 * u)
        love.graphics.rectangle("fill", x + 7 * u, y + 5 * u, 10 * u, 3 * u)
        for row = 0, 2 do
            for c_col = 0, 2 do
                love.graphics.circle("fill",
                    x + (7 + c_col * 3.5) * u,
                    y + (11 + row * 3) * u, 1 * u)
            end
        end

    elseif name == "cal" then
        love.graphics.rectangle("line", x + 3 * u, y + 5 * u, 18 * u, 15 * u, 1 * u)
        love.graphics.rectangle("fill", x + 3 * u, y + 5 * u, 18 * u, 3 * u)
        love.graphics.setColor(0.1, 0.1, 0.15, a)
        for i = 0, 2 do
            love.graphics.rectangle("fill", x + (5 + i * 5) * u, y + (10 + 0) * u, 3 * u, 3 * u)
        end
        C(col, a)
        for i = 0, 2 do
            love.graphics.rectangle("line", x + (10 + i * 4) * u, y + 2 * u, 1.5 * u, 4 * u)
        end

    elseif name == "text" then
        love.graphics.rectangle("line", x + 5 * u, y + 3 * u, 14 * u, 18 * u, 1 * u)
        for row = 0, 3 do
            love.graphics.line(x + 7 * u, y + (8 + row * 3) * u,
                               x + (row == 3 and 13 or 17) * u, y + (8 + row * 3) * u)
        end

    elseif name == "terminal" then
        love.graphics.rectangle("line", x + 3 * u, y + 5 * u, 18 * u, 14 * u, 1 * u)
        love.graphics.line(x + 6 * u, y + 9 * u, x + 9 * u, y + 12 * u)
        love.graphics.line(x + 9 * u, y + 12 * u, x + 6 * u, y + 15 * u)
        love.graphics.line(x + 11 * u, y + 15 * u, x + 15 * u, y + 15 * u)

    elseif name == "globe" then
        love.graphics.circle("line", cx, cy, 9 * u)
        love.graphics.ellipse("line", cx, cy, 3.5 * u, 9 * u)
        love.graphics.line(x + 3 * u, cy, x + 21 * u, cy)
        love.graphics.line(x + 5 * u, y + 7 * u, x + 19 * u, y + 7 * u)
        love.graphics.line(x + 5 * u, y + 17 * u, x + 19 * u, y + 17 * u)

    elseif name == "sun" then
        love.graphics.circle("line", cx, cy, 5 * u)
        for i = 0, 7 do
            local ang = i * math.pi / 4
            love.graphics.line(
                cx + math.cos(ang) * 7 * u, cy + math.sin(ang) * 7 * u,
                cx + math.cos(ang) * 10 * u, cy + math.sin(ang) * 10 * u)
        end

    elseif name == "gear" then
        love.graphics.circle("line", cx, cy, 4 * u)
        for i = 0, 7 do
            local ang = i * math.pi / 4
            love.graphics.line(
                cx + math.cos(ang) * 5 * u, cy + math.sin(ang) * 5 * u,
                cx + math.cos(ang) * 9 * u, cy + math.sin(ang) * 9 * u)
        end

    elseif name == "star" then
        local pts = {}
        for i = 0, 9 do
            local ang = -math.pi / 2 + i * math.pi / 5
            local r = (i % 2 == 0) and 9 or 3.8
            table.insert(pts, cx + math.cos(ang) * r * u)
            table.insert(pts, cy + math.sin(ang) * r * u)
        end
        love.graphics.polygon("fill", pts)

    elseif name == "video" then
        love.graphics.rectangle("line", x + 3 * u, y + 5 * u, 18 * u, 14 * u, 1 * u)
        love.graphics.polygon("fill",
            x + 10 * u, y + 9 * u,
            x + 10 * u, y + 15 * u,
            x + 15 * u, y + 12 * u)

    elseif name == "music" then
        love.graphics.circle("fill", x + 7 * u, y + 17 * u, 2.5 * u)
        love.graphics.circle("fill", x + 17 * u, y + 15 * u, 2.5 * u)
        love.graphics.line(x + 9.5 * u, y + 17 * u, x + 9.5 * u, y + 6 * u)
        love.graphics.line(x + 19.5 * u, y + 15 * u, x + 19.5 * u, y + 4 * u)
        love.graphics.line(x + 9.5 * u, y + 6 * u, x + 19.5 * u, y + 4 * u)

    elseif name == "disk" then
        love.graphics.rectangle("line", x + 4 * u, y + 8 * u, 16 * u, 10 * u, 2 * u)
        love.graphics.circle("line", x + 9 * u, y + 13 * u, 2 * u)
        love.graphics.line(x + 14 * u, y + 13 * u, x + 18 * u, y + 13 * u)

    elseif name == "book" then
        love.graphics.polygon("line",
            x + 4 * u, y + 5 * u,
            x + 12 * u, y + 3 * u,
            x + 20 * u, y + 5 * u,
            x + 20 * u, y + 20 * u,
            x + 12 * u, y + 18 * u,
            x + 4 * u, y + 20 * u)
        love.graphics.line(x + 12 * u, y + 3 * u, x + 12 * u, y + 18 * u)

    elseif name == "power" then
        love.graphics.arc("line", "open", cx, cy, 8 * u, -math.pi * 0.7, math.pi * 0.7)
        love.graphics.line(cx, y + 3 * u, cx, cy)

    elseif name == "chevron" then
        love.graphics.line(x + 9 * u, y + 7 * u, x + 15 * u, y + 12 * u)
        love.graphics.line(x + 15 * u, y + 12 * u, x + 9 * u, y + 17 * u)

    elseif name == "back" then
        love.graphics.line(x + 15 * u, y + 7 * u, x + 9 * u, y + 12 * u)
        love.graphics.line(x + 9 * u, y + 12 * u, x + 15 * u, y + 17 * u)

    elseif name == "arrow_up" then
        love.graphics.line(x + 12 * u, y + 5 * u, x + 12 * u, y + 19 * u)
        love.graphics.line(x + 6 * u, y + 11 * u, x + 12 * u, y + 5 * u)
        love.graphics.line(x + 18 * u, y + 11 * u, x + 12 * u, y + 5 * u)

    elseif name == "arrow_down" then
        love.graphics.line(x + 12 * u, y + 5 * u, x + 12 * u, y + 19 * u)
        love.graphics.line(x + 6 * u, y + 13 * u, x + 12 * u, y + 19 * u)
        love.graphics.line(x + 18 * u, y + 13 * u, x + 12 * u, y + 19 * u)

    elseif name == "play" then
        love.graphics.polygon("fill",
            x + 7 * u, y + 5 * u,
            x + 7 * u, y + 19 * u,
            x + 18 * u, y + 12 * u)

    elseif name == "pause" then
        love.graphics.rectangle("fill", x + 7 * u, y + 5 * u, 3.5 * u, 14 * u)
        love.graphics.rectangle("fill", x + 14 * u, y + 5 * u, 3.5 * u, 14 * u)

    elseif name == "refresh" then
        love.graphics.arc("line", "open", cx, cy, 7 * u, -math.pi * 0.8, math.pi * 0.8)
        love.graphics.polygon("fill",
            x + 18 * u, y + 5 * u,
            x + 18 * u, y + 11 * u,
            x + 13 * u, y + 8 * u)

    elseif name == "search" then
        love.graphics.circle("line", x + 10 * u, y + 10 * u, 6 * u)
        love.graphics.line(x + 14 * u, y + 14 * u, x + 19 * u, y + 19 * u)

    elseif name == "check" then
        love.graphics.line(x + 5 * u, y + 12 * u, x + 10 * u, y + 17 * u)
        love.graphics.line(x + 10 * u, y + 17 * u, x + 19 * u, y + 7 * u)

    elseif name == "warn" then
        love.graphics.polygon("line",
            x + 12 * u, y + 4 * u,
            x + 20 * u, y + 19 * u,
            x + 4 * u, y + 19 * u)
        love.graphics.line(x + 12 * u, y + 9 * u, x + 12 * u, y + 14 * u)
        love.graphics.circle("fill", x + 12 * u, y + 16.5 * u, 1 * u)

    elseif name == "info" then
        love.graphics.circle("line", cx, cy, 9 * u)
        love.graphics.circle("fill", cx, y + 7 * u, 1 * u)
        love.graphics.line(cx, y + 11 * u, cx, y + 17 * u)

    elseif name == "code" then
        love.graphics.line(x + 8 * u, y + 7 * u, x + 4 * u, y + 12 * u)
        love.graphics.line(x + 4 * u, y + 12 * u, x + 8 * u, y + 17 * u)
        love.graphics.line(x + 16 * u, y + 7 * u, x + 20 * u, y + 12 * u)
        love.graphics.line(x + 20 * u, y + 12 * u, x + 16 * u, y + 17 * u)
        love.graphics.line(x + 13 * u, y + 6 * u, x + 11 * u, y + 18 * u)

    elseif name == "gamepad" then
        love.graphics.rectangle("line", x + 2 * u, y + 9 * u, 20 * u, 8 * u, 4 * u)
        love.graphics.line(x + 6 * u, y + 13 * u, x + 9 * u, y + 13 * u)
        love.graphics.line(x + 7.5 * u, y + 11.5 * u, x + 7.5 * u, y + 14.5 * u)
        love.graphics.circle("fill", x + 16 * u, y + 12 * u, 1 * u)
        love.graphics.circle("fill", x + 18.5 * u, y + 14 * u, 1 * u)

    elseif name == "keyboard" then
        love.graphics.rectangle("line", x + 2 * u, y + 7 * u, 20 * u, 11 * u, 1 * u)
        for i = 0, 4 do
            love.graphics.circle("fill", x + (5 + i * 3.5) * u, y + 11 * u, 1 * u)
        end
        love.graphics.line(x + 6 * u, y + 15 * u, x + 18 * u, y + 15 * u)

    elseif name == "download" then
        love.graphics.line(x + 12 * u, y + 4 * u, x + 12 * u, y + 14 * u)
        love.graphics.line(x + 6 * u, y + 10 * u, x + 12 * u, y + 15 * u)
        love.graphics.line(x + 18 * u, y + 10 * u, x + 12 * u, y + 15 * u)
        love.graphics.line(x + 4 * u, y + 19 * u, x + 20 * u, y + 19 * u)

    elseif name == "upload" then
        love.graphics.line(x + 12 * u, y + 15 * u, x + 12 * u, y + 4 * u)
        love.graphics.line(x + 6 * u, y + 9 * u, x + 12 * u, y + 4 * u)
        love.graphics.line(x + 18 * u, y + 9 * u, x + 12 * u, y + 4 * u)
        love.graphics.line(x + 4 * u, y + 19 * u, x + 20 * u, y + 19 * u)

    elseif name == "trash" then
        love.graphics.line(x + 5 * u, y + 6 * u, x + 19 * u, y + 6 * u)
        love.graphics.line(x + 9 * u, y + 4 * u, x + 15 * u, y + 4 * u)
        love.graphics.rectangle("line", x + 6 * u, y + 7 * u, 12 * u, 13 * u, 1 * u)
        love.graphics.line(x + 10 * u, y + 10 * u, x + 10 * u, y + 17 * u)
        love.graphics.line(x + 14 * u, y + 10 * u, x + 14 * u, y + 17 * u)

    elseif name == "plus" then
        love.graphics.line(cx, y + 6 * u, cx, y + 18 * u)
        love.graphics.line(x + 6 * u, cy, x + 18 * u, cy)

    elseif name == "minus" then
        love.graphics.line(x + 6 * u, cy, x + 18 * u, cy)

    elseif name == "list" then
        for i = 0, 2 do
            love.graphics.circle("fill", x + 6 * u, y + (8 + i * 4) * u, 1 * u)
            love.graphics.line(x + 9 * u, y + (8 + i * 4) * u,
                               x + 19 * u, y + (8 + i * 4) * u)
        end

    elseif name == "grid" then
        for row = 0, 2 do
            for c = 0, 2 do
                love.graphics.rectangle("line",
                    x + (4 + c * 6) * u,
                    y + (4 + row * 6) * u,
                    5 * u, 5 * u)
            end
        end

    elseif name == "eye" then
        love.graphics.arc("line", "open", cx, cy, 8 * u, math.pi, 2 * math.pi)
        love.graphics.arc("line", "open", cx, cy, 8 * u, 0, math.pi)
        love.graphics.circle("line", cx, cy, 3 * u)

    elseif name == "lock" then
        love.graphics.rectangle("line", x + 6 * u, y + 11 * u, 12 * u, 9 * u, 1 * u)
        love.graphics.arc("line", "open", cx, y + 11 * u, 4 * u, math.pi, 2 * math.pi)
        love.graphics.circle("fill", cx, y + 15 * u, 1 * u)

    elseif name == "link" then
        love.graphics.arc("line", "open", x + 8 * u, cy, 3 * u, -math.pi * 0.5, math.pi * 0.5)
        love.graphics.arc("line", "open", x + 16 * u, cy, 3 * u, math.pi * 0.5, math.pi * 1.5)
        love.graphics.line(x + 10 * u, cy, x + 14 * u, cy)

    elseif name == "uplink" then
        love.graphics.line(x + 12 * u, y + 20 * u, x + 12 * u, y + 8 * u)
        love.graphics.line(x + 6 * u, y + 20 * u, x + 12 * u, y + 12 * u)
        love.graphics.line(x + 18 * u, y + 20 * u, x + 12 * u, y + 12 * u)
        love.graphics.circle("fill", x + 12 * u, y + 7 * u, 2 * u)
        love.graphics.arc("line", "open", x + 12 * u, y + 7 * u, 5 * u, -math.pi * 0.7, -math.pi * 0.3)
        love.graphics.arc("line", "open", x + 12 * u, y + 7 * u, 8 * u, -math.pi * 0.75, -math.pi * 0.25)

    elseif name == "image" then
        love.graphics.rectangle("line", x + 3 * u, y + 5 * u, 18 * u, 14 * u, 1 * u)
        love.graphics.circle("fill", x + 8 * u, y + 10 * u, 1.5 * u)
        love.graphics.polygon("fill",
            x + 5 * u, y + 17 * u,
            x + 11 * u, y + 11 * u,
            x + 17 * u, y + 17 * u)

    end

    love.graphics.setLineWidth(1)
    love.graphics.setColor(1, 1, 1, 1)
end

return icon
