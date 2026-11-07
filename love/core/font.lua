local font = {}
local cache = {}

function font.load(name, size)
    local key = name .. "_" .. size
    if cache[key] then return cache[key] end
    local ok, f = pcall(love.graphics.newFont, "assets/fonts/" .. name, size)
    if not ok or not f then
        f = love.graphics.newFont(size)
    end
    f:setFilter("linear", "linear")
    cache[key] = f
    return f
end

function font.regular(sz) return font.load("DejaVuSans.ttf", sz) end
function font.bold(sz)    return font.load("DejaVuSans-Bold.ttf", sz) end
function font.mono(sz)    return font.load("JetBrainsMono-Regular.ttf", sz) end

function font.print_shadow(text, x, y, f, col, shadow)
    shadow = shadow or { 0, 0, 0, 0.65 }
    love.graphics.setFont(f)
    love.graphics.setColor(shadow[1], shadow[2], shadow[3], shadow[4] or 0.65)
    love.graphics.print(text, x + 1, y + 1)
    love.graphics.setColor(col[1], col[2], col[3], col[4] or 1)
    love.graphics.print(text, x, y)
end

return font
