-- Top overlay carousel: press M to toggle. Auto-rotates every 2.5s.
local notif = {}
notif.items = {}
notif.active = false
notif.carousel_i = 1
notif.last_rotate = 0
notif.MAX = 10

function notif.add(title, body, level)
    level = level or "info"
    table.insert(notif.items, {
        title = title or "",
        body = body or "",
        level = level,
        ts = os.time(),
    })
    while #notif.items > notif.MAX do
        table.remove(notif.items, 1)
    end
    -- auto-open if error
    if level == "error" or level == "warn" then
        notif.active = true
        notif.carousel_i = #notif.items
        notif.last_rotate = love.timer.getTime()
    end
end

function notif.toggle()
    notif.active = not notif.active
    notif.last_rotate = love.timer.getTime()
    notif.carousel_i = math.max(1, #notif.items)
end

function notif.update()
    if notif.active and #notif.items > 0 then
        local now = love.timer.getTime()
        if now - notif.last_rotate > 2.5 then
            notif.carousel_i = notif.carousel_i % #notif.items + 1
            notif.last_rotate = now
        end
    end
end

local LEVEL_COLORS = {
    info    = { 0.30, 0.80, 1.00 },
    ok      = { 0.40, 0.90, 0.50 },
    warn    = { 1.00, 0.70, 0.20 },
    error   = { 1.00, 0.30, 0.30 },
}

function notif.draw(theme, header_h)
    if not notif.active then return end
    local W = love.graphics.getWidth()
    local H = love.graphics.getHeight()
    if #notif.items == 0 then
        -- empty state
        local top = header_h + 4
        love.graphics.setColor(0.05, 0.05, 0.08, 0.92)
        love.graphics.rectangle("fill", 10, top, W - 20, 44, 6)
        love.graphics.setColor(0.3, 0.3, 0.4, 0.9)
        love.graphics.setLineWidth(1.5)
        love.graphics.rectangle("line", 10, top, W - 20, 44, 6)
        love.graphics.setColor(0.6, 0.6, 0.7, 1)
        love.graphics.print("No notifications · press M to hide", 22, top + 16)
        return
    end

    local n = notif.items[notif.carousel_i]
    local color = LEVEL_COLORS[n.level] or LEVEL_COLORS.info
    local top = header_h + 4
    local h = 60

    -- Slide-in animation
    local intro = math.min(1, (love.timer.getTime() - notif.last_rotate) / 0.25 + 1)
    local y = top - (1 - math.min(1, intro)) * h

    love.graphics.setColor(0.05, 0.05, 0.08, 0.92)
    love.graphics.rectangle("fill", 10, y, W - 20, h, 6)
    love.graphics.setColor(color[1], color[2], color[3], 0.95)
    love.graphics.setLineWidth(1.5)
    love.graphics.rectangle("line", 10, y, W - 20, h, 6)

    -- Level dot + title
    love.graphics.setColor(color[1], color[2], color[3], 1)
    love.graphics.circle("fill", 24, y + 18, 4)
    love.graphics.setColor(1, 1, 1, 1)
    love.graphics.print(n.title, 34, y + 10)

    -- Body
    love.graphics.setColor(0.8, 0.85, 0.9, 0.9)
    local body_text = n.body
    if #body_text > 90 then body_text = body_text:sub(1, 87) .. "..." end
    love.graphics.print(body_text, 22, y + 32)

    -- Page indicator
    local pag = string.format("%d/%d", notif.carousel_i, #notif.items)
    love.graphics.setColor(0.5, 0.55, 0.6, 0.9)
    local tw = love.graphics.getFont():getWidth(pag)
    love.graphics.print(pag, W - tw - 22, y + h - 20)
end

return notif
