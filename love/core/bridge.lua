-- Bridge via JSON files: LÖVE writes .love_request.json,
-- Python service reads it, writes .love_response.json.
-- Polling every 100ms — no external dependencies.
local json    = require("lib.json")
local bridge  = {}
local pending = {}   -- callback queue
local timer   = 0
local POLL    = 0.08

local function app_dir()
    return os.getenv("VOIDDESK_APP_DIR") or "."
end

function bridge.req_path()  return app_dir().."/data/.love_request.json"  end
function bridge.resp_path() return app_dir().."/data/.love_response.json" end

function bridge.init()
    bridge._id = 0
    -- rimuovi file stale
    os.remove(bridge.resp_path())
end

function bridge.call(cmd, args, cb)
    bridge._id = bridge._id + 1
    local req = { id = bridge._id, cmd = cmd, args = args or {} }
    local f = io.open(bridge.req_path(), "w")
    if not f then
        if cb then cb({ ok = false, error = "cannot write request" }) end
        return
    end
    f:write(json.encode(req))
    f:close()
    table.insert(pending, { id = bridge._id, cb = cb, since = love.timer.getTime() })
end

function bridge.poll()
    timer = timer + love.timer.getDelta()
    if timer < POLL then return end
    timer = 0

    if #pending == 0 then return end

    local f = io.open(bridge.resp_path(), "r")
    if not f then
        -- timeout dopo 10s
        local now = love.timer.getTime()
        while #pending > 0 and (now - pending[1].since) > 10 do
            local p = table.remove(pending, 1)
            if p.cb then p.cb({ ok = false, error = "timeout" }) end
        end
        return
    end

    local s = f:read("*a") ; f:close() ; os.remove(bridge.resp_path())
    local ok, resp = pcall(json.decode, s)
    if not ok or type(resp) ~= "table" then
        if #pending > 0 then
            local p = table.remove(pending, 1)
            if p.cb then p.cb({ ok = false, error = "bad json" }) end
        end
        return
    end

    -- match per id
    for i, p in ipairs(pending) do
        if p.id == resp.id then
            table.remove(pending, i)
            if p.cb then p.cb(resp) end
            return
        end
    end
    -- fallback: rispondi al primo
    if #pending > 0 then
        local p = table.remove(pending, 1)
        if p.cb then p.cb(resp) end
    end
end

return bridge
