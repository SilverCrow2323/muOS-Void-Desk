-- love/effects/forge_bg.lua -- procedural forge background
local ok_sfx, SFX = pcall(require, "core.audio")
if not ok_sfx then SFX = nil end
local M = { sparks = {}, arcs = {}, sfx = {}, t_sfx = 0 }
local function rnd(a, b) return a + math.random() * (b - a) end

function M._gen_sfx()
    local sr = 22050
    local vol = (SFX and SFX.get_volume and SFX.get_volume() or 0.7)
    local function mk(dur, fn)
        local n = math.floor(dur * sr)
        local sd = love.sound.newSoundData(n, sr, 16, 1)
        for i = 0, n - 1 do
            sd:setSample(i, math.max(-1, math.min(1, fn(i / sr, i / n))))
        end
        return love.audio.newSource(sd, "static")
    end
    pcall(function()
        M.sfx.sizzle = mk(0.8, function(_, k)
            return (math.random() * 2 - 1) * (1 - k) * (1 - k) * 0.12 * vol
        end)
        M.sfx.arc = mk(0.20, function(t, k)
            return (math.sin(2 * math.pi * 180 * t) * 0.3
                + (math.random() * 2 - 1) * 0.4) * (1 - k) ^ 3 * 0.22 * vol
        end)
    end)
end

function M._spark(W, H)
    return { x = rnd(0, W), y = H + 8,
             vx = rnd(-40, 40), vy = rnd(-130, -70),
             life = rnd(0.8, 1.8), age = 0,
             hot = math.random() > 0.5 }
end

function M._arc(W, H)
    local y0 = rnd(30, H * 0.55)
    local pts = {}
    for i = 0, 8 do
        local dy = (i == 0 or i == 8) and 0 or rnd(-14, 14)
        pts[#pts + 1] = { x = i / 8 * W, y = y0 + dy }
    end
    return { pts = pts, life = rnd(0.08, 0.16), age = 0 }
end

function M.draw(W, H, t, nc, alpha)
    alpha = alpha or 1
    if not M.sfx.sizzle then M._gen_sfx() end
    local dt = love.timer.getDelta()

    love.graphics.clear(0.020 * alpha, 0.012 * alpha, 0.008 * alpha, 1)
    for r = 260, 40, -40 do
        love.graphics.setColor(1, 0.28, 0.05, 0.02 * alpha)
        love.graphics.circle("fill", W / 2, H + 40, r)
    end
    for i = 1, 3 do
        local y = H * 0.6 + math.sin(t * 0.8 + i) * 30
        love.graphics.setColor(1, 0.5, 0.15, 0.012 * alpha)
        love.graphics.rectangle("fill", 0, y, W, 40)
    end

    while #M.sparks < 24 do M.sparks[#M.sparks + 1] = M._spark(W, H) end
    for i = #M.sparks, 1, -1 do
        local s = M.sparks[i]
        s.age = s.age + dt
        s.x = s.x + s.vx * dt
        s.y = s.y + s.vy * dt
        s.vy = s.vy + 60 * dt
        if s.age > s.life or s.y < -10 then
            table.remove(M.sparks, i)
        else
            local k = 1 - s.age / s.life
            love.graphics.setColor(1, s.hot and 0.85 or 0.3,
                                   s.hot and 0.25 or 0.05, k * alpha * 0.9)
            love.graphics.circle("fill", s.x, s.y, 1 + k)
        end
    end

    if math.random() < 0.03 and #M.arcs < 2 then
        M.arcs[#M.arcs + 1] = M._arc(W, H)
        if M.sfx.arc and math.random() < 0.4 then
            M.sfx.arc:stop(); M.sfx.arc:play()
        end
    end
    for i = #M.arcs, 1, -1 do
        local a = M.arcs[i]
        a.age = a.age + dt
        if a.age > a.life then
            table.remove(M.arcs, i)
        else
            local k = 1 - a.age / a.life
            love.graphics.setColor(0.9, 0.95, 1, k * 0.7 * alpha)
            love.graphics.setLineWidth(1.5)
            local flat = {}
            for _, p in ipairs(a.pts) do
                flat[#flat + 1] = p.x; flat[#flat + 1] = p.y
            end
            love.graphics.line(flat)
            love.graphics.setLineWidth(1)
        end
    end

    M.t_sfx = M.t_sfx + dt
    if M.t_sfx > 4.0 then
        M.t_sfx = 0
        if M.sfx.sizzle and math.random() < 0.5 then
            M.sfx.sizzle:stop(); M.sfx.sizzle:play()
        end
    end
end

return M
