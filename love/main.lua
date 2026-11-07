local sm         = require("core.scene_manager")
local bridge     = require("core.bridge")
local config     = require("core.config")
local theme      = require("theme.loader")
local input      = require("core.input")
local inputdbg   = require("core.input_debug")

function love.load()
    config.load()
    theme.apply(config.get("theme", "cyberpunk"))
    bridge.init()

    -- joystick discovery (log only if VOIDDESK_DEBUG_INPUT=1)
    if os.getenv("VOIDDESK_DEBUG_INPUT") == "1" then
        inputdbg.dump_joysticks()
    end

    sm.register("intro",     require("scenes.intro"))
    sm.register("nexus",     require("scenes.nexus"))
    sm.register("hub_forge", require("scenes.hub_forge"))
    sm.register("hub_stub",  require("scenes.hub_stub"))

    sm.switch("intro", { duration = 2.0 })
end

function love.update(dt)
    sm.update(dt)
    bridge.poll()
end

function love.draw()
    sm.draw()
end

-- ─── KEYBOARD ──────────────────────────────────────────────
function love.keypressed(key, sc, isrepeat)
    if isrepeat then return end
    if key == "f11" then
        love.window.setFullscreen(not love.window.getFullscreen())
        return
    end
    local logical = input.KEYMAP[key]
    if logical then input.press(logical, "key:" .. key) end
end

-- ─── GAMEPAD (named buttons, reliable) ────────────────────
function love.gamepadpressed(joystick, button)
    local logical = input.GAMEPAD_NAMES[button]
    if logical then input.press(logical, "gamepad:" .. button) end
end

-- ─── JOYSTICK (raw buttons, fallback for unmapped controllers) ──
function love.joystickpressed(joystick, button)
    -- If it IS a gamepad, gamepadpressed already fired: skip to avoid double
    if joystick:isGamepad() then return end
    local logical = input.JOYBTN_FALLBACK[button]
    if logical then input.press(logical, "joybtn:" .. button)
    else
        if os.getenv("VOIDDESK_DEBUG_INPUT") == "1" then
            print("[input] unmapped joystick button: " .. tostring(button))
        end
    end
end

-- ─── HAT (d-pad on most devices) ───────────────────────────
function love.joystickhat(joystick, hat, direction)
    -- direction: "c" (center), "u","d","l","r","ru","rd","lu","ld"
    if direction == "u" then input.press("up",    "hat:u")
    elseif direction == "d" then input.press("down",  "hat:d")
    elseif direction == "l" then input.press("left",  "hat:l")
    elseif direction == "r" then input.press("right", "hat:r")
    end
    -- diagonal: fire the dominant axis only (menus don't like diagonals)
    -- ignored for now — user can navigate cleanly
end

-- ─── AXIS (analog stick as d-pad fallback) ────────────────
function love.joystickaxis(joystick, axis, value)
    -- Heuristic: only treat as d-pad if no hat is present
    if joystick:getHatCount() > 0 then return end
    if axis > 1 then return end  -- axes 0/1 are typically left stick X/Y

    local prev = axis_state[axis] or 0
    local dir = 0
    if value >  input.DEADZONE then dir =  1
    elseif value < -input.DEADZONE then dir = -1 end
    axis_state[axis] = dir

    if dir == prev then return end
    if axis == 0 then
        if dir ==  1 then input.press("right", "axis:x+")
        elseif dir == -1 then input.press("left",  "axis:x-") end
    elseif axis == 1 then
        if dir == -1 then input.press("up",   "axis:y-")
        elseif dir ==  1 then input.press("down", "axis:y+") end
    end
end
