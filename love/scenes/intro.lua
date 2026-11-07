local sm    = require("core.scene_manager")
local theme = require("theme.loader")
local intro = {}
local t = 0
local dur = 2.0

function intro.enter(args)
    t = 0
    dur = (args and args.duration) or 2.0
end

function intro.update(dt)
    t = t + dt
    if t >= dur then
        sm.switch("nexus", {})
    end
end

function intro.draw()
    local W, H = love.graphics.getDimensions()
    local th = theme.get()

    love.graphics.clear(th.bg[1], th.bg[2], th.bg[3])

    -- rings concentriche
    love.graphics.setLineWidth(2)
    for i = 1, 12 do
        local r = (i / 12) * 300 * (1 + 0.04 * math.sin(t * 3 + i))
        local a = 0.5 - i * 0.03
        if a > 0 then
            love.graphics.setColor(th.accent[1], th.accent[2], th.accent[3], a)
            love.graphics.circle("line", W/2, H/2, r)
        end
    end

    -- logo
    local fade = math.min(1, t * 1.5)
    love.graphics.setColor(th.text[1], th.text[2], th.text[3], fade)
    local font = love.graphics.newFont(32)
    love.graphics.setFont(font)
    local title = "VOID-DESK"
    local tw = font:getWidth(title)
    love.graphics.print(title, (W - tw)/2, H/2 - 20)

    -- progress bar
    local pct = math.min(1, t / dur)
    love.graphics.setColor(th.accent[1], th.accent[2], th.accent[3], 0.8)
    love.graphics.rectangle("fill", W/2 - 100, H/2 + 40, 200 * pct, 3)
end

function intro.keypressed(key)
    if key == "escape" or key == "return" then
        sm.switch("nexus", {})
    end
end

return intro
