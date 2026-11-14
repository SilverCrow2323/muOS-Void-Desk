local dashboard = require("core.dashboard_screen")
local bridge = require("core.bridge")
local sm = require("core.scene_manager")
local nodes = require("core.nodes")
local widgets = require("core.widgets")
local font = require("core.font")

local state = {
    cpu = 0,
    ram = {used_mb = 0, total_mb = 0, pct = 0},
    temp_c = nil,
    uptime_s = 0,
    cpu_history = {},
    ram_history = {},
}

local function push_sample(values, value)
    values[#values + 1] = math.max(0, math.min(100, tonumber(value) or 0))
    while #values > 60 do table.remove(values, 1) end
end

local function refresh(scene, silent)
    bridge.call("system_status", {}, function(resp)
        if not resp.ok or not resp.system then
            if not silent then scene.set_status(resp.error or "Monitor unavailable") end
            return
        end
        local system = resp.system
        state.cpu = tonumber(system.cpu) or 0
        state.ram = system.ram or state.ram
        state.temp_c = system.temp_c
        state.uptime_s = system.uptime_s or 0
        push_sample(state.cpu_history, state.cpu)
        push_sample(state.ram_history, state.ram.pct or 0)
        if not silent then scene.set_status("Live system monitor updated") end
    end)
end

local function fmt_uptime(seconds)
    local d = math.floor((seconds or 0) / 86400)
    local h = math.floor(((seconds or 0) % 86400) / 3600)
    local m = math.floor(((seconds or 0) % 3600) / 60)
    if d > 0 then return string.format("%dd %dh", d, h) end
    if h > 0 then return string.format("%dh %dm", h, m) end
    return string.format("%dm", m)
end

local function graph(x, y, w, h, values, label, value, color, alpha)
    love.graphics.setColor(0.035, 0.045, 0.065, 0.94 * alpha)
    love.graphics.rectangle("fill", x, y, w, h, 6)
    love.graphics.setColor(color[1], color[2], color[3], 0.55 * alpha)
    love.graphics.rectangle("line", x, y, w, h, 6)
    love.graphics.setColor(0.25, 0.29, 0.34, 0.5 * alpha)
    for i = 1, 3 do
        local gy = y + h * i / 4
        love.graphics.line(x + 8, gy, x + w - 8, gy)
    end
    local f = font.regular(10) or love.graphics.newFont(10)
    love.graphics.setFont(f)
    love.graphics.setColor(0.88, 0.91, 0.95, alpha)
    love.graphics.print(label, x + 9, y + 7)
    love.graphics.setColor(color[1], color[2], color[3], alpha)
    love.graphics.print(string.format("%.0f%%", value or 0),
        x + w - 44, y + 7)
    if #values > 1 then
        local points = {}
        for i, sample in ipairs(values) do
            local px = x + 8 + (w - 16) * (i - 1) / (#values - 1)
            local py = y + h - 12 - (h - 36) * sample / 100
            points[#points + 1] = px
            points[#points + 1] = py
        end
        love.graphics.setColor(color[1], color[2], color[3], alpha)
        love.graphics.setLineWidth(2)
        love.graphics.line(points)
        love.graphics.setLineWidth(1)
    end
end

return dashboard.new({
    title = "VOID MONITOR",
    node_idx = 6,
    widget_height = 150,
    row_height = 46,
    status = "Live CPU and memory history",

    on_enter = function(scene)
        state.cpu_history, state.ram_history = {}, {}
        refresh(scene, false)
    end,
    on_update = function(scene, dt)
        scene._t = (scene._t or 0) + dt
        if scene._t >= 1.5 then
            scene._t = 0
            refresh(scene, true)
        end
    end,

    widgets_draw = function(scene, alpha)
        local W = love.graphics.getWidth()
        local nc = nodes.color_for(6)
        local half = (W - 36) / 2
        graph(12, 62, half, 116, state.cpu_history, "CPU", state.cpu, nc, alpha)
        graph(24 + half, 62, half, 116, state.ram_history, "RAM",
            state.ram.pct or 0, {0.35, 0.8, 1.0}, alpha)
        local temp = state.temp_c and string.format("%.1f°C", state.temp_c) or "—"
        widgets.info_row(20, 188, W - 40, "Temperature", temp,
            {0.95, 0.65, 0.35}, alpha)
        widgets.info_row(20, 208, W - 40, "Uptime", fmt_uptime(state.uptime_s),
            nc, alpha)
    end,

    items = {
        {icon = "refresh", label = "Sample now",
         desc = "Take an immediate CPU/RAM sample",
         action = function(scene) refresh(scene, false); return "Sampling..." end},
        {icon = "info", label = "Diagnostics",
         desc = "Open read-only system and service checks",
         action = function() sm.push("hub_diagnostics", {}) end},
        {icon = "back", label = "Back",
         desc = "Return to Workshop",
         action = function() sm.back() end},
    },
})
