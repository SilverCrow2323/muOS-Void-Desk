-- Unified input: keyboard + gamepad (named) + joystick (raw) + hat + axis
-- Scenes subscribe via input.on("press", fn) and receive logical actions:
--   up / down / left / right / a / b / x / y / l1 / r1 / l2 / r2 / start / select / menu
local input = {}
local listeners = {}
local DEBUG = (os.getenv("VOIDDESK_DEBUG_INPUT") == "1")

function input.on(event, fn)
    listeners[event] = listeners[event] or {}
    table.insert(listeners[event], fn)
end

function input.clear()
    listeners = {}
end

function input.emit(event, ...)
    for _, fn in ipairs(listeners[event] or {}) do
        fn(...)
    end
end

function input.press(action, source)
    if DEBUG then
        print(string.format("[input] %s  (%s)", action, source or "?"))
    end
    input.emit("press", action)
end

-- Keyboard map (for desktop)
input.KEYMAP = {
    ["up"] = "up", ["down"] = "down",
    ["left"] = "left", ["right"] = "right",
    ["z"] = "a", ["return"] = "a",
    ["x"] = "b", ["backspace"] = "b",
    ["a"] = "y", ["s"] = "x",
    ["q"] = "l1", ["w"] = "r1",
    ["e"] = "l2", ["r"] = "r2",
    ["tab"] = "select",
    [" "] = "start",
    ["escape"] = "menu", ["m"] = "menu",
}

-- SDL gamepad named buttons → logical
input.GAMEPAD_NAMES = {
    dpup = "up", dpdown = "down",
    dpleft = "left", dpright = "right",
    a = "a", b = "b", x = "x", y = "y",
    leftshoulder = "l1", rightshoulder = "r1",
    lefttrigger = "l2", righttrigger = "r2",
    back = "select", start = "start", guide = "menu",
    leftstick = "l3", rightstick = "r3",
}

-- Raw joystick button fallback (used only when joystick:isGamepad() == false)
-- Common RG35XX-H mapping when no gamepad DB mapping is loaded:
input.JOYBTN_FALLBACK = {
    [0] = "a", [1] = "b", [2] = "x", [3] = "y",
    [4] = "l1", [5] = "r1",
    [6] = "select", [7] = "start",
    [8] = "l3", [9] = "r3",
    [10] = "menu",
}

-- Analog deadzone for axis-based d-pad
input.DEADZONE = 0.5
local axis_state = {}

return input
