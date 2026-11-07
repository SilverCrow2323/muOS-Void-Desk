-- BLAME-style cel-shaded planets, custom rings, orbit-following comet tail.
local planet = {}

local function mix(a, b, t)
    return { a[1]*(1-t)+b[1]*t, a[2]*(1-t)+b[2]*t, a[3]*(1-t)+b[3]*t }
end
local function cl01(v) return math.max(0, math.min(1, v)) end

-- Desaturate (BLAME muted palette)
local function desat(c, amt)
    amt = amt or 0.28
    local g = c[1]*0.299 + c[2]*0.587 + c[3]*0.114
    return { c[1]*(1-amt)+g*amt, c[2]*(1-amt)+g*amt, c[3]*(1-amt)+g*amt }
end

-- 3 hard tones from base + light direction
local function cel_tones(base, lit_dir_x, lit_dir_y)
    -- lit_dir points TOWARD the light
    local shadow = { base[1]*0.14 + 0.02, base[2]*0.14 + 0.03, base[3]*0.16 + 0.05 }
    local mid    = { base[1]*0.68, base[2]*0.68, base[3]*0.70 }
    local light  = { math.min(1, base[1]*1.42), math.min(1, base[2]*1.38),
                     math.min(1, base[3]*1.35) }
    return shadow, mid, light, lit_dir_x, lit_dir_y
end

-- Draw sphere with 8x8 hard-tone cells (cel shading)
local function draw_cel_sphere(x, y, r, base, lit_dx, lit_dy)
    local SHADOW, MID, LIGHT = cel_tones(base, lit_dx, lit_dy)
    local llen = math.sqrt(lit_dx*lit_dx + lit_dy*lit_dy)
    if llen < 0.001 then lit_dx, lit_dy = -0.7, -0.7
    else lit_dx, lit_dy = lit_dx/llen, lit_dy/llen end

    local N = 8
    local cell = (r * 2) / N

    love.graphics.setColor(SHADOW[1], SHADOW[2], SHADOW[3], 1)
    love.graphics.circle("fill", x, y, r)

    -- batch by tone for fewer color changes
    for tone_idx = 1, 3 do
        local tone
        if tone_idx == 1 then tone = SHADOW
        elseif tone_idx == 2 then tone = MID
        else tone = LIGHT end
        love.graphics.setColor(tone[1], tone[2], tone[3], 1)

        for i = 0, N-1 do
            for j = 0, N-1 do
                local cx = x - r + cell * (i + 0.5)
                local cy = y - r + cell * (j + 0.5)
                local dx, dy = cx - x, cy - y
                local dist = math.sqrt(dx*dx + dy*dy)
                if dist <= r - 0.5 then
                    local d = (dx * lit_dx + dy * lit_dy) / r
                    local matches
                    if tone_idx == 1 then matches = (d <= -0.15)
                    elseif tone_idx == 2 then matches = (d > -0.15 and d <= 0.4)
                    else matches = (d > 0.4) end
                    if matches then
                        love.graphics.rectangle("fill",
                            cx - cell/2 - 0.5, cy - cell/2 - 0.5,
                            cell + 1, cell + 1)
                    end
                end
            end
        end
    end

    -- Bold BLAME outline
    love.graphics.setColor(0.08, 0.08, 0.10, 0.95)
    love.graphics.setLineWidth(2)
    love.graphics.circle("line", x, y, r)
end

-- Surface feature projection
local function project(phi, theta, r)
    local cos_t = math.cos(theta)
    if cos_t <= 0.02 then return nil end
    return r * math.cos(phi) * math.sin(theta), r * math.sin(phi), cos_t
end

local function prng(seed)
    local s = seed or 1
    return function()
        s = (s * 1103515245 + 12345) % 2147483648
        return s / 2147483648
    end
end

local function ensure_surface(body, type, seed)
    if body._surface then return body._surface end
    local rnd = prng(seed or 42)
    local feats = {}
    if type == "gas_bands" then
        for i = 1, 7 do
            feats[i] = { band = true, lat = -0.85 + (i-1)*0.27,
                         h = 0.10 + rnd()*0.08, tint = rnd()*0.5 }
        end
    elseif type == "rocky_craters" then
        for i = 1, 10 do
            feats[i] = { crater = true,
                phi = (rnd()-0.5)*2.4, theta = rnd()*6.28,
                size = 0.06 + rnd()*0.11 }
        end
    elseif type == "ocean_clouds" then
        for i = 1, 3 do
            feats[i] = { land = true,
                phi = (rnd()-0.5)*1.8, theta = rnd()*6.28,
                w = 0.16 + rnd()*0.16, h = 0.10 + rnd()*0.10 }
        end
        for i = 1, 6 do
            feats[#feats+1] = { cloud = true,
                phi = (rnd()-0.5)*2.2, theta = rnd()*6.28,
                w = 0.14 + rnd()*0.18, h = 0.05 + rnd()*0.07,
                speed_mult = 1.5 }
        end
    elseif type == "desert_dunes" then
        for i = 1, 8 do
            feats[i] = { dune = true, lat = -0.9 + (i-1)*0.24,
                         tilt = (rnd()-0.5)*0.6, tint = rnd()*0.5 }
        end
    elseif type == "volcanic" then
        for i = 1, 7 do
            feats[i] = { crack = true,
                phi = (rnd()-0.5)*2.0, theta = rnd()*6.28,
                size = 0.06 + rnd()*0.10, glow = rnd() }
        end
        for i = 1, 3 do
            feats[#feats+1] = { pool = true,
                phi = (rnd()-0.5)*1.6, theta = rnd()*6.28,
                size = 0.11 + rnd()*0.10 }
        end
    elseif type == "icy" then
        for i = 1, 7 do
            feats[i] = { snow = true,
                phi = (rnd()-0.5)*2.2, theta = rnd()*6.28,
                size = 0.14 + rnd()*0.14 }
        end
        for i = 1, 5 do
            feats[#feats+1] = { crack = true,
                phi = (rnd()-0.5)*2.0, theta = rnd()*6.28,
                size = 0.10 + rnd()*0.13 }
        end
    end
    body._surface = feats
    return feats
end

-- ============ SURFACES (all in hard-tone cel style) ============
local SURFACES = {}

SURFACES.gas_bands = function(x, y, r, base, rot, body)
    local feats = ensure_surface(body, "gas_bands", body.node and body.node.idx or 3)
    local des = desat(base, 0.30)
    for _, f in ipairs(feats) do
        if f.band then
            local yy = y + f.lat * r * 0.92
            local hw = r * math.sqrt(math.max(0, 1 - (f.lat*0.92)^2)) * 0.96
            local cc = mix(des, {0.85, 0.72, 0.50}, 0.35 + f.tint*0.3)
            love.graphics.setColor(cc[1], cc[2], cc[3], 0.85)
            love.graphics.rectangle("fill", x - hw, yy - f.h*r*0.5, hw*2, f.h*r)
            -- hard edge line (BLAME panel look)
            love.graphics.setColor(0.10, 0.10, 0.12, 0.6)
            love.graphics.setLineWidth(1)
            love.graphics.line(x - hw, yy - f.h*r*0.5, x + hw, yy - f.h*r*0.5)
        end
    end
end

SURFACES.rocky_craters = function(x, y, r, base, rot, body)
    local feats = ensure_surface(body, "rocky_craters", body.node and body.node.idx or 1)
    local des = desat(base, 0.22)
    for _, f in ipairs(feats) do
        if f.crater then
            local theta = f.theta + rot
            local x_off, y_off, depth = project(f.phi, theta, r)
            if x_off then
                local cr = r * f.size
                -- shadow (hard)
                love.graphics.setColor(0.08, 0.08, 0.10, 0.85 * depth)
                love.graphics.ellipse("fill",
                    x + x_off, y + y_off, cr*depth, cr)
                -- highlight rim (hard)
                love.graphics.setColor(
                    math.min(1, des[1]*1.6), math.min(1, des[2]*1.6),
                    math.min(1, des[3]*1.6), 0.85 * depth)
                love.graphics.ellipse("fill",
                    x + x_off - cr*0.3*depth, y + y_off - cr*0.3,
                    cr*0.5*depth, cr*0.5)
            end
        end
    end
end

SURFACES.ocean_clouds = function(x, y, r, base, rot, body)
    local feats = ensure_surface(body, "ocean_clouds", body.node and body.node.idx or 2)
    for _, f in ipairs(feats) do
        if f.land then
            local theta = f.theta + rot
            local x_off, y_off, depth = project(f.phi, theta, r)
            if x_off then
                love.graphics.setColor(0.32, 0.55, 0.36, 0.95 * depth)
                love.graphics.ellipse("fill",
                    x + x_off, y + y_off, r*f.w*depth, r*f.h)
                -- hard edge
                love.graphics.setColor(0.10, 0.14, 0.10, 0.7 * depth)
                love.graphics.setLineWidth(1)
                love.graphics.ellipse("line",
                    x + x_off, y + y_off, r*f.w*depth, r*f.h)
            end
        end
    end
    for _, f in ipairs(feats) do
        if f.cloud then
            local theta = f.theta + rot * (f.speed_mult or 1.5)
            local x_off, y_off, depth = project(f.phi, theta, r)
            if x_off then
                love.graphics.setColor(0.92, 0.95, 1.0, 0.82 * depth)
                love.graphics.ellipse("fill",
                    x + x_off, y + y_off, r*f.w*depth, r*f.h)
            end
        end
    end
end

SURFACES.desert_dunes = function(x, y, r, base, rot, body)
    local feats = ensure_surface(body, "desert_dunes", body.node and body.node.idx or 0)
    for _, f in ipairs(feats) do
        if f.dune then
            local yy = y + f.lat * r * 0.92
            local hw = r * math.sqrt(math.max(0, 1 - (f.lat*0.92)^2)) * 0.95
            local cc = mix({0.85, 0.62, 0.30}, {1, 0.85, 0.50}, f.tint)
            love.graphics.setColor(cc[1], cc[2], cc[3], 0.9)
            love.graphics.setLineWidth(2)
            love.graphics.line(x - hw, yy, x + hw, yy + f.tilt * r * 0.15)
        end
    end
end

SURFACES.volcanic = function(x, y, r, base, rot, body)
    local feats = ensure_surface(body, "volcanic", body.node and body.node.idx or 6)
    for _, f in ipairs(feats) do
        if f.pool then
            local theta = f.theta + rot
            local x_off, y_off, depth = project(f.phi, theta, r)
            if x_off then
                local pulse = 0.7 + 0.3 * math.sin(rot*2.5 + f.phi*3)
                love.graphics.setColor(0.95, 0.30, 0.10, 0.85 * depth * pulse)
                love.graphics.circle("fill", x + x_off, y + y_off, r*f.size*depth)
                love.graphics.setColor(1, 0.85, 0.30, 0.9 * depth * pulse)
                love.graphics.circle("fill", x + x_off, y + y_off, r*f.size*depth*0.4)
            end
        end
    end
    for _, f in ipairs(feats) do
        if f.crack then
            local theta = f.theta + rot
            local x_off, y_off, depth = project(f.phi, theta, r)
            if x_off then
                local pulse = 0.7 + 0.3 * math.sin(rot*3 + f.glow*6)
                local cr = r * f.size * depth
                local nx = x + x_off + math.cos(f.theta*2 + rot) * cr*2
                local ny = y + y_off + math.sin(f.theta*3 + rot) * cr*2
                love.graphics.setColor(1, 0.85, 0.25, 0.95 * depth * pulse)
                love.graphics.setLineWidth(math.max(1, 2*depth))
                love.graphics.line(x + x_off, y + y_off, nx, ny)
            end
        end
    end
end

SURFACES.icy = function(x, y, r, base, rot, body)
    local feats = ensure_surface(body, "icy", body.node and body.node.idx or 7)
    love.graphics.setColor(0.72, 0.82, 0.94, 0.55)
    love.graphics.circle("fill", x, y, r)
    for _, f in ipairs(feats) do
        if f.snow then
            local theta = f.theta + rot
            local x_off, y_off, depth = project(f.phi, theta, r)
            if x_off then
                love.graphics.setColor(0.95, 0.98, 1.0, 0.85 * depth)
                love.graphics.ellipse("fill",
                    x + x_off, y + y_off, r*f.size*depth, r*f.size*0.7)
            end
        end
    end
    for _, f in ipairs(feats) do
        if f.crack then
            local theta = f.theta + rot
            local x_off, y_off, depth = project(f.phi, theta, r)
            if x_off then
                local px, py = x + x_off, y + y_off
                local ex = px + math.cos(f.theta*2 + rot*0.5) * r * f.size * depth
                local ey = py + math.sin(f.theta*2 + rot*0.5) * r * f.size * depth
                love.graphics.setColor(0.42, 0.62, 0.85, 0.95 * depth)
                love.graphics.setLineWidth(1.5)
                love.graphics.line(px, py, ex, ey)
            end
        end
    end
end

-- ============ SUN ============
function planet.draw_sun(x, y, r, base, t)
    local pulse = 0.92 + 0.08 * math.sin(t * 1.8)
    for k = 5, 1, -1 do
        love.graphics.setColor(1, 0.55, 0.20, 0.06 + 0.03 * math.sin(t*2+k))
        love.graphics.circle("fill", x, y, r * (1 + k*0.30) * pulse)
    end
    -- flares
    for i = 1, 12 do
        local ang = (i/12) * math.pi*2 + t * 0.6
        local fl = r + 5 + 9 * math.abs(math.sin(t*2.2 + i*0.9))
        love.graphics.setColor(1, 0.75, 0.35, 0.65)
        love.graphics.setLineWidth(2)
        love.graphics.line(
            x + math.cos(ang)*(r*0.9), y + math.sin(ang)*(r*0.9),
            x + math.cos(ang)*fl,      y + math.sin(ang)*fl)
    end
    -- cel tone core
    love.graphics.setColor(1.0, 0.75, 0.35, 1)
    love.graphics.circle("fill", x, y, r * pulse)
    love.graphics.setColor(1.0, 0.92, 0.55, 1)
    love.graphics.circle("fill", x - r*0.18, y - r*0.18, r*0.72)
    love.graphics.setColor(1.0, 1.0, 0.85, 1)
    love.graphics.circle("fill", x - r*0.28, y - r*0.28, r*0.42)
    -- sunspots
    for i = 1, 4 do
        local a = t * 0.5 + i * 1.8
        if math.cos(a) > 0 then
            local sx = x + math.cos(a) * r * 0.55
            local sy = y + math.sin(a*0.8) * r * 0.35
            love.graphics.setColor(0.45, 0.18, 0.05, 0.75)
            love.graphics.circle("fill", sx, sy, r * 0.10)
        end
    end
    -- outline
    love.graphics.setColor(0.10, 0.05, 0.02, 0.9)
    love.graphics.setLineWidth(2)
    love.graphics.circle("line", x, y, r * pulse)
end

-- ============ SATELLITE ============
function planet.draw_satellite(x, y, r, base, t)
    local rot = t * 1.5
    for side = -1, 1, 2 do
        local px = x + side * r * 1.8
        local py = y + math.sin(rot + (side>0 and 0 or math.pi)) * r * 0.5
        love.graphics.setColor(0.28, 0.38, 0.55, 0.95)
        love.graphics.rectangle("fill", px - 5, py - 2, 10, 4)
        love.graphics.setColor(0.70, 0.85, 1.0, 0.9)
        love.graphics.setLineWidth(1)
        love.graphics.rectangle("line", px - 5, py - 2, 10, 4)
    end
    draw_cel_sphere(x, y, r, base, -0.6, -0.8)
    -- antenna + blink
    local blink = math.sin(t * 4) > 0
    love.graphics.setColor(0.6, 0.6, 0.6, 1)
    love.graphics.setLineWidth(1)
    love.graphics.line(x, y - r, x, y - r * 1.5)
    love.graphics.setColor(blink and 1 or 0.4, blink and 0.25 or 0.10, 0.10, 1)
    love.graphics.circle("fill", x, y - r * 1.5, 2)
    if blink then
        love.graphics.setColor(1, 0.25, 0.25, 0.35)
        love.graphics.circle("fill", x, y - r * 1.5, 5)
    end
end

-- ============ COMET (END NODE) with orbit-following tail ============
function planet.draw_comet(x, y, r, base, t, body, samples)
    -- ── Tail: curved along the orbit path ──
    if samples and #samples > 1 then
        for i = 1, #samples - 1 do
            local s0 = samples[i]
            local s1 = samples[i+1]
            local frac = s0.t
            local width = r * (1.5 * (1 - frac) + 0.10)
            local cc = mix({0.55, 0.12, 0.72}, {0.85, 0.20, 0.30}, frac)
            love.graphics.setColor(cc[1], cc[2], cc[3], (1-frac) * 0.55)
            love.graphics.setLineWidth(math.max(1, width * 1.8))
            love.graphics.line(s0.x, s0.y, s1.x, s1.y)
            love.graphics.circle("fill", s0.x, s0.y, width)
        end
        -- Electric sparks between samples
        for i = 2, #samples - 1, 2 do
            local s = samples[i]
            local frac = s.t
            local perp_x = -(samples[i+1].y - samples[i-1].y)
            local perp_y =  (samples[i+1].x - samples[i-1].x)
            local perp_len = math.sqrt(perp_x*perp_x + perp_y*perp_y)
            if perp_len > 0.001 then perp_x, perp_y = perp_x/perp_len, perp_y/perp_len end
            local jitter = math.sin(t * 18 + i) * 4 * (1 - frac)
            local nx = s.x + perp_x * jitter
            local ny = s.y + perp_y * jitter
            love.graphics.setColor(0.85, 0.65, 1.0, (1-frac) * 0.75)
            love.graphics.setLineWidth(1)
            love.graphics.line(s.x, s.y, nx, ny)
        end
    end

    -- ── Body: dark purple core + gold cracks ──
    -- Electric glow
    for k = 4, 1, -1 do
        love.graphics.setColor(0.55, 0.25, 0.90, 0.16 / k)
        love.graphics.circle("fill", x, y, r + k * 3)
    end
    -- Dark core
    love.graphics.setColor(0.10, 0.04, 0.16, 1)
    love.graphics.circle("fill", x, y, r)
    -- Purple rim (hard)
    love.graphics.setColor(0.60, 0.30, 1.0, 1)
    love.graphics.setLineWidth(1.5)
    love.graphics.circle("line", x, y, r)
    -- Gold cracks (rotating)
    for i = 1, 6 do
        local a0 = i * math.pi / 3 + t * 1.2
        local a1 = a0 + math.pi / 5
        local x1 = x + math.cos(a0) * r * 0.90
        local y1 = y + math.sin(a0) * r * 0.90
        local x2 = x + math.cos(a1) * r * 0.55
        local y2 = y + math.sin(a1) * r * 0.55
        love.graphics.setColor(1, 0.85, 0.30, 0.55)
        love.graphics.setLineWidth(3)
        love.graphics.line(x1, y1, x2, y2)
        love.graphics.setColor(1, 1, 0.70, 0.95)
        love.graphics.setLineWidth(1.2)
        love.graphics.line(x1, y1, x2, y2)
    end
    -- Small electric arcs circling the body
    for i = 1, 4 do
        local a = t * 2.5 + i * 1.4
        local ax = x + math.cos(a) * (r + 3)
        local ay = y + math.sin(a) * (r + 3)
        local a2 = a + 0.5 + math.sin(t*15 + i) * 0.3
        local bx = x + math.cos(a2) * (r + 7)
        local by = y + math.sin(a2) * (r + 7)
        love.graphics.setColor(0.80, 0.55, 1.0, 0.85)
        love.graphics.setLineWidth(1)
        love.graphics.line(ax, ay, bx, by)
    end
end

-- ============ RINGS ============
-- Asteroid rings (FORGE): 2 diagonal bands of small rocks
local function draw_asteroid_band(x, y, r, color, t, layer, ring_idx, tilt, inner_m, outer_m, density)
    local is_back = (layer == "back")
    local speed = 0.35 * (ring_idx == 1 and 1 or -1)
    local des = desat(color, 0.20)
    for i = 1, density do
        local ang = (i / density) * math.pi * 2 + t * speed
        local dist_frac = (i * 37 % 11) / 11  -- deterministic scatter
        local dist = r * (inner_m + dist_frac * (outer_m - inner_m))
        local sin_a = math.sin(ang)
        local this_back = sin_a < 0
        if this_back == is_back then
            local ax = x + math.cos(ang) * dist
            local ay = y + sin_a * dist * tilt
            local sz = 1 + (i * 17 % 3) * 0.7
            -- Hard cel rock tones (no anti-alias gradient)
            if this_back then
                love.graphics.setColor(des[1]*0.4, des[2]*0.4, des[3]*0.4, 0.7)
            else
                love.graphics.setColor(des[1]*0.9, des[2]*0.8, des[3]*0.6, 0.95)
            end
            love.graphics.circle("fill", ax, ay, sz)
            -- Tiny highlight on front rocks
            if not this_back and sz > 1.2 then
                love.graphics.setColor(1, 0.95, 0.7, 0.7)
                love.graphics.circle("fill", ax - 0.5, ay - 0.5, sz * 0.4)
            end
        end
    end
end

local function draw_asteroid_double(x, y, r, color, t, layer)
    draw_asteroid_band(x, y, r, color, t, layer, 1, 0.50, 1.65, 2.55, 55)
    draw_asteroid_band(x, y, r, color, t, layer, 2, -0.55, 1.55, 2.35, 45)
end

-- Thin single ring (MEDIA)
local function draw_thin_ring(x, y, r, color, t, layer)
    local is_back = (layer == "back")
    local tilt = 0.35
    local rad = r * 1.85
    local steps = 50
    local c = desat(color, 0.15)
    local alpha = is_back and 0.35 or 0.85
    love.graphics.setColor(c[1], c[2], c[3], alpha)
    love.graphics.setLineWidth(is_back and 1 or 2)
    for i = 1, steps do
        local a1 = (i-1)/steps * math.pi*2
        local a2 = i/steps * math.pi*2
        local mid = (a1+a2)/2
        local this_back = math.sin(mid) < 0
        if this_back == is_back then
            love.graphics.line(
                x + math.cos(a1)*rad, y + math.sin(a1)*rad*tilt,
                x + math.cos(a2)*rad, y + math.sin(a2)*rad*tilt)
        end
    end
end

-- Thick Saturn ring (TOOLBOX)
local function draw_saturn_ring(x, y, r, color, t, layer)
    local is_back = (layer == "back")
    local tilt = 0.42
    local inner = r * 1.55
    local outer = r * 2.55
    local bands = 6
    local steps = 60
    local c = desat(color, 0.20)
    for b = 1, bands do
        local t_b = (b - 1) / (bands - 1)
        local rad = inner + t_b * (outer - inner)
        -- Cassini-like gaps (skip a band)
        local is_gap = (b == 3)
        if not is_gap then
            local alpha = (is_back and 0.30 or 0.65) * (0.75 + 0.25 * math.sin(t_b * math.pi))
            love.graphics.setColor(c[1], c[2], c[3], alpha)
            love.graphics.setLineWidth(2.5)
            for i = 1, steps do
                local a1 = (i-1)/steps * math.pi*2
                local a2 = i/steps * math.pi*2
                local mid = (a1+a2)/2
                local this_back = math.sin(mid) < 0
                if this_back == is_back then
                    love.graphics.line(
                        x + math.cos(a1)*rad, y + math.sin(a1)*rad*tilt,
                        x + math.cos(a2)*rad, y + math.sin(a2)*rad*tilt)
                end
            end
        end
    end
end

-- ============ PLANET dispatch ============
function planet.draw_planet(x, y, r, base, t, opts, body, lit_dx, lit_dy)
    opts = opts or {}
    local surface = opts.surface or "gas_bands"
    local rot = t * (opts.rot_speed or 0.6)
    local ring = opts.ring

    -- Back ring layer
    if ring == "asteroid_double" then
        draw_asteroid_double(x, y, r, base, t, "back")
    elseif ring == "thin" then
        draw_thin_ring(x, y, r, base, t, "back")
    elseif ring == "saturn_thick" then
        draw_saturn_ring(x, y, r, base, t, "back")
    end

    -- Cel shaded sphere
    draw_cel_sphere(x, y, r, base, lit_dx or -0.7, lit_dy or -0.7)

    -- Surface features
    local fn = SURFACES[surface]
    if fn and r >= 8 then fn(x, y, r, base, rot, body or {node = {idx=0}}) end

    -- Front ring layer
    if ring == "asteroid_double" then
        draw_asteroid_double(x, y, r, base, t, "front")
    elseif ring == "thin" then
        draw_thin_ring(x, y, r, base, t, "front")
    elseif ring == "saturn_thick" then
        draw_saturn_ring(x, y, r, base, t, "front")
    end

    -- Moon
    if opts.moon then
        local ma = t * 1.3
        local mr = r * 2.4
        local mx = x + math.cos(ma) * mr
        local my = y + math.sin(ma) * mr * 0.45
        local shadow = math.sin(ma) > 0
        draw_cel_sphere(mx, my, math.max(2, r*0.18),
            shadow and {0.3,0.3,0.35} or {0.8,0.8,0.85},
            -0.5, -0.7)
    end
end

return planet
