-- Unified input with debounce for hat/axis/gamepad overlap
local input = {}
local listeners = {}
local DEBUG = (os.getenv("VOIDDESK_DEBUG_INPUT") == "1")

-- Debounce: per evitare doppio trigger (hat + gamepad_dpad + axis)
local last_emit = {}
local DEBOUNCE = 0.12   -- 120ms

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
    local now = love.timer.getTime()
    -- Directions: debounce strictly to avoid dpad 2-step
    local DIRS = { up = true, down = true, left = true, right = true }
    if DIRS[action] then
        if last_emit[action] and (now - last_emit[action]) < DEBOUNCE then
            if DEBUG then
                print(string.format("[input] DROP %s (%.3fs since last) src=%s",
                    action, now - last_emit[action], source or "?"))
            end
            return
        end
        last_emit[action] = now
    else
        -- Buttons: shorter debounce (50ms) to allow rapid taps
        if last_emit[action] and (now - last_emit[action]) < 0.05 then
            return
        end
        last_emit[action] = now
    end
    if DEBUG then
        print(string.format("[input] %s  (%s)", action, source or "?"))
    end
    input.emit("press", action)
end

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

input.GAMEPAD_NAMES = {
    dpup = "up", dpdown = "down",
    dpleft = "left", dpright = "right",
    a = "a", b = "b", x = "x", y = "y",
    leftshoulder = "l1", rightshoulder = "r1",
    lefttrigger = "l2", righttrigger = "r2",
    back = "select", start = "start", guide = "menu",
    leftstick = "l3", rightstick = "r3",
}

input.JOYBTN_FALLBACK = {
    [0] = "a", [1] = "b", [2] = "x", [3] = "y",
    [4] = "l1", [5] = "r1", [6] = "l2", [7] = "r2",
    [8] = "select", [9] = "start", [10] = "menu",
    [11] = "l3", [12] = "r3",
}

input.DEADZONE = 0.5
local axis_state = {}

return input
