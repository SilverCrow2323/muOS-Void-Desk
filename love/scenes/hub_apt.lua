-- Native APT package manager for the optional Debian/Ubuntu XFCE image.
-- All package operations are executed by the Python service inside that chroot;
-- the muOS Buildroot host is never passed to apt.
local sm = require("core.scene_manager")
local theme = require("theme.loader")
local chrome = require("core.chrome")
local font = require("core.font")
local input = require("core.input")
local bridge = require("core.bridge")

local scene = {}
local tabs = {"SEARCH", "INSTALLED", "JOBS", "SYSTEM"}
local tab = 1
local query = "htop"
local results, installed, jobs, job_log = {}, {}, {}, {}
local selected, offset, key_selected = 1, 1, 1
local mode = "results"
local status = "Reading package catalogue..."
local busy = false
local refresh_t = 0

local system_actions = {
    {name="APT UPDATE", action="update", desc="Refresh package indexes"},
    {name="UPGRADE", action="upgrade", desc="Upgrade installed packages"},
    {name="CLEAN CACHE", action="clean", desc="Remove downloaded package archives"},
}

local keys = {
    "a","b","c","d","e","f","g","h","i","j",
    "k","l","m","n","o","p","q","r","s","t",
    "u","v","w","x","y","z","0","1","2","3",
    "4","5","6","7","8","9","-",".","+","SPACE",
    "DEL","SEARCH",
}

local function set_status(value) status = tostring(value or "") end
scene.set_status = set_status

local function installed_map()
    local map = {}
    for _, item in ipairs(installed) do
        local name = tostring(item.name or ""):match("^[^:]+")
        if name then map[name] = true end
    end
    return map
end

local function refresh_installed()
    bridge.call("apt_catalog", {mode="installed"}, function(resp)
        if resp.ok then
            installed = resp.packages or {}
        else
            set_status("Installed list: " .. (resp.error or "unavailable"))
        end
    end)
end

local function refresh_search()
    if busy then return end
    if query == "" then set_status("Enter a package name first"); return end
    busy = true
    set_status("Searching: " .. query)
    bridge.call("apt_catalog", {mode="search", query=query}, function(resp)
        busy = false
        if resp.ok then
            results = resp.packages or {}
            selected, offset = 1, 1
            set_status(string.format("%d matches for %s", #results, query))
        else
            results = {}
            set_status("Search failed: " .. (resp.error or "unknown error"))
        end
    end)
end

local function refresh_jobs()
    bridge.call("job_list", {}, function(resp)
        if resp.ok then jobs = resp.jobs or {} end
    end)
end

local function refresh_tab()
    selected, offset = 1, 1
    if tab == 1 then refresh_search()
    elseif tab == 2 then refresh_installed()
    else refresh_jobs() end
end

local function start_package_job(action, name)
    if busy then return end
    busy = true
    set_status(action:upper() .. " " .. name .. "...")
    bridge.call("job_start", {
        apt_action = action, packages = {name},
        name = action .. ": " .. name, hub = "forge",
    }, function(resp)
        busy = false
        if resp.ok then
            set_status("Job #" .. tostring(resp.job.id) .. " started")
            refresh_jobs()
            refresh_installed()
        else
            set_status("Cannot start job: " .. (resp.error or "unknown error"))
        end
    end)
end

local function selected_items()
    if tab == 1 then return results end
    if tab == 2 then return installed end
    if tab == 3 then return jobs end
    return system_actions
end

local function move_selection(delta)
    local items = selected_items()
    selected = math.max(1, math.min(math.max(1, #items), selected + delta))
    if selected < offset then offset = selected end
    if selected > offset + 5 then offset = selected - 5 end
end

local function activate_selected()
    local items = selected_items()
    local item = items[selected]
    if not item then return end
    if tab == 1 or tab == 2 then
        local name = tostring(item.name or "")
        name = name:match("^[^:]+") or name
        if name == "" then return end
        if installed_map()[name] then
            start_package_job("remove", name)
        else
            start_package_job("install", name)
        end
    elseif tab == 3 then
        if item.status == "running" then
            bridge.call("job_cancel", {job_id=item.id}, function(resp)
                set_status(resp.ok and "Cancellation requested" or
                    ("Cancel failed: " .. (resp.error or "?")))
                refresh_jobs()
            end)
        else
            bridge.call("job_log", {job_id=item.id}, function(resp)
                job_log = resp.ok and (resp.lines or {}) or {}
                set_status("Job log: " .. tostring(item.name or item.id))
            end)
        end
    elseif tab == 4 then
        if busy then return end
        busy = true
        set_status(item.name .. "...")
        bridge.call("job_start", {apt_action=item.action, packages={},
            name=item.name, hub="forge"}, function(resp)
            busy = false
            set_status(resp.ok and ("Job #" .. tostring(resp.job.id) .. " started")
                or ("Cannot start: " .. (resp.error or "unknown error")))
            refresh_jobs()
        end)
    end
end

local function key_activate()
    local key = keys[key_selected]
    if not key then return end
    if key == "SEARCH" then
        mode = "results"
        refresh_search()
    elseif key == "DEL" then
        query = query:sub(1, -2)
    elseif key == "SPACE" then
        query = query .. " "
    else
        query = query .. key
    end
end

function scene.enter()
    tab, selected, offset, key_selected = 1, 1, 1, 1
    mode, busy = "results", false
    status = "Search APT packages in the XFCE image"
    results, installed, jobs, job_log = {}, {}, {}, {}
    refresh_installed()
    refresh_search()
    input.clear()
    input.on("press", function(action)
        if action == "b" then
            if mode == "keyboard" then mode = "results"
            else sm.back() end
            return
        end
        if action == "l1" then
            tab = math.max(1, tab - 1); mode = "results"; refresh_tab(); return
        elseif action == "r1" then
            tab = math.min(#tabs, tab + 1); mode = "results"; refresh_tab(); return
        end
        if mode == "keyboard" then
            if action == "left" then key_selected = math.max(1, key_selected - 1)
            elseif action == "right" then key_selected = math.min(#keys, key_selected + 1)
            elseif action == "up" then key_selected = math.max(1, key_selected - 10)
            elseif action == "down" then key_selected = math.min(#keys, key_selected + 10)
            elseif action == "a" then key_activate()
            elseif action == "x" then query = query:sub(1, -2)
            elseif action == "start" then mode = "results"; refresh_search() end
            return
        end
        if action == "up" then move_selection(-1)
        elseif action == "down" then move_selection(1)
        elseif action == "a" then activate_selected()
        elseif action == "y" and tab == 1 then
            mode = "keyboard"; key_selected = 1
        elseif action == "x" and tab == 1 then
            query = ""; results = {}; set_status("Search cleared — press Y to type")
        elseif action == "select" then
            refresh_tab(); refresh_jobs()
        elseif action == "start" and tab == 1 then
            refresh_search()
        end
    end)
end

function scene.update(dt)
    refresh_t = refresh_t + dt
    if refresh_t >= 3 then
        refresh_t = 0
        refresh_jobs()
    end
end

local function draw_panel(x, y, w, h, accent)
    love.graphics.setColor(0.045, 0.055, 0.075, 0.96)
    love.graphics.rectangle("fill", x, y, w, h, 8)
    love.graphics.setColor(accent[1], accent[2], accent[3], 0.55)
    love.graphics.setLineWidth(1)
    love.graphics.rectangle("line", x, y, w, h, 8)
end

function scene.draw()
    local W, H = love.graphics.getDimensions()
    local th = theme.get()
    local accent = th.accent or {0.3, 0.8, 0.9}
    love.graphics.clear(th.bg[1], th.bg[2], th.bg[3], 1)
    chrome.draw_header({theme=th, title="THE FORGE", subtitle="APT MANAGER"})
    local f = font.regular(15) or love.graphics.newFont(15)
    local fb = font.bold(15) or love.graphics.newFont(15)
    love.graphics.setFont(fb)
    local tx = 18
    for i, label in ipairs(tabs) do
        local w = 110
        local active = i == tab
        love.graphics.setColor(active and accent or {0.16,0.18,0.22})
        love.graphics.rectangle("fill", tx, 68, w, 30, 6)
        love.graphics.setColor(active and {0.02,0.03,0.04} or {0.8,0.84,0.9})
        love.graphics.printf(label, tx, 76, w, "center")
        tx = tx + w + 8
    end

    draw_panel(14, 108, W - 28, mode == "keyboard" and 180 or 292, accent)
    love.graphics.setFont(fb)
    love.graphics.setColor(0.9,0.93,0.97)
    if tab == 1 then
        love.graphics.print("SEARCH  >  " .. query .. (mode == "keyboard" and "_" or ""), 26, 120)
    elseif tab == 2 then love.graphics.print("INSTALLED PACKAGES", 26, 120)
    elseif tab == 3 then love.graphics.print("BACKGROUND JOBS", 26, 120)
    else love.graphics.print("SYSTEM MAINTENANCE", 26, 120) end

    local items = selected_items()
    love.graphics.setFont(f)
    local max_rows = mode == "keyboard" and 3 or 6
    for row = 0, max_rows - 1 do
        local idx = offset + row
        local item = items[idx]
        if item then
            local y = 150 + row * 37
            if idx == selected and mode == "results" then
                love.graphics.setColor(accent[1], accent[2], accent[3], 0.22)
                love.graphics.rectangle("fill", 22, y - 4, W - 44, 32, 5)
            end
            love.graphics.setColor(0.9,0.93,0.97)
            local name = tostring(item.name or item.id or "package")
            local desc = tostring(item.description or item.version or item.status or "")
            love.graphics.print(name:sub(1, 30), 30, y)
            love.graphics.setColor(0.55,0.62,0.7)
            love.graphics.printf(desc:sub(1, 52), W * 0.47, y, W * 0.48, "left")
        end
    end

    if mode == "keyboard" then
        local kx, ky = 22, 270
        love.graphics.setFont(font.bold(13) or love.graphics.newFont(13))
        for i, key in ipairs(keys) do
            local col, row = (i - 1) % 10, math.floor((i - 1) / 10)
            local x, y = kx + col * 59, ky + row * 27
            if i == key_selected then
                love.graphics.setColor(accent[1], accent[2], accent[3], 0.55)
            else
                love.graphics.setColor(0.13,0.16,0.20,0.95)
            end
            love.graphics.rectangle("fill", x, y, 54, 23, 4)
            love.graphics.setColor(0.92,0.94,0.98)
            love.graphics.printf(key, x, y + 4, 54, "center")
        end
    elseif tab == 3 and #job_log > 0 then
        love.graphics.setFont(font.mono(11) or love.graphics.newFont(11))
        love.graphics.setColor(0.65,0.78,0.68)
        love.graphics.printf(table.concat(job_log, "  "), 26, 335, W - 52, "left")
    end

    love.graphics.setFont(font.regular(12) or love.graphics.newFont(12))
    love.graphics.setColor(0.72,0.78,0.85)
    love.graphics.printf(status, 18, H - 66, W - 36, "center")
    chrome.draw_footer({theme=th, hints={
        {icon="dpad",label="Navigate"}, {icon="a",label=tab == 3 and "Cancel / Log" or (tab == 4 and "Run" or "Install / Remove")},
        {icon="y",label=tab == 1 and "Search keys" or "Actions"}, {icon="l1",label="Tabs"}, {icon="b",label="Back"},
    }, right_text=busy and "WORKING" or "SELECT refresh"})
end

return scene
