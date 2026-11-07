local sm = {}
local scenes = {}
local current = nil
local current_name = ""

function sm.register(name, mod)
    scenes[name] = mod
end

function sm.switch(name, args)
    if not scenes[name] then
        print("[scene] not found: "..name)
        return
    end
    if current and current.leave then current.leave() end
    current_name = name
    current = scenes[name]
    if current.enter then current.enter(args or {}) end
end

function sm.current_name() return current_name end

function sm.update(dt)
    if current and current.update then current.update(dt) end
end

function sm.draw()
    if current and current.draw then current.draw() end
end

function sm.keypressed(key, sc, isrepeat)
    if current and current.keypressed then current.keypressed(key, sc, isrepeat) end
end

function sm.joystickpressed(joy, btn)
    if current and current.joystickpressed then current.joystickpressed(joy, btn) end
end

function sm.joystickhat(joy, hat, dir)
    if current and current.joystickhat then current.joystickhat(joy, hat, dir) end
end

return sm
