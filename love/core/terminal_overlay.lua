-- Terminal ID overlay (full-screen, opened with SELECT)
local jobs    = require("core.jobs")
local font    = require("core.font")
local theme   = require("theme.loader")
local chrome  = require("core.chrome")
local input   = require("core.input")
local icon    = require("core.icon")

local term = {}
local selected_idx = 1
local log_cache = {}
local log_cache_t = {}

local function ensure_log(job_id)
    local now = love.timer.getTime()
    if log_cache[job_id] and (now - (log_cache_t[job_id] or 0)) < 1.0 then
        return log_cache[job_id]
    end
    jobs.get_log(job_id, function(resp)
        if resp.ok then
            log_cache[job_id] = resp.lines or {}
            log_cache_t[job_id] = love.timer.getTime()
        end
    end)
    return log_cache[job_id] or {}
end

local function status_color(status)
    if status == "done"      then return {0.4, 0.9, 0.5}  end
    if status == "error"     then return {1.0, 0.3, 0.3}  end
    if status == "cancelled" then return {0.6, 0.6, 0.6}  end
    return {0.9, 0.8, 0.4}   -- running / starting
end

function term.draw(W, H)
    if not jobs.overlay_open then return end
    local th = theme.get()
    local list = jobs.list_active()

    -- backdrop
    love.graphics.setColor(0, 0, 0, 0.85)
    love.graphics.rectangle("fill", 0, 0, W, H)

    -- frame
    love.graphics.setColor(0.06, 0.07, 0.10, 1)
    love.graphics.rectangle("fill", 20, 60, W - 40, H - 140, 8)
    love.graphics.setColor(0.3, 0.5, 0.7, 1)
    love.graphics.setLineWidth(2)
    love.graphics.rectangle("line", 20, 60, W - 40, H - 140, 8)

    -- title bar
    love.graphics.setColor(0.10, 0.14, 0.20, 1)
    love.graphics.rectangle("fill", 22, 62, W - 44, 30, 6, 6)
    local f_big = font.bold(16) or love.graphics.newFont(16)
    love.graphics.setFont(f_big)
    love.graphics.setColor(0.9, 0.95, 1.0, 1)
    love.graphics.print("Terminal I.D.", 34, 68)
    love.graphics.setColor(0.5, 0.55, 0.6, 1)
    local f_small = font.regular(11) or love.graphics.newFont(11)
    love.graphics.setFont(f_small)
    love.graphics.print(
        string.format("%d job%s running   ·   L1/R1: tab   ·   B: close",
            #list, (#list == 1) and "" or "s"),
        W - 340, 72)

    if #list == 0 then
        local f = font.regular(14) or love.graphics.newFont(14)
        love.graphics.setFont(f)
        love.graphics.setColor(0.5, 0.55, 0.6, 1)
        love.graphics.print("No jobs", W/2 - 30, H/2)
        return
    end

    -- Selected job
    if selected_idx > #list then selected_idx = 1 end
    if selected_idx < 1 then selected_idx = #list end
    local job = list[selected_idx]

    -- Sidebar (tabs) left 160px
    local sidebar_x = 34
    local sidebar_y = 100
    local sidebar_w = 155
    local row_h = 32
    for i, j in ipairs(list) do
        local y = sidebar_y + (i - 1) * row_h
        local is_sel = (i == selected_idx)
        local col = j.color or {0.5, 0.7, 0.9}
        if is_sel then
            love.graphics.setColor(col[1], col[2], col[3], 0.25)
            love.graphics.rectangle("fill", sidebar_x, y, sidebar_w, row_h - 4, 4)
            love.graphics.setColor(col[1], col[2], col[3], 1)
            love.graphics.setLineWidth(2)
            love.graphics.rectangle("line", sidebar_x, y, sidebar_w, row_h - 4, 4)
        else
            love.graphics.setColor(0.10, 0.12, 0.15, 1)
            love.graphics.rectangle("fill", sidebar_x, y, sidebar_w, row_h - 4, 4)
        end
        -- Status dot
        local sc = status_color(j.status)
        love.graphics.setColor(sc[1], sc[2], sc[3], 1)
        love.graphics.circle("fill", sidebar_x + 12, y + 14, 4)
        -- Name
        local f_n = font.regular(11) or love.graphics.newFont(11)
        love.graphics.setFont(f_n)
        love.graphics.setColor(is_sel and col or {0.75, 0.8, 0.85})
        local nm = j.name
        while #nm > 3 and f_n:getWidth(nm) > (sidebar_w - 30) do
            nm = nm:sub(1, #nm - 4) .. "..."
        end
        love.graphics.print(nm, sidebar_x + 22, y + 6)
    end

    -- Log area (right)
    local log_x = sidebar_x + sidebar_w + 12
    local log_y = sidebar_y
    local log_w = W - log_x - 34
    local log_h = H - log_y - 145

    love.graphics.setColor(0.02, 0.03, 0.05, 1)
    love.graphics.rectangle("fill", log_x, log_y, log_w, log_h, 4)
    love.graphics.setColor(0.2, 0.3, 0.4, 1)
    love.graphics.setLineWidth(1)
    love.graphics.rectangle("line", log_x, log_y, log_w, log_h, 4)

    -- Log lines
    local lines = ensure_log(job.id)
    local f_mono = font.mono(10) or love.graphics.newFont(10)
    love.graphics.setFont(f_mono)
    local line_h = 13
    local visible = math.floor((log_h - 8) / line_h)
    local start = math.max(1, #lines - visible + 1)
    local yy = log_y + 4
    for i = start, #lines do
        local line = lines[i]
        love.graphics.setColor(0.75, 0.85, 0.9, 1)
        if line:find("error") or line:find("ERROR") or line:find("fatal") then
            love.graphics.setColor(1, 0.5, 0.5, 1)
        elseif line:find("done") or line:find("OK") then
            love.graphics.setColor(0.5, 0.95, 0.5, 1)
        end
        love.graphics.print(line:sub(1, 100), log_x + 4, yy)
        yy = yy + line_h
    end

    -- Progress bar (bottom of overlay)
    local bar_x = 34
    local bar_y = H - 92
    local bar_w = W - 68
    local bar_h = 16

    love.graphics.setColor(0.1, 0.12, 0.15, 1)
    love.graphics.rectangle("fill", bar_x, bar_y, bar_w, bar_h, 4)
    local col = job.color or {0.5, 0.7, 0.9}
    local fill_w = bar_w * (job.progress or 0) / 100
    if fill_w > 1 then
        love.graphics.setColor(col[1], col[2], col[3], 1)
        love.graphics.rectangle("fill", bar_x, bar_y, fill_w, bar_h, 4)
    end
    love.graphics.setColor(col[1], col[2], col[3], 0.6)
    love.graphics.setLineWidth(1)
    love.graphics.rectangle("line", bar_x, bar_y, bar_w, bar_h, 4)

    -- Progress text
    local f_prog = font.bold(14) or love.graphics.newFont(14)
    love.graphics.setFont(f_prog)
    local pct = math.floor(job.progress or 0)
    local sc = status_color(job.status)
    love.graphics.setColor(sc[1], sc[2], sc[3], 1)
    love.graphics.print(string.format("%s  ·  %d%%  ·  %s",
        job.name, pct, job.status),
        34, H - 68)
end

function term.keypressed(key)
    if not jobs.overlay_open then return false end
    local list = jobs.list_active()
    if key == "b" or key == "escape" then
        jobs.overlay_open = false
        return true
    end
    return false
end

function term.joystickpressed(joy, btn)
    if not jobs.overlay_open then return false end
    local list = jobs.list_active()
    if btn == 4 then  -- L1
        if #list > 0 then
            selected_idx = ((selected_idx - 2) % #list) + 1
        end
        return true
    elseif btn == 5 then  -- R1
        if #list > 0 then
            selected_idx = (selected_idx % #list) + 1
        end
        return true
    elseif btn == 1 then  -- B
        jobs.overlay_open = false
        return true
    end
    return false
end

return term
