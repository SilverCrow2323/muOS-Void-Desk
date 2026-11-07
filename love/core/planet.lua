-- Planet renderer with true spherical rotation.
-- Features stored as (phi, theta_init) where:
--   phi = latitude, range -π/2 (south) to +π/2 (north)
--   theta_init = starting longitude (radians)
-- At render time, rotate by t*speed. Compute screen position + depth:
--   theta = theta_init + rot
--   x_screen = r * cos(phi) * sin(theta)
--   y_screen = r * sin(phi)
--   depth = cos(phi) * cos(theta)     (visible if > 0)
--   scale = cos(theta)                 (foreshortening near edges)
local planet = {}

local function mix(c1, c2, t)
    return { c1[1]*(1-t)+c2[1]*t, c1[2]*(1-t)+c2[2]*t, c1[3]*(1-t)+c2[3]*t }
end
local function shade(c, f) return { math.max(0,c[1]*f), math.max(0,c[2]*f), math.max(0,c[3]*f) } end
local function clamp01(v) return math.max(0, math.min(1, v)) end

local function prng(seed)
    local s = seed or 1
    return function()
        s = (s * 1103515245 + 12345) % 2147483648
        return s / 2147483648
    end
end

-- ============ FEATURE GENERATION (once per body) ============
local function ensure_surface(body, type, seed)
    if body._surface then return body._surface end
    local rnd = prng(seed or 42)
    local feats = {}

    if type == "gas_bands" then
        for i = 1, 8 do
            feats[i] = { band = true,
                lat = -0.85 + (i-1) * 0.24,
                h = 0.09 + rnd() * 0.10,
                tint = rnd() * 0.5,
            }
        end
        for i = 1, 2 do
            feats[#feats+1] = { storm = true,
                phi = (rnd() - 0.5) * 1.2,
                theta = rnd() * 6.28,
                size = 0.18 + rnd() * 0.14,
                color = { 1.0, 0.55 + rnd()*0.2, 0.30 },
            }
        end

    elseif type == "rocky_craters" then
        for i = 1, 9 do
            feats[i] = { crater = true,
                phi = (rnd() - 0.5) * 2.4,
                theta = rnd() * 6.28,
                size = 0.06 + rnd() * 0.11,
            }
        end
        for i = 1, 4 do
            feats[#feats+1] = { ambient = true,
                dx = (rnd() - 0.5) * 1.3, dy = (rnd() - 0.5) * 1.3,
                size = 0.18 + rnd() * 0.20,
                shade_f = 0.6 + rnd() * 0.5,
            }
        end

    elseif type == "ocean_clouds" then
        for i = 1, 3 do
            feats[i] = { land = true,
                phi = (rnd() - 0.5) * 1.8,
                theta = rnd() * 6.28,
                w = 0.16 + rnd() * 0.16,
                h = 0.10 + rnd() * 0.10,
            }
        end
        for i = 1, 6 do
            feats[#feats+1] = { cloud = true,
                phi = (rnd() - 0.5) * 2.2,
                theta = rnd() * 6.28,
                w = 0.14 + rnd() * 0.18,
                h = 0.05 + rnd() * 0.07,
                speed_mult = 1.5,
            }
        end

    elseif type == "desert_dunes" then
        for i = 1, 9 do
            feats[i] = { dune = true,
                lat = -0.9 + (i-1) * 0.22,
                tilt = (rnd() - 0.5) * 0.6,
                tint = rnd() * 0.5,
            }
        end
        for i = 1, 3 do
            feats[#feats+1] = { storm = true,
                phi = (rnd() - 0.5) * 1.0,
                theta = rnd() * 6.28,
                size = 0.12 + rnd() * 0.10,
                color = { 1.0, 0.75, 0.4 },
            }
        end

    elseif type == "volcanic" then
        for i = 1, 8 do
            feats[i] = { crack = true,
                phi = (rnd() - 0.5) * 2.0,
                theta = rnd() * 6.28,
                size = 0.06 + rnd() * 0.10,
                glow = rnd(),
            }
        end
        for i = 1, 3 do
            feats[#feats+1] = { pool = true,
                phi = (rnd() - 0.5) * 1.6,
                theta = rnd() * 6.28,
                size = 0.12 + rnd() * 0.10,
            }
        end

    elseif type == "icy" then
        for i = 1, 8 do
            feats[i] = { snow = true,
                phi = (rnd() - 0.5) * 2.2,
                theta = rnd() * 6.28,
                size = 0.14 + rnd() * 0.16,
            }
        end
        for i = 1, 6 do
            feats[#feats+1] = { crack = true,
                phi = (rnd() - 0.5) * 2.0,
                theta = rnd() * 6.28,
                size = 0.10 + rnd() * 0.15,
            }
        end
    end

    body._surface = feats
    return feats
end

-- Project a feature at (phi, theta_current) on sphere of radius r.
-- Returns: x_offset, y_offset, depth (0=back,1=front-center), or nil if back.
local function project(phi, theta, r)
    local cos_t = math.cos(theta)
    if cos_t <= 0.02 then return nil end
    local cos_p = math.cos(phi)
    local sin_p = math.sin(phi)
    local x_off = r * cos_p * math.sin(theta)
    local y_off = r * sin_p
    return x_off, y_off, cos_t
end

-- ============ SURFACE RENDERERS ============
local SURFACES = {}

SURFACES.gas_bands = function(x, y, r, base, rot, body)
    local feats = ensure_surface(body, "gas_bands", body.node and body.node.idx or 3)
    -- Bands: static ellipses clipped to sphere
    for _, f in ipairs(feats) do
        if f.band then
            local yy = y + f.lat * r * 0.90
            local hh = f.h * r
            local half_w = r * math.sqrt(math.max(0, 1 - (f.lat * 0.90)^2)) * 0.96
            local cc = mix(base, {1, 0.85, 0.55}, 0.3 + f.tint * 0.4)
            love.graphics.setColor(cc[1], cc[2], cc[3], 0.55)
            love.graphics.ellipse("fill", x, yy, half_w, hh)
        end
    end
    -- Storms rotate with proper projection
    for _, f in ipairs(feats) do
        if f.storm then
            local theta = f.theta + rot
            local x_off, y_off, depth = project(f.phi, theta, r)
            if x_off then
                local px = x + x_off
                local py = y + y_off
                local sw = r * f.size * depth
                local sh = r * f.size * 0.65
                love.graphics.setColor(f.color[1], f.color[2], f.color[3], 0.85 * depth)
                love.graphics.ellipse("fill", px, py, sw, sh)
                love.graphics.setColor(1, 0.85, 0.55, 0.4 * depth)
                love.graphics.ellipse("fill", px, py, sw * 0.5, sh * 0.5)
            end
        end
    end
end

SURFACES.rocky_craters = function(x, y, r, base, rot, body)
    local feats = ensure_surface(body, "rocky_craters", body.node and body.node.idx or 1)
    -- Ambient patches (fixed, no rotation)
    for _, f in ipairs(feats) do
        if f.ambient then
            local cc = shade(base, f.shade_f)
            love.graphics.setColor(cc[1], cc[2], cc[3], 0.25)
            love.graphics.circle("fill", x + f.dx * r, y + f.dy * r, r * f.size)
        end
    end
    -- Craters with spherical projection
    for _, f in ipairs(feats) do
        if f.crater then
            local theta = f.theta + rot
            local x_off, y_off, depth = project(f.phi, theta, r)
            if x_off then
                local px = x + x_off
                local py = y + y_off
                local cr = r * f.size
                -- crater shadow
                love.graphics.setColor(shade(base, 0.20)[1], shade(base, 0.20)[2], shade(base, 0.20)[3], 0.85 * depth)
                love.graphics.ellipse("fill", px, py, cr * depth, cr)
                -- rim highlight
                love.graphics.setColor(shade(base, 1.5)[1], shade(base, 1.5)[2], shade(base, 1.5)[3], 0.6 * depth)
                love.graphics.ellipse("fill", px - cr * 0.25 * depth, py - cr * 0.25, cr * 0.55 * depth, cr * 0.55)
            end
        end
    end
end

SURFACES.ocean_clouds = function(x, y, r, base, rot, body)
    local feats = ensure_surface(body, "ocean_clouds", body.node and body.node.idx or 2)
    -- Deep ocean
    love.graphics.setColor(shade(base, 0.35)[1], shade(base, 0.35)[2],
                           shade(base, 0.55)[3], 0.95)
    love.graphics.circle("fill", x, y, r)
    -- Land
    for _, f in ipairs(feats) do
        if f.land then
            local theta = f.theta + rot
            local x_off, y_off, depth = project(f.phi, theta, r)
            if x_off then
                local px = x + x_off
                local py = y + y_off
                local g = mix(base, {0.35, 0.85, 0.45}, 0.6)
                love.graphics.setColor(g[1], g[2], g[3], 0.9 * depth)
                love.graphics.ellipse("fill", px, py, r * f.w * depth, r * f.h)
            end
        end
    end
    -- Clouds (faster rotation, separate layer)
    for _, f in ipairs(feats) do
        if f.cloud then
            local theta = f.theta + rot * (f.speed_mult or 1.5)
            local x_off, y_off, depth = project(f.phi, theta, r)
            if x_off then
                local px = x + x_off
                local py = y + y_off
                love.graphics.setColor(1, 1, 1, 0.75 * depth)
                love.graphics.ellipse("fill", px, py, r * f.w * depth, r * f.h)
            end
        end
    end
end

SURFACES.desert_dunes = function(x, y, r, base, rot, body)
    local feats = ensure_surface(body, "desert_dunes", body.node and body.node.idx or 0)
    for _, f in ipairs(feats) do
        if f.dune then
            local yy = y + f.lat * r * 0.90
            local half_w = r * math.sqrt(math.max(0, 1 - (f.lat * 0.90)^2)) * 0.95
            local x1 = x - half_w
            local x2 = x + half_w
            local cc = mix(base, {1, 0.9, 0.55}, 0.3 + f.tint * 0.4)
            love.graphics.setColor(cc[1], cc[2], cc[3], 0.6)
            love.graphics.setLineWidth(3)
            love.graphics.line(x1, yy, x2, yy + f.tilt * r * 0.15)
        end
    end
    for _, f in ipairs(feats) do
        if f.storm then
            local theta = f.theta + rot * 1.2
            local x_off, y_off, depth = project(f.phi, theta, r)
            if x_off then
                love.graphics.setColor(f.color[1], f.color[2], f.color[3], 0.65 * depth)
                love.graphics.ellipse("fill", x + x_off, y + y_off,
                                     r * f.size * depth, r * f.size * 0.7)
            end
        end
    end
end

SURFACES.volcanic = function(x, y, r, base, rot, body)
    local feats = ensure_surface(body, "volcanic", body.node and body.node.idx or 6)
    -- Lava pools
    for _, f in ipairs(feats) do
        if f.pool then
            local theta = f.theta + rot
            local x_off, y_off, depth = project(f.phi, theta, r)
            if x_off then
                local pulse = 0.65 + 0.35 * math.sin(rot * 2.5 + f.phi * 3)
                love.graphics.setColor(1, 0.35, 0.10, 0.4 * depth * pulse)
                love.graphics.circle("fill", x + x_off, y + y_off,
                                     r * f.size * 1.5 * depth)
                love.graphics.setColor(1, 0.65, 0.25, 0.85 * depth * pulse)
                love.graphics.circle("fill", x + x_off, y + y_off,
                                     r * f.size * depth)
            end
        end
    end
    -- Lava cracks
    for _, f in ipairs(feats) do
        if f.crack then
            local theta = f.theta + rot
            local x_off, y_off, depth = project(f.phi, theta, r)
            if x_off then
                local pulse = 0.7 + 0.3 * math.sin(rot * 3 + f.glow * 6)
                local px, py = x + x_off, y + y_off
                local cr = r * f.size * depth
                -- crack line (short)
                local nx = px + math.cos(f.theta * 2 + rot) * cr * 2
                local ny = py + math.sin(f.theta * 3 + rot) * cr * 2
                love.graphics.setColor(1, 0.85, 0.30, 0.9 * depth * pulse)
                love.graphics.setLineWidth(math.max(1, 2 * depth))
                love.graphics.line(px, py, nx, ny)
            end
        end
    end
    -- Ambient red glow
    love.graphics.setColor(1, 0.3, 0.1, 0.10)
    love.graphics.circle("fill", x, y, r * 1.05)
end

SURFACES.icy = function(x, y, r, base, rot, body)
    local feats = ensure_surface(body, "icy", body.node and body.node.idx or 7)
    -- Base icy
    love.graphics.setColor(shade(base, 1.1)[1], shade(base, 1.15)[2],
                           shade(base, 1.25)[3], 0.5)
    love.graphics.circle("fill", x, y, r)
    -- Snow patches
    for _, f in ipairs(feats) do
        if f.snow then
            local theta = f.theta + rot
            local x_off, y_off, depth = project(f.phi, theta, r)
            if x_off then
                love.graphics.setColor(1, 1, 1, 0.7 * depth)
                love.graphics.ellipse("fill", x + x_off, y + y_off,
                                     r * f.size * depth, r * f.size * 0.7)
            end
        end
    end
    -- Cracks (blue lines)
    for _, f in ipairs(feats) do
        if f.crack then
            local theta = f.theta + rot
            local x_off, y_off, depth = project(f.phi, theta, r)
            if x_off then
                local px, py = x + x_off, y + y_off
                local ex = px + math.cos(f.theta * 2 + rot * 0.5) * r * f.size * depth
                local ey = py + math.sin(f.theta * 2 + rot * 0.5) * r * f.size * depth
                love.graphics.setColor(0.55, 0.80, 1.0, 0.8 * depth)
                love.graphics.setLineWidth(1.5)
                love.graphics.line(px, py, ex, ey)
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
    end
    love.graphics.setColor(dark[1], dark[2], dark[3], 1)
    love.graphics.circle("fill", x, y, r)
    love.graphics.setColor(light[1], light[2], light[3], 1)
    love.graphics.circle("fill", x - r*0.25, y - r*0.25, r*0.70)
    local blink = math.sin(t * 4) > 0
    love.graphics.setColor(blink and 1 or 0.5, blink and 0.25 or 0.1, 0.1, 1)
    love.graphics.circle("fill", x, y - r * 1.5, 2)
    if blink then
        love.graphics.setColor(1, 0.25, 0.25, 0.3)
        love.graphics.circle("fill", x, y - r * 1.5, 5)
    end
    love.graphics.setColor(0.6, 0.6, 0.6, 1)
    love.graphics.setLineWidth(1)
    love.graphics.line(x, y - r, x, y - r * 1.5)
end

-- ============ COMET (END NODE) ============
function planet.draw_comet(x, y, r, base, t, body)
    local orbit_angle = body and (body.angle or 0) or 0
    local tx = -math.sin(orbit_angle)
    local ty =  math.cos(orbit_angle) * 0.42
    local tlen = math.sqrt(tx*tx + ty*ty)
    if tlen > 0.001 then tx, ty = tx/tlen, ty/tlen end
    local dx, dy = -tx, -ty

    local tail_len = r * 14
    for i = 1, 56 do
        local frac = i / 56
        local dist = frac * tail_len
        local px = x + dx * dist
        local py = y + dy * dist
        local width = r * (1.4 * (1 - frac) + 0.15)
        local cc = mix({0.55, 0.15, 0.72}, {0.85, 0.20, 0.30}, frac)
        love.graphics.setColor(cc[1], cc[2], cc[3], (1 - frac) * 0.55)
        love.graphics.circle("fill", px, py, width)
    end
    for i = 1, 30 do
        local frac = i / 30
        local px = x + dx * frac * tail_len * 0.65
        local py = y + dy * frac * tail_len * 0.65
        local width = r * (0.9 * (1 - frac) + 0.08)
        love.graphics.setColor(0.90, 0.30, 0.45, (1 - frac) * 0.55)
        love.graphics.circle("fill", px, py, width)
    end
    for i = 1, 14 do
        local frac = (i / 14) ^ 1.3
        local bx = x + dx * frac * tail_len * 0.9
        local by = y + dy * frac * tail_len * 0.9
        local perp_x, perp_y = -dy, dx
        local off = math.sin(t * 8 + i * 1.7) * r * 1.2 * (1 - frac)
        local jx = bx + perp_x * off + math.sin(t * 22 + i * 2.3) * 3.5
        local jy = by + perp_y * off + math.cos(t * 19 + i * 1.9) * 3.5
        love.graphics.setColor(0.85, 0.65, 1.0, (1 - frac) * 0.85)
        love.graphics.setLineWidth(1.2)
        love.graphics.line(bx, by, jx, jy)
    end
    for k = 4, 1, -1 do
        love.graphics.setColor(0.55, 0.25, 0.90, 0.16 / k)
        love.graphics.circle("fill", x, y, r + k * 3)
    end
    love.graphics.setColor(0.10, 0.04, 0.16, 1)
    love.graphics.circle("fill", x, y, r)
    love.graphics.setColor(0.65, 0.35, 1.0, 0.75)
    love.graphics.setLineWidth(1.5)
    love.graphics.circle("line", x, y, r)
    for i = 1, 6 do
        local a0 = i * math.pi / 3 + t * 1.2
        local a1 = a0 + math.pi / 5
        local x1 = x + math.cos(a0) * r * 0.88
        local y1 = y + math.sin(a0) * r * 0.88
        local x2 = x + math.cos(a1) * r * 0.55
        local y2 = y + math.sin(a1) * r * 0.55
        love.graphics.setColor(1, 0.85, 0.30, 0.55)
        love.graphics.setLineWidth(3)
        love.graphics.line(x1, y1, x2, y2)
        love.graphics.setColor(1, 1, 0.70, 0.95)
        love.graphics.setLineWidth(1.2)
        love.graphics.line(x1, y1, x2, y2)
    end
    for i = 1, 4 do
        local a = t * 2.5 + i * 1.4
        local ax = x + math.cos(a) * (r + 3)
        local ay = y + math.sin(a) * (r + 3)
        local a2 = a + 0.5 + math.sin(t * 15 + i) * 0.3
        local bx = x + math.cos(a2) * (r + 7)
        local by = y + math.sin(a2) * (r + 7)
        love.graphics.setColor(0.80, 0.55, 1.0, 0.85)
        love.graphics.setLineWidth(1)
        love.graphics.line(ax, ay, bx, by)
    end
    love.graphics.setColor(1, 0.85, 0.55, 0.35)
    love.graphics.circle("fill", x - r * 0.3, y - r * 0.3, r * 0.35)
end

-- ============ PLANET (dispatcher) ============
function planet.draw_planet(x, y, r, base, t, opts, body)
    opts = opts or {}
    local surface = opts.surface or "gas_bands"
    local rot = t * (opts.rot_speed or 0.6)

    if opts.ring then planet._ring_arc(x, y, r, opts.ring, opts.ring_tilt or 0.35, base, true) end

    local dark = shade(base, 0.30)
    love.graphics.setColor(dark[1], dark[2], dark[3], 1)
    love.graphics.circle("fill", x, y, r)

    local fn = SURFACES[surface]
    if fn and r >= 8 then fn(x, y, r, base, rot, body or {node = {idx = 0}}) end

    -- Light gradient top-left
    love.graphics.setColor(1, 1, 1, 0.16)
    love.graphics.circle("fill", x - r*0.30, y - r*0.30, r*0.55)
    -- Terminator
    love.graphics.setColor(dark[1], dark[2], dark[3], 0.45)
    love.graphics.circle("fill", x + r*0.55, y + r*0.55, r*0.88)
    -- Limb glow
    love.graphics.setColor(mix(base, {1,1,1}, 0.5)[1],
                           mix(base, {1,1,1}, 0.5)[2],
                           mix(base, {1,1,1}, 0.5)[3], 0.20)
    love.graphics.setLineWidth(2)
    love.graphics.circle("line", x, y, r + 1)
    -- Edge
    love.graphics.setColor(mix(base, {1,1,1}, 0.3)[1],
                           mix(base, {1,1,1}, 0.3)[2],
                           mix(base, {1,1,1}, 0.3)[3], 0.35)
    love.graphics.setLineWidth(1)
    love.graphics.circle("line", x, y, r)

    if opts.ring then planet._ring_arc(x, y, r, opts.ring, opts.ring_tilt or 0.35, base, false) end

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
