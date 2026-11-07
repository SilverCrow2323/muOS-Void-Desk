-- Scene manager with navigation stack (push/back/switch).
local sm = {}

local scenes = {}
local current = nil
local current_name = ""

-- Stack of {name, args, state}. Last entry = current.
local stack = {}

local function _copy(t)
    local o = {}
    if t then for k, v in pairs(t) do o[k] = v end end
    return o
end

function sm.register(name, mod)
    scenes[name] = mod
end

local function _enter(name, args, restore_state)
    if not scenes[name] then
        print("[scene] not found: " .. name)
        return false
    end
    current_name = name
    current = scenes[name]
    local a = _copy(args)
    if restore_state then a.restore_state = restore_state end
    if current.enter then current.enter(a) end
    return true
end

local function _save_current_state()
    if current and current.save_state then
        local ok, st = pcall(current.save_state)
        if ok then return st end
    end
    return nil
end

-- Push a new scene on top of stack. Current scene is preserved below.
function sm.push(name, args)
    -- Save current state
    if current then
        local state = _save_current_state()
        if #stack > 0 then
            stack[#stack].state = state
        end
    end
    -- Enter new scene
    if _enter(name, args) then
        table.insert(stack, { name = name, args = _copy(args) })
    end
end

-- Pop current, restore previous scene with its saved state.
function sm.back()
    if #stack < 2 then
        -- Nothing to go back to
        return false
    end
    -- Save current state (in case we come back via push again)
    local state = _save_current_state()
    stack[#stack].state = state
    -- Remove current from stack
    table.remove(stack)
    -- Restore previous
    local prev = stack[#stack]
    if current and current.leave then current.leave() end
    return _enter(prev.name, prev.args, prev.state)
end

-- Switch = reset stack to this single scene. Use for boot, intro→nexus, etc.
function sm.switch(name, args)
    if current and current.leave then current.leave() end
    stack = {}
    if _enter(name, args) then
        stack = { { name = name, args = _copy(args) } }
    end
end

function sm.current_name() return current_name end
function sm.can_back() return #stack > 1 end

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
