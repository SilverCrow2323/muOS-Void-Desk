-- Procedural planet rendering: rotating bodies with unique surfaces.
-- Surface types: gas_bands, rocky_craters, ocean_clouds, desert_dunes,
--                volcanic, icy, sun, satellite.
local planet = {}

local function mix(c1, c2, t)
    return { c1[1]*(1-t)+c2[1]*t, c1[2]*(1-t)+c2[2]*t, c1[3]*(1-t)+c2[3]*t }
end
local function shade(c, f) return { math.max(0,c[1]*f), math.max(0,c[2]*f), math.max(0,c[3]*f) } end
local function clamp01(v) return math.max(0, math.min(1, v)) end

-- ============ Deterministic pseudo-random per body ============
local function prng(seed)
    local s = seed or 1
    return function()
        s = (s * 1103515245 + 12345) % 2147483648
        return s / 2147483648
    end
end

-- Generate surface feature list ONCE per body (cached on the body table)
local function ensure_surface(body, type, seed)
    if body._surface then return body._surface end
    local rnd = prng(seed or 42)
    local feats = {}

    if type == "gas_bands" then
        -- 8 flowing horizontal bands
        for i = 1, 8 do
            feats[i] = {
                y = -0.9 + (i-1) * 0.24,
                h = 0.10 + rnd() * 0.10,
                col_shift = rnd() * 0.7 - 0.35,
                wave = rnd() * 6.28,
            }
        end
        -- 1-2 big storms (Jupiter Great Red Spot)
        for i = 1, 2 do
            feats[#feats+1] = { storm = true,
                y = -0.4 + rnd() * 0.8, size = 0.20 + rnd() * 0.15,
                col = {1.0, 0.55 + rnd()*0.2, 0.30} }
        end

    elseif type == "rocky_craters" then
        -- 12 craters of varying size, deterministic positions
        for i = 1, 12 do
            feats[i] = {
                ax = rnd() * 6.28,
                ay = (rnd() - 0.5) * 1.6,
                r  = 0.06 + rnd() * 0.14,
                depth = 0.4 + rnd() * 0.5,
            }
        end

    elseif type == "ocean_clouds" then
        -- 6 cloud swirls (white), scattered
        for i = 1, 6 do
            feats[i] = {
                ax = rnd() * 6.28,
                ay = (rnd() - 0.5) * 1.4,
                w  = 0.15 + rnd() * 0.20,
                h  = 0.06 + rnd() * 0.10,
                alpha = 0.55 + rnd() * 0.35,
            }
        end
        -- 1-2 land masses (green)
        for i = 1, 2 do
            feats[#feats+1] = { land = true,
                ax = rnd() * 6.28, ay = (rnd() - 0.5) * 1.2,
                w = 0.18 + rnd() * 0.15, h = 0.12 + rnd() * 0.10 }
        end

    elseif type == "desert_dunes" then
        -- 10 diagonal dune ridges
        for i = 1, 10 do
            feats[i] = {
                y = -0.9 + (i-1) * 0.20,
                tilt = (rnd() - 0.5) * 0.6,
                col_shift = rnd() * 0.5,
            }
        end

    elseif type == "volcanic" then
        -- 8 lava cracks
        for i = 1, 8 do
            feats[i] = {
                ax = rnd() * 6.28,
                ay = (rnd() - 0.5) * 1.5,
                r  = 0.05 + rnd() * 0.10,
                glow = rnd(),
            }
        end

    elseif type == "icy" then
        -- 9 cracks (blue lines)
        for i = 1, 9 do
            feats[i] = {
                ax = rnd() * 6.28,
                ay = (rnd() - 0.5) * 1.7,
                len = 0.3 + rnd() * 0.4,
                angle = rnd() * 6.28,
            }
        end
        -- 2-3 snow patches
        for i = 1, 3 do
            feats[#feats+1] = { snow = true,
                ax = rnd() * 6.28, ay = (rnd() - 0.5) * 1.2,
                r = 0.12 + rnd() * 0.15 }
        end
    end

    body._surface = feats
    return feats
end

-- ============ SURFACE TYPES ============
-- Each returns nothing; draws surface features inside the circle.
-- "rotation" angle controls horizontal scrolling of surface features.
local SURFACES = {}

SURFACES.gas_bands = function(x, y, r, base, rot, body)
    local feats = ensure_surface(body, "gas_bands", body.node and body.node.idx or 3)
    -- base gradient: darker top, brighter bottom
    for i, f in ipairs(feats) do
        if not f.storm then
            local ph = math.sin(rot + f.wave) * 0.5
            local yc = y + f.y * r + ph * r * 0.08
            local hh = f.h * r
            local cc = mix(base, {1, 0.85, 0.55}, clamp01(0.25 + f.col_shift * 0.5))
            love.graphics.setColor(cc[1], cc[2], cc[3], 0.55)
            -- Clip to circle via ellipse half-width
            local bpx = math.sqrt(math.max(0, r*r - (f.y * r)^2))
            love.graphics.ellipse("fill", x, yc, bpx * 0.96, hh)
        end
    end
    -- storms
    for _, f in ipairs(feats) do
        if f.storm then
            local sx = x + math.sin(rot * 1.5 + f.y * 3) * r * 0.5
            local sy = y + f.y * r
            if math.cos(rot * 1.5 + f.y * 3) > 0 then -- front side
                love.graphics.setColor(f.col[1], f.col[2], f.col[3], 0.85)
                love.graphics.ellipse("fill", sx, sy, r * f.size, r * f.size * 0.65)
                love.graphics.setColor(1, 0.85, 0.55, 0.5)
                love.graphics.ellipse("fill", sx, sy, r * f.size * 0.5, r * f.size * 0.30)
            end
        end
    end
end

SURFACES.rocky_craters = function(x, y, r, base, rot, body)
    local feats = ensure_surface(body, "rocky_craters", body.node and body.node.idx or 1)
    -- Base rock texture: mixed noise via a few translucent circles
    local rnd = prng((body.node and body.node.idx or 1) + 100)
    for i = 1, 6 do
        love.graphics.setColor(shade(base, 0.7 + rnd()*0.4)[1],
                               shade(base, 0.7 + rnd()*0.4)[2],
                               shade(base, 0.7 + rnd()*0.4)[3], 0.25)
        love.graphics.circle("fill",
            x + (rnd()-0.5) * r * 1.2, y + (rnd()-0.5) * r * 1.2, r * 0.4)
    end
    -- Craters that rotate with planet
    for _, f in ipairs(feats) do
        local a = f.ax + rot
        local cx_n = math.cos(a)
        if cx_n > -0.1 then -- front-visible
            local px = x + cx_n * r * 0.75
            local py = y + f.ay * r * 0.7
            if (px-x)^2 + (py-y)^2 < (r*0.95)^2 then
                local cr = r * f.r * (0.6 + 0.4 * cx_n)
                love.graphics.setColor(shade(base, 0.25)[1],
                                       shade(base, 0.25)[2],
                                       shade(base, 0.25)[3], 0.85)
                love.graphics.circle("fill", px, py, cr)
                love.graphics.setColor(shade(base, 1.4)[1],
                                       shade(base, 1.4)[2],
                                       shade(base, 1.4)[3], 0.7)
                love.graphics.circle("fill",
                    px - cr * 0.25, py - cr * 0.25, cr * 0.55)
            end
        end
    end
end

SURFACES.ocean_clouds = function(x, y, r, base, rot, body)
    local feats = ensure_surface(body, "ocean_clouds", body.node and body.node.idx or 2)
    -- Deep ocean base
    love.graphics.setColor(shade(base, 0.35)[1], shade(base, 0.35)[2],
                           shade(base, 0.55)[3], 0.9)
    love.graphics.circle("fill", x, y, r)
    -- Land masses (rotating)
    for _, f in ipairs(feats) do
        if f.land then
            local a = f.ax + rot
            if math.cos(a) > -0.2 then
                local px = x + math.cos(a) * r * 0.6
                local py = y + f.ay * r * 0.7
                if (px-x)^2 + (py-y)^2 < (r*0.85)^2 then
                    local g = mix(base, {0.35, 0.85, 0.45}, 0.6)
                    love.graphics.setColor(g[1], g[2], g[3], 0.85)
                    love.graphics.ellipse("fill", px, py, r * f.w, r * f.h)
                end
            end
        end
    end
    -- Clouds (white swirls, faster rotation)
    for _, f in ipairs(feats) do
        if not f.land then
            local a = f.ax + rot * 1.3
            if math.cos(a) > -0.1 then
                local px = x + math.cos(a) * r * 0.65
                local py = y + f.ay * r * 0.7
                if (px-x)^2 + (py-y)^2 < (r*0.9)^2 then
                    love.graphics.setColor(1, 1, 1, f.alpha * 0.85)
                    love.graphics.ellipse("fill", px, py, r * f.w, r * f.h)
                end
            end
        end
    end
end

SURFACES.desert_dunes = function(x, y, r, base, rot, body)
    local feats = ensure_surface(body, "desert_dunes", body.node and body.node.idx or 0)
    for i, f in ipairs(feats) do
        local ph = rot * 1.2 + i * 0.5
        local off = math.sin(ph) * r * 0.15
        local yy = y + f.y * r
        local x1 = x - r * 0.95 + off
        local x2 = x + r * 0.95 + off * 0.6
        local col = mix(base, {1, 0.9, 0.55}, 0.3 + f.col_shift * 0.4)
        love.graphics.setColor(col[1], col[2], col[3], 0.55)
        love.graphics.setLineWidth(3)
        love.graphics.line(x1, yy, x2, yy + f.tilt * r * 0.2)
    end
    -- Shimmer highlight
    local sh = math.sin(rot * 2) * 0.4 + 0.6
    love.graphics.setColor(1, 0.95, 0.65, 0.25 * sh)
    love.graphics.circle("fill", x - r*0.2, y - r*0.2, r*0.55)
end

SURFACES.volcanic = function(x, y, r, base, rot, body)
    local feats = ensure_surface(body, "volcanic", body.node and body.node.idx or 6)
    -- Lava cracks that rotate
    for _, f in ipairs(feats) do
        local a = f.ax + rot
        if math.cos(a) > -0.1 then
            local px = x + math.cos(a) * r * 0.6
            local py = y + f.ay * r * 0.7
            if (px-x)^2 + (py-y)^2 < (r*0.9)^2 then
                local pulse = 0.65 + 0.35 * math.sin(rot * 3 + f.glow * 6)
                local cr = r * f.r
                love.graphics.setColor(1, 0.35, 0.10, 0.35 * pulse)
                love.graphics.circle("fill", px, py, cr * 1.8)
                love.graphics.setColor(1, 0.55, 0.15, 0.85 * pulse)
                love.graphics.circle("fill", px, py, cr)
                love.graphics.setColor(1, 0.85, 0.40, 0.9 * pulse)
                love.graphics.circle("fill", px, py, cr * 0.45)
            end
        end
    end
    -- Ambient red glow
    love.graphics.setColor(1, 0.3, 0.1, 0.10)
    love.graphics.circle("fill", x, y, r * 1.05)
end

SURFACES.icy = function(x, y, r, base, rot, body)
    local feats = ensure_surface(body, "icy", body.node and body.node.idx or 7)
    -- Base icy tone
    love.graphics.setColor(shade(base, 1.1)[1], shade(base, 1.15)[2],
                           shade(base, 1.25)[3], 0.5)
    love.graphics.circle("fill", x, y, r)
    -- Snow patches (rotating)
    for _, f in ipairs(feats) do
        if f.snow then
            local a = f.ax + rot
            if math.cos(a) > -0.15 then
                local px = x + math.cos(a) * r * 0.55
                local py = y + f.ay * r * 0.7
                if (px-x)^2 + (py-y)^2 < (r*0.85)^2 then
                    love.graphics.setColor(1, 1, 1, 0.65)
                    love.graphics.circle("fill", px, py, r * f.r)
                end
            end
        end
    end
    -- Crack lines
    for _, f in ipairs(feats) do
        if not f.snow then
            local a = f.ax + rot
            if math.cos(a) > -0.1 then
                local px = x + math.cos(a) * r * 0.6
                local py = y + f.ay * r * 0.7
                if (px-x)^2 + (py-y)^2 < (r*0.9)^2 then
                    local ex = px + math.cos(f.angle + rot * 0.5) * r * f.len * 0.4
                    local ey = py + math.sin(f.angle + rot * 0.5) * r * f.len * 0.4
                    love.graphics.setColor(0.55, 0.75, 1.0, 0.75)
                    love.graphics.setLineWidth(1.5)
                    love.graphics.line(px, py, ex, ey)
                end
            end
        end
    end
end

-- ============ SUN ============
function planet.draw_sun(x, y, r, base, t)
    local pulse = 0.90 + 0.10 * math.sin(t * 1.8)
    for k = 6, 1, -1 do
        local c = mix(base, {1, 0.5, 0.1}, 0.3)
        love.graphics.setColor(c[1], c[2], c[3], 0.05 + 0.03 * math.sin(t*2 + k))
        love.graphics.circle("fill", x, y, r * (1 + k * 0.28) * pulse)
    end
    for i = 1, 14 do
        local ang = (i / 14) * math.pi * 2 + t * 0.6
        local fl = r + 6 + 10 * math.abs(math.sin(t * 2.2 + i * 0.9))
        local fc = mix(base, {1, 0.85, 0.4}, 0.5)
        love.graphics.setColor(fc[1], fc[2], fc[3], 0.55)
        love.graphics.setLineWidth(2)
        love.graphics.line(x + math.cos(ang) * (r*0.95), y + math.sin(ang) * (r*0.95),
                           x + math.cos(ang) * fl,        y + math.sin(ang) * fl)
    end
    for k = 3, 1, -1 do
        local c = mix(base, {1, 1, 0.85}, 0.35 / k)
        love.graphics.setColor(c[1], c[2], c[3], 0.95)
        love.graphics.circle("fill", x, y, r * pulse * (1 - (k-1) * 0.08))
    end
    love.graphics.setColor(1, 1, 0.9, 0.9)
    love.graphics.circle("fill", x - r*0.22, y - r*0.22, r*0.35)
    -- Surface rotation: sunspots drift
    for i = 1, 4 do
        local a = t * 0.5 + i * 1.8
        if math.cos(a) > 0 then
            local sx = x + math.cos(a) * r * 0.55
            local sy = y + math.sin(a * 0.8) * r * 0.35
            love.graphics.setColor(0.55, 0.25, 0.05, 0.55)
            love.graphics.circle("fill", sx, sy, r * 0.09)
        end
    end
end

-- ============ SATELLITE ============
function planet.draw_satellite(x, y, r, base, t)
    local light = mix(base, {1, 1, 1}, 0.35)
    local dark = shade(base, 0.4)
    local rot = t * 1.5
    for side = -1, 1, 2 do
        local px_off = side * r * 1.8
        local py_off = math.sin(rot + (side > 0 and 0 or math.pi)) * r * 0.5
        local px = x + px_off
        local py = y + py_off
        love.graphics.setColor(0.20, 0.35, 0.65, 0.95)
        love.graphics.rectangle("fill", px - 5, py - 2, 10, 4, 1, 1)
        love.graphics.setColor(0.55, 0.80, 1.0, 0.9)
        love.graphics.setLineWidth(1)
        love.graphics.rectangle("line", px - 5, py - 2, 10, 4, 1, 1)
        love.graphics.line(px - 1, py - 2, px - 1, py + 2)
        love.graphics.line(px + 1, py - 2, px + 1, py + 2)
    end
    love.graphics.setColor(dark[1], dark[2], dark[3], 1)
    love.graphics.circle("fill", x, y, r)
    love.graphics.setColor(light[1], light[2], light[3], 1)
    love.graphics.circle("fill", x - r*0.25, y - r*0.25, r*0.70)
    local blink = math.sin(t * 4) > 0
    if blink then
        love.graphics.setColor(1, 0.25, 0.25, 1)
        love.graphics.circle("fill", x, y - r * 1.5, 2)
        love.graphics.setColor(1, 0.25, 0.25, 0.3)
        love.graphics.circle("fill", x, y - r * 1.5, 5)
    else
        love.graphics.setColor(0.5, 0.1, 0.1, 1)
        love.graphics.circle("fill", x, y - r * 1.5, 2)
    end
    love.graphics.setColor(0.6, 0.6, 0.6, 1)
    love.graphics.setLineWidth(1)
    love.graphics.line(x, y - r, x, y - r * 1.5)
end

-- ============ PLANET (unified) ============
function planet.draw_planet(x, y, r, base, t, opts, body)
    opts = opts or {}
    local surface = opts.surface or "gas_bands"
    local rot = t * (opts.rot_speed or 0.6)

    -- 1) Back half of ring
    if opts.ring then planet._ring_arc(x, y, r, opts.ring, opts.ring_tilt or 0.35, base, true) end

    -- 2) Base sphere
    local dark = shade(base, 0.30)
    love.graphics.setColor(dark[1], dark[2], dark[3], 1)
    love.graphics.circle("fill", x, y, r)

    -- 3) Surface features
    local fn = SURFACES[surface]
    if fn and r >= 8 then fn(x, y, r, base, rot, body or {node = {idx = 0}}) end

    -- 4) Light gradient (top-left)
    love.graphics.setColor(1, 1, 1, 0.18)
    love.graphics.circle("fill", x - r*0.30, y - r*0.30, r*0.55)

    -- 5) Dark terminator crescent
    love.graphics.setColor(dark[1], dark[2], dark[3], 0.45)
    love.graphics.circle("fill", x + r*0.55, y + r*0.55, r*0.88)

    -- 6) Edge
    love.graphics.setColor(mix(base, {1,1,1}, 0.3)[1],
                           mix(base, {1,1,1}, 0.3)[2],
                           mix(base, {1,1,1}, 0.3)[3], 0.35)
    love.graphics.setLineWidth(1)
    love.graphics.circle("line", x, y, r)

    -- 7) Front half of ring
    if opts.ring then planet._ring_arc(x, y, r, opts.ring, opts.ring_tilt or 0.35, base, false) end

    -- 8) Moon
    if opts.moon then
        local ma = t * 1.3
        local mr = r * 2.4
        local mx = x + math.cos(ma) * mr
        local my = y + math.sin(ma) * mr * 0.45
        if math.sin(ma) > 0 then
            love.graphics.setColor(0.55, 0.55, 0.60, 0.7)
            love.graphics.circle("fill", mx, my, math.max(2, r*0.16))
        else
            love.graphics.setColor(0.85, 0.85, 0.90, 1)
            love.graphics.circle("fill", mx, my, math.max(2, r*0.20))
            love.graphics.setColor(0.55, 0.55, 0.60, 1)
            love.graphics.circle("fill", mx+1, my+1, math.max(1, r*0.12))
        end
    end
end

-- ============ RING ARCS ============
function planet._ring_arc(x, y, r, kind, tilt, color, back)
    local inner = (kind == "double") and r*1.30 or r*1.45
    local outer = (kind == "double") and r*2.60 or r*2.20
    local c
    if kind == "signal" then c = mix(color, {0.2, 0.95, 1.0}, 0.55)
    elseif kind == "double" then c = mix(color, {1.0, 0.7, 0.9}, 0.25)
    else c = mix(color, {0.85, 0.65, 0.40}, 0.35) end
    local alpha = back and 0.35 or 0.78
    local steps = 44
    local function ring_pass(rad, width, a_mult)
        love.graphics.setColor(c[1], c[2], c[3], alpha * a_mult)
        love.graphics.setLineWidth(width)
        for i = 1, steps do
            local a1 = (i-1) / steps * math.pi * 2
            local a2 = i / steps * math.pi * 2
            local mid = (a1 + a2) / 2
            local is_back = math.sin(mid) < 0
            if is_back == back then
                love.graphics.line(
                    x + math.cos(a1)*rad, y + math.sin(a1)*rad*tilt,
                    x + math.cos(a2)*rad, y + math.sin(a2)*rad*tilt)
            end
        end
    end
    ring_pass((inner+outer)/2, back and 2 or 3, 1.0)
    ring_pass(inner, back and 1 or 2, 0.7)
    ring_pass(outer, back and 1 or 2, 0.7)
    if kind == "double" then ring_pass(inner * 0.65, back and 1 or 2, 0.55) end
end

return planet
