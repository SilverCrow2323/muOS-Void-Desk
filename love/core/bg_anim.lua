local bg = {}

local function embers(W, H, t, color, alpha)
    for i = 1, 18 do
        local ph = i * 1.3
        local x = (i * 71 + math.sin(t * 0.8 + ph) * 40) % W
        local y = H - ((t * 45 + i * 90) % (H + 60))
        love.graphics.setColor(color[1], color[2]*0.6, color[3]*0.3, alpha * 0.7)
        love.graphics.circle("fill", x, y, 1.5 + math.sin(t*3 + ph)*1.2)
    end
end

local function waveform(W, H, t, color, alpha)
    local mid = H * 0.55
    for i = 0, 40 do
        local x = i * (W / 40)
        local ph = i * 0.4 + t * 2
        local h = math.abs(math.sin(ph)) * 45 + 4
        local a = alpha * (0.20 + math.abs(math.sin(ph)) * 0.25)
        love.graphics.setColor(color[1], color[2], color[3], a)
        love.graphics.rectangle("fill", x, mid - h, W/40 - 1, h * 2)
    end
end

local function radar(W, H, t, color, alpha)
    local cx, cy = W/2, H*0.55
    for k = 1, 4 do
        local r = 40 + k * 32 + math.sin(t*2 + k) * 6
        love.graphics.setColor(color[1], color[2], color[3], alpha * 0.15 / k)
        love.graphics.setLineWidth(1.5)
        love.graphics.circle("line", cx, cy, r)
    end
    local sweep = t * 1.5 % (math.pi * 2)
    love.graphics.setColor(color[1], color[2], color[3], alpha * 0.55)
    love.graphics.setLineWidth(2)
    love.graphics.line(cx, cy,
        cx + math.cos(sweep) * 200, cy + math.sin(sweep) * 200)
end

local function scanlines(W, H, t, color, alpha)
    for k = 0, 12 do
        local y = ((t * 60 + k * (H/12)) % H)
        love.graphics.setColor(color[1], color[2], color[3], alpha * 0.15)
        love.graphics.rectangle("fill", 0, y, W, 1)
    end
end

local function gears(W, H, t, color, alpha)
    local cx, cy = W/2, H*0.5
    for k = 1, 3 do
        local rad = 80 + k * 55
        local rot = t * (k * 0.4) * (k % 2 == 0 and 1 or -1)
        love.graphics.setColor(color[1], color[2], color[3], alpha * 0.10)
        love.graphics.setLineWidth(2)
        love.graphics.circle("line", cx, cy, rad)
        for i = 1, 12 do
            local a = rot + i * (math.pi*2/12)
            love.graphics.line(
                cx + math.cos(a)*rad,       cy + math.sin(a)*rad,
                cx + math.cos(a)*(rad + 5), cy + math.sin(a)*(rad + 5))
        end
    end
end

local function rings(W, H, t, color, alpha)
    local cx, cy = W/2, H*0.5
    for i = 1, 5 do
        local r = ((t * 30 + i * 55) % 260)
        local a = alpha * 0.25 * (1 - r/260)
        love.graphics.setColor(color[1], color[2], color[3], a)
        love.graphics.setLineWidth(2)
        love.graphics.circle("line", cx, cy, r)
    end
end

local function data_rain(W, H, t, color, alpha)
    for i = 1, 20 do
        local x = (i * 31) % W
        local y = ((t * 100 + i * 55) % (H + 40))
        local len = 4 + (i % 3) * 3
        love.graphics.setColor(color[1], color[2], color[3], alpha * 0.35)
        love.graphics.setLineWidth(1)
        love.graphics.line(x, y, x, y + len)
        love.graphics.setColor(color[1], color[2], color[3], alpha * 0.7)
        love.graphics.line(x, y, x, y + 2)
    end
end

local function particles(W, H, t, color, alpha)
    for i = 1, 25 do
        local ph = i * 0.9
        local x = (i * 53 + math.sin(t*0.5+ph)*40) % W
        local y = (i * 37 + math.cos(t*0.7+ph)*30) % H
        love.graphics.setColor(color[1], color[2], color[3], alpha * 0.4)
        love.graphics.circle("fill", x, y, 1.2)
    end
end

bg.MAP = {
    embers = embers, waveform = waveform, radar = radar,
    scanlines = scanlines, gears = gears, rings = rings,
    data_rain = data_rain, particles = particles,
}

bg.BY_NODE = {
    [0] = "rings", [3] = "embers", [5] = "radar", [2] = "waveform",
    [6] = "scanlines", [7] = "gears", [8] = "data_rain",
}

function bg.draw(kind, W, H, t, color, alpha)
    local fn = bg.MAP[kind or "particles"]
    if fn then fn(W, H, t, color, alpha or 1) end
end

function bg.for_node(idx)
    return bg.BY_NODE[idx] or "particles"
end

return bg
