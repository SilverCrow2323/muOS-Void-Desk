local sm         = require("core.scene_manager")
local bridge     = require("core.bridge")
local config     = require("core.config")
local theme      = require("theme.loader")
local input      = require("core.input")
local inputdbg   = require("core.input_debug")
local notifications = require("core.notifications")
local jobs       = require("core.jobs")
local term       = require("core.terminal_overlay")

function love.load()
    config.load()
    theme.apply(config.get("theme", "cyberpunk"))
    bridge.init()

    if os.getenv("VOIDDESK_DEBUG_INPUT") == "1" then
        inputdbg.dump_joysticks()
    end

    sm.register("bootanim",   require("scenes.bootanim"))
    sm.register("intro",      require("scenes.intro"))
    sm.register("nexus",      require("scenes.nexus"))
    sm.register("hub_forge",  require("scenes.hub_forge"))
    sm.register("hub_session",require("scenes.hub_session"))
    sm.register("hub_uplink", require("scenes.hub_uplink"))
    sm.register("hub_media",  require("scenes.hub_media"))
    sm.register("hub_iptv",   require("scenes.hub_iptv"))
    sm.register("hub_workshop", require("scenes.hub_workshop"))
    sm.register("hub_toolbox",require("scenes.hub_toolbox"))
    sm.register("hub_mapps",  require("scenes.hub_mapps"))
    sm.register("hub_settings", require("scenes.hub_settings"))
    sm.register("hub_info",   require("scenes.hub_info"))
    sm.register("hub_external", require("scenes.hub_external"))
    sm.register("hub_stub",   require("scenes.hub_stub"))

    sm.switch("intro", { duration = 2.0 })

    jobs.refresh()
end

function love.update(dt)
    sm.update(dt)
    bridge.poll()
    notifications.update()
    jobs.update(dt)
end

function love.draw()
    sm.draw()
    local chrome = require("core.chrome")
    local theme_mod = require("theme.loader")
    notifications.draw(theme_mod.get(), chrome.HEADER_H)
    local W, H = love.graphics.getDimensions()
    term.draw(W, H)
end

function love.keypressed(key, sc, isrepeat)
    if isrepeat then return end
    if key == "f11" then
        love.window.setFullscreen(not love.window.getFullscreen())
        return
    end
    if term.keypressed(key) then return end
    if key == "m" then
        notifications.toggle()
        return
    end
    if key == "tab" then
        jobs.toggle_overlay()
        return
    end
    if key == "escape" then
        input.press("b", "key:escape")
        return
    end
    local logical = input.KEYMAP[key]
    if logical then input.press(logical, "key:" .. key) end
end

function love.gamepadpressed(joystick, button)
    -- Route to overlay first
    local btn_id = ({a=0, b=1, x=2, y=3,
                    leftshoulder=4, rightshoulder=5,
                    back=6, start=7}[button])
    if btn_id and term.joystickpressed(joystick, btn_id) then return end

    local logical = input.GAMEPAD_NAMES[button]
    if logical then input.press(logical, "gamepad:" .. button) end
end

function love.joystickpressed(joystick, button)
    if joystick:isGamepad() then return end
    -- Raw fallback for unmapped joysticks
    local map = input.JOYBTN_FALLBACK
    local logical = map[button]
    if logical then input.press(logical, "joybtn:" .. button) end
end

function love.joystickhat(joystick, hat, direction)
    if direction == "u" then input.press("up",    "hat:u")
    elseif direction == "d" then input.press("down",  "hat:d")
    elseif direction == "l" then input.press("left",  "hat:l")
    elseif direction == "r" then input.press("right", "hat:r")
    end
end
