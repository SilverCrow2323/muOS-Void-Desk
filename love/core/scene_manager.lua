-- Scene manager with lazy-loaded scene modules and a navigation stack.
local sm = {}

local scenes = {}
local current = nil
local current_name = ""
local last_error = nil
local current_error = nil

-- Stack of {name, args, state}. Last entry = current.
local stack = {}

local function _copy(t)
    local o = {}
    if t then
        for k, v in pairs(t) do o[k] = v end
    end
    return o
end

function sm.register(name, mod)
    if type(name) ~= "string" or type(mod) ~= "table" then
        return false
    end
    scenes[name] = mod
    last_error = nil
    return true
end

-- Sub-scenes (calendar, shell, calculator, editor, etc.) are loaded only
-- when first opened. This keeps boot light without making those routes dead.
local function _resolve(name)
    if scenes[name] then return true end
    if type(name) ~= "string" or not name:match("^[%w_]+$") then
        last_error = "invalid scene name"
        return false
    end

    local ok, mod = pcall(require, "scenes." .. name)
    if not ok then
        last_error = tostring(mod)
        print("[scene] failed to load " .. name .. ": " .. last_error)
        return false
    end
    if type(mod) ~= "table" then
        last_error = "scene module did not return a table"
        print("[scene] invalid module " .. name)
        return false
    end
    scenes[name] = mod
    last_error = nil
    return true
end

function sm.load(name)
    return _resolve(name)
end

function sm.is_registered(name)
    return scenes[name] ~= nil
end

function sm.last_error()
    return last_error
end

local function _enter(name, args, restore_state)
    if not _resolve(name) then
        print("[scene] not found: " .. tostring(name))
        return false
    end

    local previous, previous_name, previous_error = current, current_name, current_error
    current_name = name
    current = scenes[name]
    current_error = nil

    local a = _copy(args)
    if restore_state then a.restore_state = restore_state end
    if current.enter then
        local ok, err = pcall(current.enter, a)
        if not ok then
            last_error = tostring(err)
            print("[scene] enter failed " .. name .. ": " .. last_error)
            current, current_name, current_error = previous, previous_name, previous_error
            return false
        end
    end
    last_error = nil
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
    if current then
        local state = _save_current_state()
        if #stack > 0 then stack[#stack].state = state end
    end
    if _enter(name, args) then
        table.insert(stack, { name = name, args = _copy(args) })
        return true
    end
    return false
end

-- Pop current, restore previous scene with its saved state.
function sm.back()
    if #stack < 2 then return false end
    local state = _save_current_state()
    stack[#stack].state = state
    table.remove(stack)
    local prev = stack[#stack]
    if current and current.leave then
        pcall(current.leave)
    end
    return _enter(prev.name, prev.args, prev.state)
end

-- Switch = reset stack to this single scene. Use for boot, intro→nexus, etc.
function sm.switch(name, args)
    if current and current.leave then
        pcall(current.leave)
    end
    stack = {}
    if _enter(name, args) then
        stack = { { name = name, args = _copy(args) } }
        return true
    end
    current = nil
    current_name = ""
    return false
end

function sm.current_name() return current_name end
function sm.can_back() return #stack > 1 end

function sm.update(dt)
    if current and current.update then
        local ok, err = pcall(current.update, dt)
        if not ok then
            current_error = tostring(err)
            last_error = current_error
            print("[scene] update failed " .. current_name .. ": " .. last_error)
        end
    end
end

function sm.current_error()
    return current_error
end

local function draw_error_notice(message)
    if not love or not love.graphics then return end
    pcall(function()
        local W, H = love.graphics.getDimensions()
        love.graphics.setColor(0.025, 0.03, 0.045, 1)
        love.graphics.rectangle("fill", 0, 0, W, H)
        love.graphics.setColor(1, 0.32, 0.32, 1)
        love.graphics.setFont(love.graphics.newFont(18))
        love.graphics.printf("SCENE RENDER ERROR", 20, H * 0.34, W - 40, "center")
        love.graphics.setColor(0.88, 0.9, 0.94, 1)
        love.graphics.setFont(love.graphics.newFont(11))
        love.graphics.printf(tostring(message):sub(1, 240), 24, H * 0.44,
                             W - 48, "center")
    end)
end

function sm.draw()
    if current and current.draw then
        local ok, err = pcall(current.draw)
        if not ok then
            current_error = tostring(err)
            last_error = current_error
            print("[scene] draw failed " .. current_name .. ": " .. current_error)
            draw_error_notice(current_error)
            return false, current_error
        end
    end
    return true
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
