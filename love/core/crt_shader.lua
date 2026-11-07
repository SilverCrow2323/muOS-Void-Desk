-- CRT shader effect: scanlines + chromatic aberration + vignette.
-- Loaded optionally by main.lua. Provides:
--   crt.load()       — compile shader (returns true/false)
--   crt.apply(canvas) — draw canvas through shader onto screen
--   crt.enabled      — bool flag (user can toggle)
local crt = {}

crt.enabled = true
crt.shader = nil
crt.loaded = false

local SHADER_SRC = [[
extern number time;
extern number scanline_alpha;
extern number aberration;
extern number vignette;
extern vec2 resolution;

vec4 effect(vec4 color, Image tex, vec2 texcoord, vec2 screen_coord) {
    // Chromatic aberration: shift R and B channels slightly
    vec2 dir = texcoord - vec2(0.5);
    vec2 offset = dir * aberration / resolution;
    vec4 c;
    c.r = Texel(tex, texcoord + offset).r;
    c.g = Texel(tex, texcoord).g;
    c.b = Texel(tex, texcoord - offset).b;
    c.a = 1.0;

    // Scanlines
    float scan = 0.5 + 0.5 * sin(screen_coord.y * 3.14159 * 2.0 / 3.0);
    c.rgb *= (1.0 - scanline_alpha * (1.0 - scan));

    // Vignette
    float d = length(dir) * 2.0;
    float vig = 1.0 - vignette * smoothstep(0.4, 1.0, d);
    c.rgb *= vig;

    return c * color;
}
]]

function crt.load()
    if crt.loaded then return true end
    local ok, shader = pcall(love.graphics.newShader, SHADER_SRC)
    if ok and shader then
        crt.shader = shader
        crt.loaded = true
        return true
    end
    crt.shader = nil
    crt.loaded = false
    return false
end

function crt.apply(canvas)
    if not crt.enabled or not crt.loaded or not crt.shader then
        -- Passthrough: draw canvas as-is
        if canvas then
            love.graphics.setShader()
            love.graphics.setColor(1, 1, 1, 1)
            love.graphics.draw(canvas, 0, 0)
        end
        return
    end
    local W, H = love.graphics.getDimensions()
    crt.shader:send("time", love.timer.getTime())
    crt.shader:send("scanline_alpha", 0.10)
    crt.shader:send("aberration", 1.2)
    crt.shader:send("vignette", 0.35)
    crt.shader:send("resolution", {W, H})
    love.graphics.setShader(crt.shader)
    love.graphics.setColor(1, 1, 1, 1)
    love.graphics.draw(canvas, 0, 0)
    love.graphics.setShader()
end

function crt.toggle()
    crt.enabled = not crt.enabled
    -- Aliases: main.lua calls crt.init(), crt.apply(), crt.draw(), crt.render()
crt.init   = crt.load
crt.draw   = crt.apply
crt.render = crt.apply
crt.setup  = crt.load

return crt.enabled
end

return crt
