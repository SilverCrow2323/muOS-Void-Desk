-- CRT shader effect for VoidDesk LÖVE frontend.
-- Scanlines + chromatic aberration + vignette.
-- Works as passthrough if shader compilation fails (e.g. on weak GLES).
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
    vec2 dir = texcoord - vec2(0.5);
    vec2 offset = dir * aberration / resolution;
    vec4 c;
    c.r = Texel(tex, texcoord + offset).r;
    c.g = Texel(tex, texcoord).g;
    c.b = Texel(tex, texcoord - offset).b;
    c.a = 1.0;

    float scan = 0.5 + 0.5 * sin(screen_coord.y * 3.14159 * 2.0 / 3.0);
    c.rgb *= (1.0 - scanline_alpha * (1.0 - scan));

    float d = length(dir) * 2.0;
    float vig = 1.0 - vignette * smoothstep(0.4, 1.0, d);
    c.rgb *= vig;

    return c * color;
}
]]

-- crt.load() and crt.init() are aliases. Both compile the shader.
local function _load_impl()
    if crt.loaded then return true end
    if not (love.graphics and love.graphics.newShader) then
        return false
    end
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

function crt.load()   return _load_impl() end
function crt.init()   return _load_impl() end

function crt.apply(canvas)
    if not crt.enabled or not crt.loaded or not crt.shader then
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

function crt.draw(canvas)   crt.apply(canvas) end
function crt.render(canvas) crt.apply(canvas) end
function crt.setup()        return crt.load() end

function crt.toggle()
    crt.enabled = not crt.enabled
    return crt.enabled
end

return crt
