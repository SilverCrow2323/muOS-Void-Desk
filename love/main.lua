local sm         = require("core.scene_manager")
local bridge     = require("core.bridge")
local config     = require("core.config")
local theme      = require("theme.loader")
local input      = require("core.input")
local inputdbg   = require("core.input_debug")
local notifications = require("core.notifications")
local jobs       = require("core.jobs")
local tablet     = require("core.tablet")
local operation_overlay = require("core.operation_overlay")
local onboarding = require("core.onboarding")
local crt        = require("core.crt_shader")
local visual_capture = require("core.visual_capture")
local qwasar_profile = require("core.qwasar_profile")
local qwasar_nodes = require("core.nodes")
local crt_on     = true
local axis_state = {} -- analog-stick edge tracking (per axis)

function love.load()
    config.load()
    onboarding.init(config)
    theme.apply(config.get("theme", "cyberpunk"))
    local composition, profile_err = qwasar_profile.load()
    if composition then
        qwasar_nodes.apply_profile(composition)
        print("[QWASAR] profile loaded: " ..
            tostring((composition.profile or {}).name or "unnamed"))
    else
        print("[QWASAR] profile snapshot unavailable; using built-in NEXUS defaults: " ..
            tostring(profile_err or "not generated"))
    end
    bridge.init()
    crt.init()

    -- joystick discovery (log only if VOIDDESK_DEBUG_INPUT=1)
    if os.getenv("VOIDDESK_DEBUG_INPUT") == "1" then
        inputdbg.dump_joysticks()
    end

    sm.register("bootanim",  require("scenes.bootanim"))
    sm.register("intro",     require("scenes.intro"))
    sm.register("nexus",     require("scenes.nexus"))
    sm.register("hub_forge", require("scenes.hub_forge"))
    sm.register("hub_apt", require("scenes.hub_apt"))
    sm.register("hub_stub",  require("scenes.hub_stub"))
    sm.register("hub_session", require("scenes.hub_session"))
    sm.register("hub_uplink", require("scenes.hub_uplink"))
    sm.register("hub_tailscale", require("scenes.hub_tailscale"))
    sm.register("hub_syncthing", require("scenes.hub_syncthing"))
    sm.register("hub_media", require("scenes.hub_media"))
    sm.register("hub_workshop", require("scenes.hub_workshop"))
    sm.register("hub_settings", require("scenes.hub_settings"))
    sm.register("hub_display_fx", require("scenes.hub_display_fx"))
    sm.register("hub_info", require("scenes.hub_info"))

    if os.getenv("VOIDDESK_CAPTURE_ALL") == "1" then
        onboarding.disable_for_visual_capture()
        tablet.active = false
        jobs.overlay_open = false
        local ok, err = visual_capture.start_batch(sm)
        if not ok then error(err or "unable to start visual capture batch") end
    else
        sm.switch("intro", { duration = 2.0 })
    end
end

function love.update(dt)
    if not onboarding.active then sm.update(dt) end
    bridge.poll()
    jobs.update(dt)
    tablet.update(dt)
    onboarding.update(dt)
    notifications.update()
    visual_capture.update(dt)
end

function love.draw()
    crt.frame(love.timer.getDelta(), function()
        sm.draw()
    end)
    local chrome = require("core.chrome")
    local current_theme = theme.get()
    if not tablet.active and not jobs.overlay_open and not onboarding.active then
        notifications.draw(current_theme, chrome.HEADER_H)
    end
    tablet.draw()
    operation_overlay.draw()
    onboarding.draw(current_theme)
end

-- ─── KEYBOARD ──────────────────────────────────────────────
function love.keypressed(key, sc, isrepeat)
    if isrepeat then return end
    if onboarding.active then
        onboarding.keypressed(key, config)
        return
    end
    if key == "f12" then
        local ok, err = visual_capture.capture(sm.current_name())
        if not ok then
            print("[visual-capture] " .. tostring(err or "capture failed"))
        end
        return
    end
    if key == "f11" then
        love.window.setFullscreen(not love.window.getFullscreen())
        return
    end
    if key == "m" then
        if jobs.overlay_open then jobs.hide_overlay() end
        tablet.toggle()
        return
    end
    if key == "c" then
        crt.set_enabled(not crt_on)
        crt_on = not crt_on
        return
    end
    if key == "escape" then
        input.press("b", "key:escape")
        return
    end
    local logical = input.KEYMAP[key]
    if logical then input.press(logical, "key:" .. key) end
end

function love.textinput(text)
    if onboarding.active then onboarding.textinput(text, config)
    elseif not tablet.active and not jobs.overlay_open then sm.textinput(text) end
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
