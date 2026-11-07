local sm      = require("core.scene_manager")
local theme   = require("theme.loader")
local input   = require("core.input")
local chrome  = require("core.chrome")
local effects = require("core.effects")
local font    = require("core.font")
local nodes   = require("core.nodes")
local planet  = require("core.planet")
local anim    = require("core.anim")

local nexus = {}
local bodies, stars = {}, {}
local time = 0
local selected = 1

-- Selection animation: reticle flies from OLD to NEW position
local sel = {
    from_idx = 1, to_idx = 1, t = 1.0,   -- 1.0 = settled
    from_x = 0, from_y = 0, from_r = 0,
    to_x = 0,   to_y = 0,   to_r = 0,
}
local warp = { active=false, t=0, target_idx=nil,
               target_scene=nil, use_stub=false, quit=false }

local RING_RADII = { [1]=0, [2]=240, [3]=340, [4]=420 }

-- ============ CYBERPUNK RETICLE (draws at any position) ============
local function draw_cyber_reticle(x, y, r, c, t_now, enter_t, alpha)
    alpha = alpha or 1
    enter_t = anim.clamp(enter_t, 0, 1)

    -- RGB split on entry
    if enter_t < 0.6 then
        local off = 5 * (1 - enter_t / 0.6)
        love.graphics.setColor(1, 0.15, 0.25, 0.35 * alpha)
        love.graphics.setLineWidth(1.5)
        love.graphics.circle("line", x + off, y, r + 3)
        love.graphics.setColor(0.15, 0.95, 1.0, 0.35 * alpha)
        love.graphics.circle("line", x - off, y, r + 3)
    end

    -- Rotating reticle (4 arcs, CCW)
    local rot = t_now * 1.4
    local reticle_r = r + 9 + 2.5 * math.sin(t_now * 3.2)
    love.graphics.setColor(c[1], c[2], c[3], 0.90 * alpha)
    love.graphics.setLineWidth(2)
    for i = 0, 3 do
        local a0 = rot + i * (math.pi / 2)
        local a1 = a0 + math.pi / 3.2
        love.graphics.arc("line", "open", x, y, reticle_r, a0, a1)
    end

    -- CW dashed inner ring
    local rot2 = -t_now * 0.9
    love.graphics.setColor(c[1]*0.85, c[2]*0.85, c[3]*0.85, 0.55 * alpha)
    love.graphics.setLineWidth(1)
    for i = 0, 7 do
        local a0 = rot2 + i * (math.pi / 4)
        local a1 = a0 + math.pi / 10
        love.graphics.arc("line", "open", x, y, r + 4, a0, a1)
    end

    -- Corner brackets
    if enter_t > 0.3 then
        local bt = (enter_t - 0.3) / 0.7
        local arm = 10 * bt
        local off = r + 8
        love.graphics.setColor(c[1], c[2], c[3], alpha)
        love.graphics.setLineWidth(2.5)
        for sx = -1, 1, 2 do
            for sy = -1, 1, 2 do
                local bx = x + sx * off
                local by = y + sy * off
                love.graphics.line(bx - sx*arm, by, bx, by)
                love.graphics.line(bx, by - sy*arm, bx, by)
            end
        end
    end

    -- Scanlines
    love.graphics.setLineWidth(1)
    for yy = -r, r, 3 do
        local b = 0.4 + 0.6 * math.abs(math.sin(yy*0.5 + t_now*7))
        love.graphics.setColor(c[1], c[2], c[3], 0.12 * b * alpha)
        love.graphics.line(x - r - 3, y + yy, x + r + 3, y + yy)
    end

    -- Glitch bar
    local gs = math.floor(t_now * 12) % 9
    if gs < 2 then
        local gy = y + math.sin(t_now * 47) * r * 0.7
        local gw = r * 2 * (0.3 + 0.5 * math.abs(math.sin(t_now * 13)))
        love.graphics.setColor(c[1], c[2], c[3], 0.75 * alpha)
        love.graphics.rectangle("fill", x - gw/2, gy, gw, 2)
    end

    -- Data readout
    if enter_t > 0.5 then
        local readout = string.format("TGT %03d  LOCK", math.floor(t_now * 7) % 999)
        love.graphics.setColor(c[1], c[2], c[3], 0.65 * alpha)
        love.graphics.print(readout, x + r + 12, y - r - 4)
    end
end

-- ============ TRAIL of dots from old to new position ============
local function draw_selection_trail(sel, c, t_frac)
    if t_frac >= 1.0 or t_frac <= 0.01 then return end
    local steps = 6
    for i = 0, steps do
        local f = i / steps
        local trail_frac = math.max(0, t_frac - f * 0.12)
        if trail_frac > 0 then
            local tt = anim.ease_out_cubic(trail_frac)
            local x = sel.from_x + (sel.to_x - sel.from_x) * tt
            local y = sel.from_y + (sel.to_y - sel.from_y) * tt
            local r = sel.from_r + (sel.to_r - sel.from_r) * tt
            local a = (1 - f / steps) * 0.65
            love.graphics.setColor(c[1], c[2], c[3], a)
            love.graphics.setLineWidth(2)
            love.graphics.circle("line", x, y, r + 6)
        end
    end
end

-- ============ BUILD ============
local function build_bodies()
    local list = nodes.visible()
    local per_ring, counters = {}, {}
    for _, n in ipairs(list) do
        if n.type ~= "sun" then per_ring[n.ring] = (per_ring[n.ring] or 0) + 1 end
    end
    local out = {}
    for _, n in ipairs(list) do
        local angle = 0
        if n.type ~= "sun" then
            counters[n.ring] = (counters[n.ring] or 0) + 1
            local i_in = counters[n.ring] - 1
            local cnt = per_ring[n.ring] or 1
            angle = (i_in / cnt) * math.pi * 2 + (n.ring - 1) * 0.42
        end
        table.insert(out, {
            node = n, color = nodes.color_for(n.idx),
            angle = angle, r = n.size or 14,
            icon = nodes.image_for(n.icon),
            x = 320, y = 240,
        })
    end
    return out
end

local function compute_positions()
    for _, b in ipairs(bodies) do
        if b.node.type == "sun" then
            b.x, b.y = 320, 240
        else
            local rr = RING_RADII[b.node.ring] or 240
            b.x = 320 + math.cos(b.angle) * rr
            b.y = 240 + math.sin(b.angle) * rr * 0.42
        end
    end
end

-- ============ ENTER / UPDATE / DRAW ============
function nexus.enter(args)
    time = 0
    selected = (args and args.selected) or 1
    math.randomseed(77)
    stars = {}
    for i = 1, 200 do
        stars[i] = {
            x = math.random() * 640, y = 44 + math.random() * 400,
            phase = math.random() * 6.28,
            size = 0.6 + math.random() * 1.4,
            col = ({ {0.85,0.90,1.00}, {0.70,0.80,1.00},
                     {1.00,0.95,0.85} })[math.random(1,3)],
        }
    end
    bodies = build_bodies()
    compute_positions()
    sel.t = 1.0
    sel.from_idx = selected; sel.to_idx = selected
    warp.active, warp.t = false, 0

    input.clear()
    input.on("press", function(action)
        if warp.active then
            if action == "b" or action == "menu" then warp.active=false; warp.t=0 end
            return
        end

        local function move_selection(new_idx)
            if new_idx == selected then return end
            -- capture OLD position and radius
            local ob = bodies[selected]
            local nb = bodies[new_idx]
            sel.from_idx = selected
            sel.to_idx = new_idx
            sel.from_x = ob.x; sel.from_y = ob.y; sel.from_r = ob.r
            sel.to_x = nb.x;   sel.to_y = nb.y;   sel.to_r = nb.r
            sel.t = 0
            selected = new_idx
        end

        if action == "up" or action == "left" then
            move_selection(math.max(1, selected - 1))
        elseif action == "down" or action == "right" then
            move_selection(math.min(#bodies, selected + 1))
        elseif action == "a" then
            local b = bodies[selected]
            warp.active = true; warp.t = 0
            warp.target_idx = b.node.idx
            local sc = b.node.scene
            if sc == "quit" then
                warp.quit=true; warp.use_stub=false; warp.target_scene=nil
            elseif sc and sc ~= "" then
                warp.target_scene = sc; warp.use_stub=false; warp.quit=false
            else
                warp.target_scene = "hub_stub"; warp.use_stub=true; warp.quit=false
            end
        elseif action == "b" or action == "menu" then
            love.event.quit()
        end
    end)
end

function nexus.update(dt)
    time = time + dt
    for _, b in ipairs(bodies) do
        if b.node.type ~= "sun" then
            local step = dt * (0.06 + 0.02 * (4 - b.node.ring)) * (b.node.orbit_mult or 1)
            b.angle = b.angle + step
        end
    end
    compute_positions()

    -- selection flight: update positions live so reticle follows the moving body
    if sel.t < 1.0 then
        sel.t = math.min(1.0, sel.t + dt / 0.32)
        local tb = bodies[sel.to_idx]
        sel.to_x = tb.x; sel.to_y = tb.y; sel.to_r = tb.r
    end

    if warp.active then
        warp.t = warp.t + dt / 0.7
        if warp.t >= 1.0 then
            if warp.quit then love.event.quit()
            elseif warp.target_scene then
                local ok, mod = pcall(require, "scenes." .. warp.target_scene)
                if ok and mod then
                    sm.register(warp.target_scene, mod)
                    sm.switch(warp.target_scene, { idx = warp.target_idx })
                end
            end
            warp.active = false; warp.t = 0
        end
    end
end

function nexus.draw()
    local W, H = love.graphics.getDimensions()
    local th = theme.get()

    local warp_dim = warp.active and (0.4 + 0.6 * warp.t) or 1.0
    love.graphics.clear(th.bg[1]*warp_dim, th.bg[2]*warp_dim, th.bg[3]*warp_dim, 1)

    -- Stars
    for _, s in ipairs(stars) do
        local tw = 0.3 + 0.7 * math.abs(math.sin(time * 1.3 + s.phase))
        love.graphics.setColor(s.col[1], s.col[2], s.col[3], tw * warp_dim)
        love.graphics.circle("fill", s.x, s.y, s.size)
    end

    -- Orbits
    love.graphics.setLineWidth(1.5)
    for ring = 2, 4 do
        local rr = RING_RADII[ring]
        love.graphics.setColor(th.orbit_color[1], th.orbit_color[2],
                               th.orbit_color[3], 0.35 * warp_dim)
        love.graphics.ellipse("line", 320, 240, rr, rr * 0.42)
    end

    -- Sort bodies (outer first for depth)
    local sorted = {}
    for _, b in ipairs(bodies) do table.insert(sorted, b) end
    table.sort(sorted, function(a, b)
        if a.node.type == "sun" then return true end
        if b.node.type == "sun" then return false end
        return a.node.ring > b.node.ring
    end)

    for _, b in ipairs(sorted) do
        local real_sel = (bodies[selected] == b)
        local scl = 1.0
        if real_sel and warp.active then scl = 1.0 + warp.t * 2.2 end
        local vis_alpha = 1.0
        if warp.active and not real_sel then
            vis_alpha = math.max(0, 1.0 - warp.t * 1.6)
        end
        if vis_alpha <= 0.02 then goto continue end

        local c = b.color
        local rr = b.r * scl

        if b.node.type == "sun" then
            planet.draw_sun(b.x, b.y, rr, c, time)
        elseif b.node.type == "satellite" then
            planet.draw_satellite(b.x, b.y, rr, c, time)
        else
            planet.draw_planet(b.x, b.y, rr, c, time, {
                ring = b.node.ring_kind,
                ring_tilt = b.node.ring_tilt,
                moon = b.node.moon,
                rot_speed = b.node.rot_speed,
                surface = b.node.surface or "gas_bands",
            }, b)
        end

        if b.icon and b.node.type ~= "sun" then
            local sz = b.r * 0.75
            local s = sz / b.icon:getWidth()
            love.graphics.setColor(1, 1, 1, 0.42 * vis_alpha)
            love.graphics.draw(b.icon, b.x - b.icon:getWidth()*s/2,
                                       b.y - b.icon:getHeight()*s/2, 0, s, s)
        end

        ::continue::
    end

    -- Selection trail + reticle
    if not warp.active then
        local selb = bodies[selected]
        local cur_c = selb.color

        -- Flying trail from old position
        if sel.t < 1.0 then
            draw_selection_trail(sel, cur_c, sel.t)
        end

        -- Reticle: interpolate position during flight, snap when settled
        local rx, ry, rr2
        if sel.t < 1.0 then
            local e = anim.ease_out_cubic(sel.t)
            rx = sel.from_x + (sel.to_x - sel.from_x) * e
            ry = sel.from_y + (sel.to_y - sel.from_y) * e
            rr2 = sel.from_r + (sel.to_r - sel.from_r) * e
        else
            rx, ry, rr2 = selb.x, selb.y, selb.r
        end

        local enter_t = (sel.t < 1.0) and sel.t or 1.0
        local fade_in = math.min(1.0, sel.t * 2.0)
        draw_cyber_reticle(rx, ry, rr2, cur_c, time, enter_t, fade_in)
    end

    -- Label
    if not warp.active and sel.t >= 1.0 then
        local selb = bodies[selected]
        local f_label = font.bold(14) or love.graphics.newFont(14)
        love.graphics.setFont(f_label)
        local label = selb.node.name
        local tw = f_label:getWidth(label)
        local lx = selb.x - tw / 2
        local ly = selb.y + selb.r + 32
        love.graphics.setColor(0, 0, 0, 0.65)
        love.graphics.print(label, lx + 1, ly + 1)
        love.graphics.setColor(selb.color[1], selb.color[2], selb.color[3], 1)
        love.graphics.print(label, lx, ly)
    end

    -- Chrome
    chrome.draw_header({
        theme = th, title = "Void-DESK", subtitle = "NEXUS",
        status_icons = { "signal", "wifi", "bluetooth", "battery" },
    })
    chrome.draw_footer({
        theme = th,
        hints = {
            { icon = "dpad",  label = "Navigate" },
            { icon = "btn_a", label = "Open" },
            { icon = "btn_b", label = "Quit" },
        },
        right_text = "v10.5.1",
    })

    if th.scanlines then effects.scanlines(W, H, 0.06) end
    if th.vignette  then effects.vignette(W, H, 0.4) end
    love.graphics.setColor(1, 1, 1, 1)
end

return nexus
