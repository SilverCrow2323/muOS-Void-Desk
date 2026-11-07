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
local orbit_offset = { [1]=0, [2]=0, [3]=0, [4]=0 }
local time = 0
local selected = 1

-- Selection flight along the arc
local sel = {
    t = 1.0,
    from_ring = 2, to_ring = 2,
    from_local = 0, to_local = 0,
    from_r = 15, to_r = 15,
}

local warp = { active=false, t=0, target_idx=nil,
               target_scene=nil, use_stub=false, quit=false }

local RING_RADII = { [1]=0, [2]=240, [3]=340, [4]=420 }
local SQUASH = 0.42

local function lerp(a, b, t) return a + (b - a) * t end

local function world_angle_of(b)
    return (b.base_angle or 0) + (orbit_offset[b.node.ring] or 0)
end

local function orbit_pos(ring, world_angle)
    local rr = RING_RADII[ring] or 240
    return 320 + math.cos(world_angle) * rr,
           240 + math.sin(world_angle) * rr * SQUASH
end

local function body_pos(b)
    return orbit_pos(b.node.ring, world_angle_of(b))
end

-- ============ SELECTION MOVEMENT ============
local function set_selection(new_idx)
    if new_idx == selected or not bodies[new_idx] then return end
    local ob = bodies[selected]
    local nb = bodies[new_idx]
    sel.from_ring = ob.node.ring
    sel.to_ring = nb.node.ring
    sel.from_local = ob.base_angle or 0
    sel.to_local = nb.base_angle or 0
    sel.from_r = ob.r
    sel.to_r = nb.r
    sel.t = 0
    selected = new_idx
end

-- LEFT/RIGHT: move along current orbit
local function move_along_orbit(dir)
    local cur = bodies[selected]
    local ring = cur.node.ring
    local same = {}
    for i, b in ipairs(bodies) do
        if b.node.ring == ring then
            table.insert(same, { idx = i, base_angle = b.base_angle or 0 })
        end
    end
    if #same < 2 then return end
    table.sort(same, function(a, b) return a.base_angle < b.base_angle end)
    local cur_pos = 1
    for k, e in ipairs(same) do
        if e.idx == selected then cur_pos = k; break end
    end
    local new_pos = cur_pos + dir
    if new_pos < 1 then new_pos = #same
    elseif new_pos > #same then new_pos = 1 end
    set_selection(same[new_pos].idx)
end

-- UP/DOWN: change ring, pick nearest-angle body
local function change_ring(dir)
    local cur_ring = bodies[selected].node.ring
    local target_ring = cur_ring + dir
    -- skip empty rings
    while target_ring >= 1 and target_ring <= 4 do
        local has = false
        for _, b in ipairs(bodies) do
            if b.node.ring == target_ring then has = true; break end
        end
        if has then break end
        target_ring = target_ring + dir
    end
    if target_ring < 1 or target_ring > 4 then return end

    local cur_local = bodies[selected].base_angle or 0
    local best, best_d = nil, math.huge
    for i, b in ipairs(bodies) do
        if b.node.ring == target_ring then
            local d = math.abs((b.base_angle or 0) - cur_local)
            if d > math.pi then d = math.pi * 2 - d end
            if d < best_d then best = i; best_d = d end
        end
    end
    if best then set_selection(best) end
end

-- ============ CYBER RETICLE ============
local function draw_cyber_reticle(x, y, r, c, t_now, enter_t, alpha)
    alpha = alpha or 1
    enter_t = anim.clamp(enter_t, 0, 1)

    if enter_t < 0.6 then
        local off = 5 * (1 - enter_t / 0.6)
        love.graphics.setColor(1, 0.15, 0.25, 0.35 * alpha)
        love.graphics.setLineWidth(1.5)
        love.graphics.circle("line", x + off, y, r + 3)
        love.graphics.setColor(0.15, 0.95, 1.0, 0.35 * alpha)
        love.graphics.circle("line", x - off, y, r + 3)
    end

    local rot = t_now * 1.4
    local reticle_r = r + 9 + 2.5 * math.sin(t_now * 3.2)
    love.graphics.setColor(c[1], c[2], c[3], 0.90 * alpha)
    love.graphics.setLineWidth(2)
    for i = 0, 3 do
        local a0 = rot + i * (math.pi / 2)
        local a1 = a0 + math.pi / 3.2
        love.graphics.arc("line", "open", x, y, reticle_r, a0, a1)
    end

    local rot2 = -t_now * 0.9
    love.graphics.setColor(c[1]*0.85, c[2]*0.85, c[3]*0.85, 0.55 * alpha)
    love.graphics.setLineWidth(1)
    for i = 0, 7 do
        local a0 = rot2 + i * (math.pi / 4)
        local a1 = a0 + math.pi / 10
        love.graphics.arc("line", "open", x, y, r + 4, a0, a1)
    end

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

    love.graphics.setLineWidth(1)
    for yy = -r, r, 3 do
        local b = 0.4 + 0.6 * math.abs(math.sin(yy*0.5 + t_now*7))
        love.graphics.setColor(c[1], c[2], c[3], 0.12 * b * alpha)
        love.graphics.line(x - r - 3, y + yy, x + r + 3, y + yy)
    end

    local gs = math.floor(t_now * 12) % 9
    if gs < 2 then
        local gy = y + math.sin(t_now * 47) * r * 0.7
        local gw = r * 2 * (0.3 + 0.5 * math.abs(math.sin(t_now * 13)))
        love.graphics.setColor(c[1], c[2], c[3], 0.75 * alpha)
        love.graphics.rectangle("fill", x - gw/2, gy, gw, 2)
    end

    if enter_t > 0.5 then
        local readout = string.format("TGT %03d  LOCK", math.floor(t_now * 7) % 999)
        love.graphics.setColor(c[1], c[2], c[3], 0.65 * alpha)
        love.graphics.print(readout, x + r + 12, y - r - 4)
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
        local base_angle = 0
        if n.type ~= "sun" then
            counters[n.ring] = (counters[n.ring] or 0) + 1
            local i_in = counters[n.ring] - 1
            local cnt = per_ring[n.ring] or 1
            base_angle = (i_in / cnt) * math.pi * 2 + (n.ring - 1) * 0.42
        end
        table.insert(out, {
            node = n,
            color = nodes.color_for(n.idx),
            base_angle = base_angle,
            r = n.size or 14,
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
            b.angle = 0
        else
            local wa = world_angle_of(b)
            b.angle = wa   -- used by comet tail direction
            b.x, b.y = orbit_pos(b.node.ring, wa)
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
    orbit_offset = { [1]=0, [2]=0, [3]=0, [4]=0 }
    compute_positions()
    sel.t = 1.0
    warp.active, warp.t = false, 0

    input.clear()
    input.on("press", function(action)
        if warp.active then
            if action == "b" or action == "menu" then warp.active=false; warp.t=0 end
            return
        end

        if action == "left"  then move_along_orbit(-1)
        elseif action == "right" then move_along_orbit(1)
        elseif action == "up"   then change_ring(-1)   -- toward center
        elseif action == "down" then change_ring(1)    -- toward outer
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
    -- Advance orbit offsets (planets drift)
    for ring = 2, 4 do
        orbit_offset[ring] = (orbit_offset[ring] or 0) + dt * (0.06 + 0.02 * (4 - ring))
    end
    compute_positions()

    if sel.t < 1.0 then
        sel.t = math.min(1.0, sel.t + dt / 0.35)
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

-- Compute current reticle position (arc-following during flight)
local function reticle_position()
    if sel.t >= 1.0 then
        local b = bodies[selected]
        return b.x, b.y, b.r
    end
    local e = anim.ease_out_cubic(sel.t)
    local ring = sel.from_ring + (sel.to_ring - sel.from_ring) * e
    local rr = lerp(RING_RADII[sel.from_ring] or 240,
                    RING_RADII[sel.to_ring] or 240, e)
    -- interpolate the WORLD angle with shortest path
    local from_world = sel.from_local + (orbit_offset[sel.from_ring] or 0)
    local to_world   = sel.to_local   + (orbit_offset[sel.to_ring] or 0)
    local d = to_world - from_world
    while d >  math.pi do d = d - math.pi * 2 end
    while d < -math.pi do d = d + math.pi * 2 end
    local world = from_world + d * e
    local x = 320 + math.cos(world) * rr
    local y = 240 + math.sin(world) * rr * SQUASH
    local r = lerp(sel.from_r, sel.to_r, e)
    return x, y, r
end

-- Trail of dots following the arc
local function draw_arc_trail(c, t_frac)
    if t_frac >= 1.0 or t_frac <= 0.02 then return end
    local steps = 8
    for i = 1, steps do
        local back = i / steps
        local tt = math.max(0, t_frac - back * 0.20)
        if tt > 0.01 then
            -- recompute the reticle at tt
            local e = anim.ease_out_cubic(tt)
            local rr = lerp(RING_RADII[sel.from_ring] or 240,
                            RING_RADII[sel.to_ring] or 240, e)
            local from_world = sel.from_local + (orbit_offset[sel.from_ring] or 0)
            local to_world   = sel.to_local   + (orbit_offset[sel.to_ring] or 0)
            local d = to_world - from_world
            while d >  math.pi do d = d - math.pi * 2 end
            while d < -math.pi do d = d + math.pi * 2 end
            local world = from_world + d * e
            local x = 320 + math.cos(world) * rr
            local y = 240 + math.sin(world) * rr * SQUASH
            local a = (1 - back) * 0.55
            love.graphics.setColor(c[1], c[2], c[3], a)
            love.graphics.setLineWidth(2)
            love.graphics.circle("line", x, y, 8)
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
        love.graphics.ellipse("line", 320, 240, rr, rr * SQUASH)
    end

    -- Sort for depth
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
        elseif b.node.type == "comet" then
            planet.draw_comet(b.x, b.y, rr, c, time, b)
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

    -- Selection reticle
    if not warp.active then
        local selb = bodies[selected]
        local cur_c = selb.color

        if sel.t < 1.0 then
            draw_arc_trail(cur_c, sel.t)
        end

        local rx, ry, rr2 = reticle_position()
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
            { icon = "dpad",  label = "Orbit / Node" },
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
