local onboarding = {
    active = false,
    name = "",
    cursor = 1,
    error = "",
    pulse = 0,
}

local keys = {
    "A","B","C","D","E","F","G","H",
    "I","J","K","L","M","N","O","P",
    "Q","R","S","T","U","V","W","X",
    "Y","Z","0","1","2","3","4","5",
    "6","7","8","9","-","_","SPACE","BACK",
}
local columns = 8
local max_length = 18
local font_cache = {}

local function get_font(size)
    if not font_cache[size] then font_cache[size] = love.graphics.newFont(size) end
    return font_cache[size]
end

local function clean(value)
    value = tostring(value or ""):gsub("[%c]", "")
    value = value:gsub("[^%w _%-]", "")
    value = value:gsub("%s+", " ")
    return value:sub(1, max_length)
end

function onboarding.init(config)
    local stored = clean(config.get("profile_name", ""))
    local legacy = clean(config.get("termid_name", ""))
    local placeholders = {
        qq = true, user = true, guest = true, unknown = true,
        username = true, voiddesk = true, [""] = true,
    }
    local complete = config.get("profile_name_setup_complete", false) == true
    if stored == "" and legacy ~= "" and not placeholders[legacy:lower()] then
        -- Preserve a real identity created by the Pygame frontend and migrate
        -- it atomically instead of asking existing users twice.
        if config.set_many({
            profile_name = legacy,
            profile_name_setup_complete = true,
            termid_name = legacy,
        }) then
            stored = legacy
            complete = true
        end
    end
    onboarding.name = stored
    onboarding.active = not complete
    onboarding.cursor = 1
    onboarding.error = ""
    onboarding.pulse = 0
    if onboarding.active and love and love.keyboard then
        love.keyboard.setTextInput(true)
    end
end

function onboarding.finish(config)
    local value = clean(onboarding.name):gsub("^%s+", ""):gsub("%s+$", "")
    if #value < 2 then
        onboarding.error = "Choose a name with at least 2 characters."
        return false
    end
    if not config.set_many({
        profile_name = value,
        profile_name_setup_complete = true,
        termid_name = value,
    }) then
        onboarding.error = "The profile could not be saved. Check storage and try again."
        return false
    end
    onboarding.name = value
    onboarding.active = false
    onboarding.error = ""
    if love and love.keyboard then love.keyboard.setTextInput(false) end
    return true
end

function onboarding.textinput(text, config)
    if not onboarding.active then return false end
    onboarding.name = clean(onboarding.name .. text)
    onboarding.error = ""
    return true
end

function onboarding.keypressed(key, config)
    if not onboarding.active then return false end
    if key == "backspace" then
        onboarding.name = onboarding.name:sub(1, -2)
        onboarding.error = ""
    elseif key == "return" or key == "kpenter" then
        onboarding.finish(config)
    elseif key == "space" then
        onboarding.name = clean(onboarding.name .. " ")
    elseif key == "escape" then
        -- Identity setup is mandatory on first boot: Escape removes the last
        -- character instead of silently skipping the required profile step.
        onboarding.name = onboarding.name:sub(1, -2)
    end
    return true
end

local function apply_key(key, config)
    if key == "BACK" then
        onboarding.name = onboarding.name:sub(1, -2)
    elseif key == "SPACE" then
        onboarding.name = clean(onboarding.name .. " ")
    else
        onboarding.name = clean(onboarding.name .. key)
    end
    onboarding.error = ""
end

function onboarding.handle_action(action, config)
    if not onboarding.active then return false end
    local total = #keys
    local row = math.floor((onboarding.cursor - 1) / columns)
    local col = (onboarding.cursor - 1) % columns
    if action == "left" then
        col = (col - 1) % columns
    elseif action == "right" then
        col = (col + 1) % columns
    elseif action == "up" then
        row = math.max(0, row - 1)
    elseif action == "down" then
        row = math.min(math.ceil(total / columns) - 1, row + 1)
    elseif action == "b" then
        onboarding.name = onboarding.name:sub(1, -2)
        onboarding.error = ""
    elseif action == "a" then
        local key = keys[onboarding.cursor]
        if key then
            if key == "DONE" then onboarding.finish(config)
            else apply_key(key, config) end
        end
        return true
    elseif action == "start" then
        onboarding.finish(config)
        return true
    else
        return true
    end
    local next_idx = row * columns + col + 1
    onboarding.cursor = math.max(1, math.min(total, next_idx))
    return true
end

function onboarding.update(dt)
    if onboarding.active then onboarding.pulse = onboarding.pulse + dt end
end

function onboarding.draw(theme)
    if not onboarding.active then return end
    local W, H = love.graphics.getDimensions()
    local accent = theme and theme.accent or {0.25, 0.82, 0.95}
    local accent2 = theme and theme.accent2 or {0.83, 0.28, 0.72}
    local text = theme and theme.text or {0.92, 0.95, 1}
    local dim = theme and theme.dim or {0.53, 0.61, 0.70}
    local panel_w = math.min(W - 24, 590)
    local panel_h = math.min(H - 24, 430)
    local px, py = (W-panel_w)/2, (H-panel_h)/2
    local pulse = 0.5 + 0.5 * math.sin(onboarding.pulse * 2.4)

    love.graphics.setColor(0.008, 0.014, 0.027, 0.96)
    love.graphics.rectangle("fill", 0, 0, W, H)
    love.graphics.setColor(accent[1], accent[2], accent[3], 0.10)
    love.graphics.circle("fill", W*0.18, H*0.16, 120 + pulse*18)
    love.graphics.setColor(accent2[1], accent2[2], accent2[3], 0.08)
    love.graphics.circle("fill", W*0.84, H*0.78, 150 + pulse*20)

    love.graphics.setColor(0.045, 0.060, 0.085, 0.98)
    love.graphics.rectangle("fill", px, py, panel_w, panel_h, 12)
    love.graphics.setColor(accent[1], accent[2], accent[3], 0.8)
    love.graphics.setLineWidth(2)
    love.graphics.rectangle("line", px, py, panel_w, panel_h, 12)
    love.graphics.setColor(accent[1], accent[2], accent[3], 0.75)
    love.graphics.rectangle("fill", px+18, py+18, 4, 56, 2)

    local title = get_font(24)
    love.graphics.setFont(title)
    love.graphics.setColor(text[1], text[2], text[3], 1)
    love.graphics.print("WELCOME TO VOID DESK", px+34, py+20)
    local sub = get_font(12)
    love.graphics.setFont(sub)
    love.graphics.setColor(accent[1], accent[2], accent[3], 1)
    love.graphics.print("IDENTITY INITIALIZATION  /  LOCAL PROFILE", px+35, py+54)

    love.graphics.setColor(0.015, 0.025, 0.040, 1)
    love.graphics.rectangle("fill", px+24, py+88, panel_w-48, 48, 6)
    love.graphics.setColor(accent[1], accent[2], accent[3], 0.7)
    love.graphics.rectangle("line", px+24, py+88, panel_w-48, 48, 6)
    love.graphics.setFont(get_font(11))
    love.graphics.setColor(dim[1], dim[2], dim[3], 1)
    love.graphics.print("DISPLAY NAME", px+36, py+96)
    love.graphics.setFont(get_font(19))
    love.graphics.setColor(text[1], text[2], text[3], 1)
    local shown = onboarding.name ~= "" and onboarding.name or "Type or select a name..."
    love.graphics.print(shown .. (math.floor(onboarding.pulse*2)%2==0 and "_" or ""),
                        px+36, py+111)

    local cell_w = math.floor((panel_w-64) / columns)
    local cell_h = 36
    local key_top = py+150
    for i, key in ipairs(keys) do
        local r = math.floor((i-1)/columns)
        local c = (i-1)%columns
        local x = px+24+c*cell_w
        local y = key_top+r*(cell_h+5)
        local selected = i == onboarding.cursor
        local label = key == "SPACE" and "SPACE" or (key == "BACK" and "⌫" or key)
        if selected then
            love.graphics.setColor(accent[1], accent[2], accent[3], 0.25+0.15*pulse)
        else
            love.graphics.setColor(0.08, 0.11, 0.15, 1)
        end
        love.graphics.rectangle("fill", x+2, y, cell_w-5, cell_h, 5)
        love.graphics.setColor(selected and accent[1] or 0.24,
            selected and accent[2] or 0.30, selected and accent[3] or 0.38, 1)
        love.graphics.setLineWidth(selected and 2 or 1)
        love.graphics.rectangle("line", x+2, y, cell_w-5, cell_h, 5)
        local f = love.graphics.newFont(12)
        love.graphics.setFont(f)
        local tw = f:getWidth(label)
        love.graphics.setColor(text[1], text[2], text[3], 1)
        love.graphics.print(label, x+(cell_w-tw)/2, y+11)
    end

    local footer_y = py+panel_h-48
    love.graphics.setFont(love.graphics.newFont(11))
    love.graphics.setColor(dim[1], dim[2], dim[3], 1)
    love.graphics.print("D-PAD / L-STICK  SELECT  ·  A ADD  ·  B DELETE  ·  START CONFIRM",
                        px+24, footer_y)
    if onboarding.error ~= "" then
        love.graphics.setColor(1, 0.38, 0.38, 1)
        love.graphics.printf(onboarding.error, px+24, footer_y-22, panel_w-48, "left")
    else
        love.graphics.setColor(accent[1], accent[2], accent[3], 0.9)
        love.graphics.print("This name is stored locally and can be changed later in Settings.",
                            px+24, footer_y-22)
    end
    love.graphics.setColor(1, 1, 1, 1)
end

return onboarding
