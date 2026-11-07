-- Procedural planet rendering: rotating bodies, rings, moons, sun, satellite
local planet = {}

local function mix(c1, c2, t)
    return { c1[1] * (1-t) + c2[1] * t,
             c1[2] * (1-t) + c2[2] * t,
             c1[3] * (1-t) + c2[3] * t }
end

local function shade(c, f)
    return { math.max(0, c[1]*f), math.max(0, c[2]*f), math.max(0, c[3]*f) }
end

-- ============ SUN (START SESSION) ============
function planet.draw_sun(x, y, r, base, t)
    local pulse = 0.90 + 0.10 * math.sin(t * 1.8)

    -- Outer corona: multiple expanding layers
    for k = 6, 1, -1 do
        local c = mix(base, {1, 0.5, 0.1}, 0.3)
        love.graphics.setColor(c[1], c[2], c[3], 0.05 + 0.03 * math.sin(t*2 + k))
        love.graphics.circle("fill", x, y, r * (1 + k * 0.28) * pulse)
    end

    -- Rotating prominences / flares
    for i = 1, 14 do
        local ang = (i / 14) * math.pi * 2 + t * 0.6
        local fl = r + 6 + 10 * math.abs(math.sin(t * 2.2 + i * 0.9))
        local flare_c = mix(base, {1, 0.85, 0.4}, 0.5)
        love.graphics.setColor(flare_c[1], flare_c[2], flare_c[3], 0.55)
        love.graphics.setLineWidth(2)
        love.graphics.line(
            x + math.cos(ang) * (r * 0.95), y + math.sin(ang) * (r * 0.95),
            x + math.cos(ang) * fl, y + math.sin(ang) * fl)
    end

    -- Core layers with color depth
    for k = 3, 1, -1 do
        local c = mix(base, {1, 1, 0.85}, 0.35 / k)
        love.graphics.setColor(c[1], c[2], c[3], 0.95)
        love.graphics.circle("fill", x, y, r * pulse * (1 - (k-1) * 0.08))
    end

    -- Bright inner highlight
    love.graphics.setColor(1, 1, 0.9, 0.9)
    love.graphics.circle("fill", x - r * 0.22, y - r * 0.22, r * 0.35)

    -- Sunspots (slow drift = rotation)
    local spot_ang = t * 0.4
    for i = 1, 3 do
        local a = spot_ang + i * 2.1
        local sx = x + math.cos(a) * r * 0.5
        local sy = y + math.sin(a) * r * 0.25
        if math.cos(a) > 0 then -- front side
            love.graphics.setColor(0.6, 0.3, 0.1, 0.5)
            love.graphics.circle("fill", sx, sy, r * 0.08)
        end
    end
end

-- ============ PLANET (rotating) ============
function planet.draw_planet(x, y, r, base, t, opts)
    opts = opts or {}
    local ring_kind = opts.ring
    local ring_tilt = opts.ring_tilt or 0.35
    local moon = opts.moon
    local rot = opts.rot_speed or 0.6

    -- 1) Back half of ring (behind planet)
    if ring_kind then
        planet._ring_arc(x, y, r, ring_kind, ring_tilt, base, true)
    end

    -- 2) Planet body base (dark)
    local dark = shade(base, 0.30)
    love.graphics.setColor(dark[1], dark[2], dark[3], 1)
    love.graphics.circle("fill", x, y, r)

    -- 3) Surface bands (rotate across the surface)
    if r >= 10 then
        for band = 1, 5 do
            local yy = -r * 0.9 + (band / 6) * r * 1.8
            local phase = t * rot + band * 0.7
            local bx = math.sin(phase) * r * 0.45
            local bw = math.sqrt(math.max(1, r*r - yy*yy))
            local bc = shade(base, 0.55 + 0.20 * math.sin(phase * 1.4))
            love.graphics.setColor(bc[1], bc[2], bc[3], 0.75)
            love.graphics.ellipse("fill", x + bx, y + yy,
                                  bw * 0.85, r * 0.14)
        end
    end

    -- 4) Light side (top-left) + moving highlight spot
    local light = mix(base, {1, 1, 1}, 0.30)
    love.graphics.setColor(light[1], light[2], light[3], 0.70)
    love.graphics.circle("fill", x - r * 0.30, y - r * 0.30, r * 0.55)

    -- Rotation-visible surface spot
    local spot_a = t * rot
    local sx = x + math.cos(spot_a) * r * 0.42
    local sy = y + math.sin(spot_a * 0.7) * r * 0.28
    if math.cos(spot_a) > 0 then
        love.graphics.setColor(1, 1, 1, 0.30)
        love.graphics.circle("fill", sx, sy, r * 0.11)
    end

    -- 5) Dark crescent (bottom-right, away from sun direction)
    love.graphics.setColor(dark[1], dark[2], dark[3], 0.55)
    love.graphics.circle("fill", x + r * 0.55, y + r * 0.55, r * 0.88)

    -- 6) Thin bright edge
    love.graphics.setColor(light[1], light[2], light[3], 0.35)
    love.graphics.setLineWidth(1)
    love.graphics.circle("line", x, y, r)

    -- 7) Front half of ring (in front of planet)
    if ring_kind then
        planet._ring_arc(x, y, r, ring_kind, ring_tilt, base, false)
    end

    -- 8) Moon (orbiting)
    if moon then
        local moon_a = t * 1.3
        local mr = r * 2.4
        local mx = x + math.cos(moon_a) * mr
        local my = y + math.sin(moon_a) * mr * 0.45
        if math.sin(moon_a) > 0 then -- behind
            love.graphics.setColor(0.55, 0.55, 0.60, 0.7)
            love.graphics.circle("fill", mx, my, math.max(2, r * 0.16))
        else
            love.graphics.setColor(0.85, 0.85, 0.90, 1)
            love.graphics.circle("fill", mx, my, math.max(2, r * 0.20))
            love.graphics.setColor(0.55, 0.55, 0.60, 1)
            love.graphics.circle("fill", mx + 1, my + 1, math.max(1, r * 0.12))
        end
    end
end

-- ============ SATELITE (MUOS APPS) ============
function planet.draw_satellite(x, y, r, base, t)
    local light = mix(base, {1, 1, 1}, 0.35)
    local dark = shade(base, 0.4)
    local rot = t * 1.5

    -- Solar panels (oscillate as satellite spins)
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
        -- Panel segments
        love.graphics.line(px - 1, py - 2, px - 1, py + 2)
        love.graphics.line(px + 1, py - 2, px + 1, py + 2)
    end

    -- Body
    love.graphics.setColor(dark[1], dark[2], dark[3], 1)
    love.graphics.circle("fill", x, y, r)
    love.graphics.setColor(light[1], light[2], light[3], 1)
    love.graphics.circle("fill", x - r * 0.25, y - r * 0.25, r * 0.70)

    -- Antenna blinking light
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

-- ============ RING ARCS ============
function planet._ring_arc(x, y, r, kind, tilt, color, back)
    local inner = (kind == "double") and r * 1.30 or r * 1.45
    local outer = (kind == "double") and r * 2.60 or r * 2.20

    local c
    if kind == "signal" then
        c = mix(color, {0.2, 0.95, 1.0}, 0.55)
    elseif kind == "double" then
        c = mix(color, {1.0, 0.7, 0.9}, 0.25)
    else
        c = mix(color, {0.85, 0.65, 0.40}, 0.35)
    end
    local alpha = back and 0.35 or 0.78

    local steps = 44
    local function ring_pass(rad, width, a_mult)
        love.graphics.setColor(c[1], c[2], c[3], alpha * a_mult)
        love.graphics.setLineWidth(width)
        for i = 1, steps do
            local a1 = (i - 1) / steps * math.pi * 2
            local a2 = i / steps * math.pi * 2
            local mid = (a1 + a2) / 2
            local is_back = math.sin(mid) < 0
            if is_back == back then
                local x1 = x + math.cos(a1) * rad
                local y1 = y + math.sin(a1) * rad * tilt
                local x2 = x + math.cos(a2) * rad
                local y2 = y + math.sin(a2) * rad * tilt
                love.graphics.line(x1, y1, x2, y2)
            end
        end
    end

    -- Main ring
    ring_pass((inner + outer) / 2, back and 2 or 3, 1.0)
    -- Inner edge
    ring_pass(inner, back and 1 or 2, 0.7)
    -- Outer edge
    ring_pass(outer, back and 1 or 2, 0.7)

    -- Double ring: extra inner band with gap (Cassini style)
    if kind == "double" then
        ring_pass(inner * 0.65, back and 1 or 2, 0.55)
    end
end

return planet
