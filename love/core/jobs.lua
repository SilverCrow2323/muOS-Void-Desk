local bridge = require("core.bridge")

local jobs = {}
jobs.active = {}
jobs.overlay_open = false
jobs.focus_id = nil
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

function jobs.show_job(job_id, seed)
    if seed and job_id then jobs.active[tostring(job_id)] = seed end
    jobs.focus_id = job_id and tostring(job_id) or jobs.focus_id
    jobs.overlay_open = true
    jobs.refresh()
end

function jobs.hide_overlay()
    jobs.overlay_open = false
end

function jobs.start_tool(tool_id, name, hub, on_done)
    bridge.call("job_start", { tool_id = tool_id, name = name, hub = hub }, function(resp)
        if resp.ok and resp.job then jobs.show_job(resp.job.id, resp.job) end
        if on_done then on_done(resp) end
    end)
end

function jobs.start_cmd(cmd, name, hub, on_done)
    bridge.call("job_start", { cmd = cmd, name = name, hub = hub }, function(resp)
        if resp.ok and resp.job then jobs.show_job(resp.job.id, resp.job) end
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
        if j.status == "running" or j.status == "starting"
           or j.status == "error" or j.status == "done" then
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
    if jobs.overlay_open then jobs.refresh() end
end

function jobs.focused()
    if jobs.focus_id and jobs.active[jobs.focus_id] then
        return jobs.active[jobs.focus_id]
    end
    local list = jobs.list_active()
    local first = list[1]
    if first then jobs.focus_id = tostring(first.id) end
    return first
end

function jobs.total_progress()
    local total, count = 0, 0
    for _, job in pairs(jobs.active) do
        if job.status == "running" or job.status == "starting" then
            total = total + math.max(0, math.min(100, tonumber(job.progress) or 0))
            count = count + 1
        end
    end
    return count > 0 and total / count or 0, count
end

return jobs
