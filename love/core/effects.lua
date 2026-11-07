local effects = {}

function effects.gradient_v(x, y, w, h, top, bottom)
    local steps = 8
    for i = 0, steps - 1 do
        local t = i / (steps - 1)
        love.graphics.setColor(
            top[1] * (1 - t) + bottom[1] * t,
            top[2] * (1 - t) + bottom[2] * t,
            top[3] * (1 - t) + bottom[3] * t, 1)
        love.graphics.rectangle("fill", x, y + i * h / steps, w, h / steps + 1)
    end
end

function effects.glow(x, y, r, col, intensity, layers)
    layers = layers or 4
    intensity = intensity or 1
    for k = layers, 1, -1 do
        local a = intensity * 0.18 / k
        love.graphics.setColor(col[1], col[2], col[3], a)
        love.graphics.circle("fill", x, y, r + k * r * 0.3)
    end
end

function effects.scanlines(W, H, alpha)
    alpha = alpha or 0.06
    love.graphics.setColor(0, 0, 0, alpha)
    for y = 0, H, 3 do
        love.graphics.rectangle("fill", 0, y, W, 1)
    end
end

function effects.vignette(W, H, strength)
    strength = strength or 0.4
    local layers = 10
    for i = 0, layers - 1 do
        local t = i / layers
        local a = strength * 0.12 * (1 - t)
        love.graphics.setColor(0, 0, 0, a)
        local inset = i * 3
        love.graphics.rectangle("line",
            inset, inset, W - inset * 2, H - inset * 2)
    end
end

function effects.ease_out_cubic(t) return 1 - (1 - t) ^ 3 end
function effects.pulse(t, speed) return 0.5 + 0.5 * math.sin(t * (speed or 3)) end

return effects
