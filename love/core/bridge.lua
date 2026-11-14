-- Single-flight JSON bridge between the LÖVE frontend and Python service.
-- Requests are queued because the service exposes one request/response file pair.
local json = require("lib.json")
local bridge = {}

local queue = {}
local active = nil
local timer = 0
local POLL = 0.08
local TIMEOUT = 25

local function app_dir()
    return os.getenv("VOIDDESK_APP_DIR") or "."
end

function bridge.req_path()
    return app_dir() .. "/data/.love_request.json"
end

function bridge.resp_path()
    return app_dir() .. "/data/.love_response.json"
end

local function notify(req, response)
    if type(response) == "table" and response.ok and type(response.job) == "table" then
        local jobs = package.loaded["core.jobs"]
        if jobs and jobs.show_job then
            jobs.show_job(response.job.id, response.job)
        end
    end
    if req and req.cb then
        local ok, err = pcall(req.cb, response)
        if not ok then
            print("[bridge] callback failed: " .. tostring(err))
        end
    end
end

-- Only one request may be visible to the service at a time. Write to a
-- per-request temporary file and rename it into place to avoid partial JSON.
local function pump()
    if active then return end

    while #queue > 0 do
        local req = table.remove(queue, 1)
        local path = bridge.req_path()
        local tmp = path .. ".tmp." .. tostring(req.id)
        local f, open_err = io.open(tmp, "w")

        if not f then
            notify(req, { ok = false, error = "cannot write request: " .. tostring(open_err) })
        else
            local wrote, write_err = f:write(json.encode({
                id = req.id,
                cmd = req.cmd,
                args = req.args,
            }))
            local closed, close_err = f:close()

            if not wrote or not closed then
                os.remove(tmp)
                notify(req, {
                    ok = false,
                    error = "cannot finish request: " .. tostring(write_err or close_err),
                })
            else
                local renamed, rename_err = os.rename(tmp, path)
                if renamed then
                    req.since = love.timer.getTime()
                    active = req
                    return
                end
                os.remove(tmp)
                notify(req, { ok = false, error = "cannot publish request: " .. tostring(rename_err) })
            end
        end
    end
end

function bridge.init()
    bridge._id = 0
    queue = {}
    active = nil
    timer = 0
    -- Remove only an old response. The service owns the processing marker.
    os.remove(bridge.resp_path())
end

function bridge.call(cmd, args, cb)
    bridge._id = (bridge._id or 0) + 1
    table.insert(queue, {
        id = bridge._id,
        cmd = cmd,
        args = args or {},
        cb = cb,
    })
    pump()
    return bridge._id
end

function bridge.poll()
    timer = timer + love.timer.getDelta()
    if timer < POLL then return end
    timer = 0

    if not active then
        pump()
        return
    end

    local f = io.open(bridge.resp_path(), "r")
    if f then
        local body = f:read("*a")
        f:close()
        os.remove(bridge.resp_path())

        local ok, response = pcall(json.decode, body)
        if not ok or type(response) ~= "table" then
            local finished = active
            active = nil
            notify(finished, { ok = false, error = "bad json response" })
            pump()
            return
        end

        if tonumber(response.id) == active.id then
            local finished = active
            active = nil
            notify(finished, response)
            pump()
            return
        end
        -- A response from a request that timed out is stale. Discard it,
        -- but keep waiting for the current request's matching response.
    end

    if active and (love.timer.getTime() - active.since) > TIMEOUT then
        local finished = active
        active = nil
        notify(finished, { ok = false, error = "timeout" })
        pump()
    end
end

function bridge.pending_count()
    return #queue + (active and 1 or 0)
end

return bridge
