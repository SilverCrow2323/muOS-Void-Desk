-- ============================================================================
--  VOIDDESK // crt_shader
--  One cheap GPU post-process pass composited over the ENTIRE rendered
--  frame. Every scene in the app gets it for free — main.lua just routes
--  sm.draw() through M.frame() once.
--
--  v2: fixes two real bugs from v1 reported on-device —
--  1) "too blurry" — the composite canvas was being sampled with LÖVE's
--     default LINEAR filter. For a 1:1, unscaled pass that just softens
--     every bit of text/icon in the app for no reason; forced to NEAREST.
--  2) a draw-time error anywhere in the scene (e.g. the unrelated
--     dashboard_screen.lua crash) was caught by the outer pcall, then
--     v1 called draw_fn() a SECOND time outside any pcall as a
--     "fallback" — which just threw again and crashed anyway. Now
--     draw_fn() runs exactly once, unprotected, so a real scene bug
--     surfaces exactly like it would with no shader pass at all; only
--     the shader/canvas plumbing around it is guarded.
--
--  Reads data/desk_config.json -> crt_fx (its own key, decoupled from
--  the pygame-only nexus_bg.* flags) so the Settings > Display FX
--  submenu (scenes/hub_display_fx.lua) can tune it live.
-- ============================================================================
local config = require("core.config")

local M = {}
local shader
local canvas
local t = 0
local enabled = true

local SRC = [[
extern number u_time;
extern number u_scan;       // 0..1 scanline strength
extern number u_vignette;   // 0..1 vignette strength
extern number u_glitch;     // 0 or 1
extern number u_aberr;      // 0..1 chromatic aberration strength
extern vec2   u_resolution;

vec4 effect(vec4 color, Image tex, vec2 uv, vec2 screen_coords) {
    vec2 muv = uv;

    if (u_glitch > 0.5) {
        float band = floor(uv.y * 60.0 + u_time * 5.0);
        float n = fract(sin(band * 12.9898) * 43758.5453);
        if (n > 0.975) {
            muv.x += (n - 0.975) * 4.0;
        }
    }

    vec4 base;
    if (u_aberr > 0.001) {
        float aberr = 0.0022 * u_aberr;
        float r = Texel(tex, clamp(muv + vec2(aberr, 0.0), 0.0, 1.0)).r;
        float g = Texel(tex, muv).g;
        float b = Texel(tex, clamp(muv - vec2(aberr, 0.0), 0.0, 1.0)).b;
        base = vec4(r, g, b, 1.0);
    } else {
        base = Texel(tex, muv);
    }

    // scanlines — gentle, never darker than ~92%
    float sl = sin(uv.y * u_resolution.y * 3.14159265) * 0.5 + 0.5;
    base.rgb *= mix(1.0, 0.92 + 0.08 * sl, u_scan);

    // vignette — soft, floor at 55% instead of crushing the corners
    vec2 c = uv - vec2(0.5, 0.5);
    float vig = 1.0 - dot(c, c) * 0.65;
    base.rgb *= mix(1.0, clamp(vig, 0.55, 1.0), u_vignette);

    return base * color;
}
]]

local function defaults()
    return { scanlines = true, vignette = true, glitch = false, aberration = 0 }
end

function M.init()
    local ok, sh = pcall(love.graphics.newShader, SRC)
    shader = ok and sh or nil
    if not ok and os.getenv("VOIDDESK_DEBUG_INPUT") == "1" then
        print("[crt_shader] compile failed, falling back to plain draw: "
              .. tostring(sh))
    end

    local ok2, cv = pcall(love.graphics.newCanvas, love.graphics.getDimensions())
    if ok2 then
        cv:setFilter("nearest", "nearest")  -- kill resample blur, see header note
        canvas = cv
    else
        canvas = nil
    end
end

function M.set_enabled(v) enabled = v and true or false end
function M.is_enabled() return enabled end

-- current settings, for the Settings > Display FX submenu to read/cycle
function M.get_fx() return config.get("crt_fx", defaults()) end
function M.set_fx(fx) config.set("crt_fx", fx) end

function M.frame(dt, draw_fn)
    t = t + (dt or 0)
    if not enabled or not shader or not canvas then
        draw_fn()
        return
    end

    local prev = love.graphics.getCanvas()
    local setup_ok = pcall(function()
        love.graphics.setCanvas(canvas)
        love.graphics.clear(0, 0, 0, 1)
    end)
    if not setup_ok then
        pcall(love.graphics.setCanvas, prev)
        draw_fn()
        return
    end

    -- Runs exactly once, unprotected: a bug in the scene itself must
    -- surface exactly as it would without this shader pass at all.
    draw_fn()

    local composite_ok = pcall(function()
        love.graphics.setCanvas(prev)
        local fx = M.get_fx()
        local lvl = tonumber(fx.aberration) or 0  -- 0, 1 (low) or 2 (med)

        love.graphics.setShader(shader)
        shader:send("u_time", t)
        shader:send("u_scan", (fx.scanlines ~= false) and 1.0 or 0.0)
        shader:send("u_vignette", (fx.vignette ~= false) and 1.0 or 0.0)
        shader:send("u_glitch", (fx.glitch == true) and 1.0 or 0.0)
        shader:send("u_aberr", lvl <= 0 and 0.0 or (lvl == 1 and 0.4 or 0.8))
        shader:send("u_resolution", {canvas:getDimensions()})
        love.graphics.setColor(1, 1, 1, 1)
        love.graphics.draw(canvas, 0, 0)
        love.graphics.setShader()
    end)
    if not composite_ok then
        -- the scene is already safely drawn in `canvas` at this point;
        -- just blit it plainly instead of losing the frame
        love.graphics.setShader()
        pcall(love.graphics.setCanvas, prev)
        pcall(love.graphics.draw, canvas, 0, 0)
    end
end

return M
