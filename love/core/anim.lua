-- Easing helpers for VoidDesk LÖVE frontend
local anim = {}

function anim.ease_out_cubic(t) return 1 - (1 - t) ^ 3 end
function anim.ease_in_out_quad(t)
    if t < 0.5 then return 2 * t * t end
    return 1 - ((-2 * t + 2) ^ 2) / 2
end
function anim.ease_out_back(t)
    local c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (t - 1) ^ 3 + c1 * (t - 1) ^ 2
end
function anim.clamp(v, lo, hi) return math.max(lo, math.min(hi, v)) end
function anim.lerp(a, b, t) return a + (b - a) * t end
function anim.pulse(t, speed) return 0.5 + 0.5 * math.sin(t * (speed or 3)) end

return anim
