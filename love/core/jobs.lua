-- Job manager (client-side mirror + polling)
local bridge = require("core.bridge")

local jobs = {}
jobs.active = {}       -- id -> job (mirror of service)
jobs.overlay_open = false
jobs.overlay_index = 1
jobs.poll_timer = 0
jobs.POLL_INTERVAL = 0.6

function jobs.refresh()
    bridge.call("job_list", {}, function(resp)
        if resp.ok then
            local new = {}
            for _, j in ipairs(resp.jobs or {}) do
                new[j.id] = j
            end
            jobs.active = new
        end
    end)
end

function jobs.update(dt)
    jobs.poll_timer = jobs.poll_timer + dt
    if jobs.poll_timer >= jobs.POLL_INTERVAL then
        jobs.poll_timer = 0
        jobs.refresh()
    end
end

function jobs.start_tool(tool_id, name, hub, color, on_done)
    bridge.call("job_start", { tool_id = tool_id, name = name, hub = hub }, function(resp)
        if resp.ok then jobs.refresh() end
        if on_done then on_done(resp) end
    end)
end

function jobs.start_cmd(cmd, name, hub, on_done)
    bridge.call("job_start", { cmd = cmd, name = name, hub = hub }, function(resp)
        if resp.ok then jobs.refresh() end
        if on_done then on_done(resp) end
    end)
end

function jobs.cancel(job_id, on_done)
    bridge.call("job_cancel", { job_id = job_id }, function(resp)
        jobs.refresh()
        if on_done then on_done(resp) end
    end)
end

function jobs.get_log(job_id, on_done)
    bridge.call("job_log", { job_id = job_id }, function(resp)
        if on_done then on_done(resp) end
    end)
end

-- Helper: count jobs matching a tool name (for item badge)
function jobs.count_for_name(name)
    local n = 0
    for _, j in pairs(jobs.active) do
        if j.name == name and (j.status == "running" or j.status == "starting") then
            n = n + 1
        end
    end
    return n
end

function jobs.list_active()
    local out = {}
    for _, j in pairs(jobs.active) do
        if j.status == "running" or j.status == "starting" or j.status == "error"
            or j.status == "done" then
            table.insert(out, j)
        end
    end
    table.sort(out, function(a, b) return a.started > b.started end)
    return out
end

function jobs.total_running()
    local n = 0
    for _, j in pairs(jobs.active) do
        if j.status == "running" or j.status == "starting" then
            n = n + 1
        end
    end
    return n
end

function jobs.toggle_overlay()
    jobs.overlay_open = not jobs.overlay_open
    if jobs.overlay_open then
        jobs.refresh()
        jobs.overlay_index = 1
    end
end

return jobs
