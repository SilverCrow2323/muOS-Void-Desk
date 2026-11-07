local dashboard = require("core.dashboard_screen")
local bridge    = require("core.bridge")
local sm        = require("core.scene_manager")
local widgets   = require("core.widgets")
local nodes     = require("core.nodes")
local font      = require("core.font")

local state = {
    cpu = 0,
    ram = { used_mb = 0, total_mb = 0, pct = 0 },
    disk = {},
    uptime_s = 0,
    temp_c = nil,
    kernel = "—",
}

local function refresh(scene, silent)
    if not silent then scene.set_status("Gathering system info...") end
    bridge.call("system_status", {}, function(resp)
        if resp.ok and resp.system then
            local s = resp.system
            state.cpu = s.cpu or 0
            state.ram = s.ram or state.ram
            state.disk = s.disk or {}
            state.uptime_s = s.uptime_s or 0
            state.temp_c = s.temp_c
            state.kernel = s.kernel or "—"
            if not silent then scene.set_status("System state updated") end
        else
            scene.set_status("Stats: " .. (resp.error or "failed"))
        end
    end)
end

local function fmt_uptime(s)
    s = s or 0
    local d = math.floor(s / 86400)
    local h = math.floor((s % 86400) / 3600)
    local m = math.floor((s % 3600) / 60)
    if d > 0 then return string.format("%dd%dh", d, h) end
    if h > 0 then return string.format("%dh%dm", h, m) end
    return string.format("%dm", m)
end

return dashboard.new({
    title = "WORKSHOP",
    node_idx = 6,
    widget_height = 160,
    status = "System maintenance",

    on_enter = function(self) refresh(self, false) end,
    on_update = function(self, dt)
        self._t = (self._t or 0) + dt
        if self._t > 3 then self._t = 0; refresh(self, true) end
    end,

    widgets_draw = function(scene, alpha)
        local W = love.graphics.getWidth()
        local nc = nodes.color_for(6)

        -- CPU gauge on the left
        widgets.gauge(58, 118, 34, state.cpu, "CPU", nc, alpha)

        -- Bars on the right
        local bx = 110
        local bw = W - bx - 14

        widgets.stat_bar(bx, 70, bw, 20, "RAM",
                         string.format("%d/%d MB", state.ram.used_mb, state.ram.total_mb),
                         state.ram.pct,
                         state.ram.pct > 80 and {1.0, 0.4, 0.4} or {0.40, 0.85, 0.50},
                         alpha)

        local dy = 100
        for i = 1, math.min(2, #state.disk) do
            local d = state.disk[i]
            local lbl = d.mount == "/" and "ROOT"
                     or ((d.mount:match("/mnt/([%w]+)") or d.mount):upper())
            widgets.stat_bar(bx, dy, bw, 18,
                             lbl .. " (" .. string.format("%.1f", d.free_gb or 0) .. "GB free)",
                             string.format("%d%%", d.pct or 0),
                             d.pct or 0,
                             (d.pct or 0) > 90 and {1.0, 0.4, 0.4} or nc,
                             alpha)
            dy = dy + 22
        end

        -- Info strip (uptime/temp/kernel)
        local iy = dy + 2
        love.graphics.setColor(0.04, 0.05, 0.07, 0.9 * alpha)
        love.graphics.rectangle("fill", 12, iy, W - 24, 22, 4)
        love.graphics.setFont(font.regular(10) or love.graphics.newFont(10))
        love.graphics.setColor(0.72, 0.78, 0.84, alpha)
        local temp = state.temp_c and string.format("%.1f°C", state.temp_c) or "—"
        love.graphics.print(string.format(
            "Uptime %s   ·   Temp %s   ·   Kernel %s",
            fmt_uptime(state.uptime_s), temp, state.kernel), 20, iy + 6)
    end,

    items = {
        { badge = "D", label = "Void Diag",
          desc = "Full diagnostic scan",
          action = function(scene) scene.set_status("Diag: coming soon"); return "Diag: coming soon" end },
        { badge = "M", label = "Void Monitor",
          desc = "Live CPU/RAM/temp graphs",
          action = function(scene) scene.set_status("Monitor: coming soon"); return "Monitor: coming soon" end },
        { badge = "C", label = "Clean apt cache",
          desc = "Reclaim disk space in the image",
          action = function(scene) scene.set_status("Clean: coming soon"); return "Clean: coming soon" end },
        { badge = "L", label = "Logs",
          desc = "Service and system logs",
          action = function(scene) scene.set_status("Logs: coming soon"); return "Logs: coming soon" end },
        { badge = "<", label = "Back",
          desc = "Return to Nexus",
          action = function() sm.switch("nexus", {}) end },
    },
})
