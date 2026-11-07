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

local sel_anim = { t = 1.0 }
local warp = { active = false, t = 0, target_idx = nil,
               target_scene = nil, use_stub = false, quit = false }

local RING_RADII = { [1] = 0, [2] = 240, [3] = 340, [4] = 420 }
-- SUN sits at center (0). Ring 2 planets at 240, ring 3 at 340.

-- ============================================================
--  Cyberpunk selection overlay
-- ============================================================
local function draw_cyber_selection(x, y, r, c, t_now, t_enter)
    local t = anim.clamp(t_enter, 0, 1)

    -- 1) RGB split ghosts (only during entry, first 400ms)
    if t < 0.6 then
        local off = 5 * (1 - t / 0.6)
        love.graphics.setColor(1, 0.15, 0.25, 0.35)
        love.graphics.setLineWidth(1.5)
        love.graphics.circle("line", x + off, y, r + 3)
        love.graphics.setColor(0.15, 0.95, 1.0, 0.35)
        love.graphics.circle("line", x - off, y, r + 3)
    end

    -- 2) Rotating reticle (4 arcs, counter-rotate)
    local rot = t_now * 1.4
    local reticle_r = r + 9 + 2.5 * math.sin(t_now * 3.2)
    love.graphics.setColor(c[1], c[2], c[3], 0.90)
    love.graphics.setLineWidth(2)
    for i = 0, 3 do
        local a0 = rot + i * (math.pi / 2)
        local a1 = a0 + math.pi / 3.2
        love.graphics.arc("line", "open", x, y, reticle_r, a0, a1)
    end

    -- 3) Counter-rotating inner ring (dashed)
    local rot2 = -t_now * 0.9
    love.graphics.setColor(c[1] * 0.85, c[2] * 0.85, c[3] * 0.85, 0.55)
    love.graphics.setLineWidth(1)
    for i = 0, 7 do
        local a0 = rot2 + i * (math.pi / 4)
        local a1 = a0 + math.pi / 10
        love.graphics.arc("line", "open", x, y, r + 4, a0, a1)
    end

    -- 4) Corner brackets (animate in after t=0.3)
    if t > 0.3 then
        local bt = (t - 0.3) / 0.7
        local arm = 10 * bt
        local off = r + 8
        love.graphics.setColor(c[1], c[2], c[3], 1)
        love.graphics.setLineWidth(2.5)
        for sx = -1, 1, 2 do
            for sy = -1, 1, 2 do
                local bx = x + sx * off
                local by = y + sy * off
                love.graphics.line(bx - sx * arm, by, bx, by)
                love.graphics.line(bx, by - sy * arm, bx, by)
            end
        end
    end

    -- 5) Scanning lines sweeping over the planet
    love.graphics.setLineWidth(1)
    for yy = -r, r, 3 do
        local b = 0.4 + 0.6 * math.abs(math.sin(yy * 0.5 + t_now * 7))
        love.graphics.setColor(c[1], c[2], c[3], 0.12 * b)
        love.graphics.line(x - r - 3, y + yy, x + r + 3, y + yy)
    end

    -- 6) Periodic glitch bar
    local gs = math.floor(t_now * 12) % 9
    if gs < 2 then
        local gy = y + math.sin(t_now * 47) * r * 0.7
        local gw = r * 2 * (0.3 + 0.5 * math.abs(math.sin(t_now * 13)))
        love.graphics.setColor(c[1], c[2], c[3], 0.75)
        love.graphics.rectangle("fill", x - gw / 2, gy, gw, 2)
    end

    -- 7) Data readout (flickering)
    if t > 0.5 then
        local readout = string.format("TGT %03d  LOCK", math.floor(t_now * 7) % 999)
        love.graphics.setColor(c[1], c[2], c[3], 0.65)
        love.graphics.print(readout, x + r + 12, y - r - 4)
    end
end

-- ============================================================
--  Build body list from nodes.visible()
-- ============================================================
local function build_bodies()
    local list = nodes.visible()
    local per_ring, counters = {}, {}
    for _, n in ipairs(list) do
        if n.type ~= "sun" then
            per_ring[n.ring] = (per_ring[n.ring] or 0) + 1
        end
    end
    local out = {}
    for _, n in ipairs(list) do
        local r = n.size or 14
        local angle = 0
        if n.type == "sun" then
            angle = 0
        else
            counters[n.ring] = (counters[n.ring] or 0) + 1
            local i_in = counters[n.ring] - 1
            local cnt = per_ring[n.ring] or 1
            angle = (i_in / cnt) * math.pi * 2 + (n.ring - 1) * 0.42
        end
        table.insert(out, {
            node = n,
            color = nodes.color_for(n.idx),
            angle = angle,
            r = r,
            icon = nodes.image_for(n.icon),
            x = 320, y = 240,  -- filled each frame
        })
    end
    return out
end

-- ============================================================
--  enter / update / draw
-- ============================================================
function nexus.enter(args)
    time = 0
    selected = (args and args.selected) or 1
    math.randomseed(77)
    stars = {}
    for i = 1, 200 do
        stars[i] = {
            x = math.random() * 640,
            y = 44 + math.random() * 400,
            phase = math.random() * 6.28,
            size = 0.6 + math.random() * 1.4,
            col = ({ {0.85,0.90,1.00}, {0.70,0.80,1.00},
                     {1.00,0.95,0.85} })[math.random(1,3)],
        }
    end
    bodies = build_bodies()
    sel_anim = { t = 1.0 }
    warp.active, warp.t, warp.target_scene = false, 0, nil

    input.clear()
    input.on("press", function(action)
        if warp.active then
            if action == "b" or action == "menu" then
                warp.active = false; warp.t = 0
            end
            return
        end
        if action == "up" or action == "left" then
            local old = selected
            selected = math.max(1, selected - 1)
            if selected ~= old then sel_anim = { t = 0 } end
        elseif action == "down" or action == "right" then
            local old = selected
            selected = math.min(#bodies, selected + 1)
            if selected ~= old then sel_anim = { t = 0 } end
        elseif action == "a" then
            local b = bodies[selected]
            warp.active = true; warp.t = 0
            warp.target_idx = b.node.idx
            local scene = b.node.scene
            if scene == "quit" then
                warp.quit = true; warp.use_stub = false; warp.target_scene = nil
            elseif scene and scene ~= "" then
                warp.target_scene = scene; warp.use_stub = false; warp.quit = false
            else
                warp.target_scene = "hub_stub"; warp.use_stub = true; warp.quit = false
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
            local rr = RING_RADII[b.node.ring] or 240
            local step = dt * (0.06 + 0.02 * (4 - b.node.ring)) * (b.node.orbit_mult or 1)
            b.angle = b.angle + step
        end
    end
    if sel_anim.t < 1.0 then
        sel_anim.t = math.min(1.0, sel_anim.t + dt / 0.35)
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

    -- Compute body positions
    for _, b in ipairs(bodies) do
        if b.node.type == "sun" then
            b.x, b.y = 320, 240
        else
            local rr = RING_RADII[b.node.ring] or 240
            b.x = 320 + math.cos(b.angle) * rr
            b.y = 240 + math.sin(b.angle) * rr * 0.42
        end
    end

    local warp_dim = warp.active and (0.4 + 0.6 * warp.t) or 1.0
    love.graphics.clear(th.bg[1] * warp_dim, th.bg[2] * warp_dim,
                        th.bg[3] * warp_dim, 1)

    -- 1) Stars
    for _, s in ipairs(stars) do
        local tw = 0.3 + 0.7 * math.abs(math.sin(time * 1.3 + s.phase))
        love.graphics.setColor(s.col[1], s.col[2], s.col[3], tw * warp_dim)
        love.graphics.circle("fill", s.x, s.y, s.size)
    end

    -- 2) Orbits
    love.graphics.setLineWidth(1.5)
    for ring = 2, 4 do
        local rr = RING_RADII[ring]
        love.graphics.setColor(th.orbit_color[1], th.orbit_color[2],
                               th.orbit_color[3], 0.35 * warp_dim)
        love.graphics.ellipse("line", 320, 240, rr, rr * 0.42)
    end

    -- 3) Bodies (sort by ring so outer draws first for depth)
    local sorted = {}
    for _, b in ipairs(bodies) do
        table.insert(sorted, b)
    end
    table.sort(sorted, function(a, b)
        -- sun at center draws first
        if a.node.type == "sun" then return true end
        if b.node.type == "sun" then return false end
        return a.node.ring > b.node.ring
    end)

    for idx, b in ipairs(sorted) do
        -- Warp scaling (only for the selected body)
        local real_sel = bodies[selected] == b
        local scl = 1.0
        if real_sel and warp.active then
            scl = 1.0 + warp.t * 2.2
        end
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
            })
        end

        -- Colored dot icon at planet surface (identity marker)
        if b.icon and b.node.type ~= "sun" then
            local icon_size = b.r * 0.75
            local s = icon_size / b.icon:getWidth()
            love.graphics.setColor(1, 1, 1, 0.45 * vis_alpha)
            love.graphics.draw(b.icon,
                b.x - b.icon:getWidth() * s / 2,
                b.y - b.icon:getHeight() * s / 2, 0, s, s)
        end

        -- Selection decoration (cyberpunk)
        if real_sel and not warp.active and sel_anim.t > 0 then
            draw_cyber_selection(b.x, b.y, rr, c, time, sel_anim.t)
        end

        ::continue::
    end

    -- 4) Label of selected
    if not warp.active then
        local sel = bodies[selected]
        local f_label = font.bold(14) or love.graphics.newFont(14)
        love.graphics.setFont(f_label)
        local label = sel.node.name
        local tw = f_label:getWidth(label)
        local lx = sel.x - tw / 2
        local ly = sel.y + sel.r + 32
        love.graphics.setColor(0, 0, 0, 0.65)
        love.graphics.print(label, lx + 1, ly + 1)
        love.graphics.setColor(sel.color[1], sel.color[2], sel.color[3], 1)
        love.graphics.print(label, lx, ly)
    end

    -- 5) Chrome
    chrome.draw_header({
        theme = th,
        title = "Void-DESK", subtitle = "NEXUS",
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
