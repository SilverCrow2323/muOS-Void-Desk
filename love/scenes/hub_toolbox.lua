local dashboard = require("core.dashboard_screen")
local bridge    = require("core.bridge")
local sm        = require("core.scene_manager")
local nodes     = require("core.nodes")
local widgets   = require("core.widgets")
local jobs      = require("core.jobs")
local L         = require("core.layout")

local state = { uptime_s = 0, ram_pct = 0 }

local function refresh(scene, silent)
    bridge.call("system_status", {}, function(resp)
        if resp.ok and resp.system then
            state.uptime_s = resp.system.uptime_s or 0
            state.ram_pct = (resp.system.ram or {}).pct or 0
            if not silent then scene.set_status("Ready") end
        end
    end)
end

local function fmt_uptime(s)
    s = s or 0
    local d = math.floor(s/86400)
    local h = math.floor((s%86400)/3600)
    local m = math.floor((s%3600)/60)
    if d > 0 then return string.format("%dd%dh", d, h) end
    if h > 0 then return string.format("%dh%dm", h, m) end
    return string.format("%dm", m)
end

return dashboard.new({
    title = "RT:TOOLBOX",
    node_idx = 4,
    widget_height = L.WIDGET_H,
    row_height = L.MENU_ROW_H,
    status = "Productivity tools",

    on_enter = function(scene) refresh(scene, false) end,
    on_update = function(scene, dt)
        scene._t = (scene._t or 0) + dt
        if scene._t > 6 then scene._t = 0; refresh(scene, true) end
    end,

    widgets_draw = function(scene, alpha)
        local W = love.graphics.getWidth()
        local nc = nodes.color_for(4)
        local cy = 62
        local ch = 66
        widgets.status_card(12, cy, (W-40)/2, ch, "clock",
            "Uptime", fmt_uptime(state.uptime_s), nc, "LIVE", alpha)
        widgets.status_card(12 + (W-40)/2 + 8, cy, (W-40)/2, ch, "cpu",
            "RAM", string.format("%d%%", state.ram_pct),
            {0.4,0.85,0.9}, "SYSTEM", alpha)
    end,

    items = {
        { icon = "cal", label = "Calendar", value = "NOV",
          desc = "Temporal Drift — animated monthly grid",
          action = function() sm.push("hub_calendar", {}) end },
        { icon = "terminal", label = "Shell terminal", value = "PTY",
          desc = "Void Terminal — real bash with quick commands",
          action = function() sm.push("hub_shell", {}) end },
        { icon = "folder", label = "File Manager", value = "File-GD X",
          desc = "Dual-pane file manager with diagnostics",
          action = function(scene)
              scene.set_status("Starting File-GD X...")
              jobs.start_tool("file_gd_x", "File Manager", "toolbox",
                  function(resp)
                      if resp.ok then
                          scene.set_status("File-GD X started")
                      else
                          scene.set_status("Failed: " .. (resp.error or "?"))
                      end
                  end)
              return "Starting..."
          end },
        { icon = "calc", label = "Calculator", desc = "Scientific calculator",
          action = function() sm.push("tool_calc", {}) end },
        { icon = "clock", label = "Clock", desc = "Animated analog clock",
          action = function() sm.push("tool_clock", {}) end },
        { icon = "code", label = "Python REPL", value = "PTY",
          desc = "Interactive Python 3 console in the supervised terminal",
          action = function() sm.push("hub_shell", { python_repl = true }) end },
        { icon = "text", label = "VOID Edit", value = "EDITOR",
          desc = "Controller-operated text workspace",
          action = function() sm.push("tool_editor", {}) end },
        { icon = "monitor", label = "System Monitor",
          desc = "Live CPU and RAM graphs",
          action = function() sm.push("hub_monitor", {}) end },
        { icon = "info", label = "Diagnostics",
          desc = "Read-only system, network and service checks",
          action = function() sm.push("hub_diagnostics", {}) end },
        { icon = "refresh-cw", label = "Syncthing", value = "UPLINK",
          desc = "Manage paired devices and synchronised folders",
          action = function() sm.push("hub_syncthing", {}) end },
        { icon = "globe", label = "Tailscale", value = "UPLINK",
          desc = "Private network, peers and device connectivity",
          action = function() sm.push("hub_tailscale", {}) end },
        { icon = "wifi", label = "Network control", value = "UPLINK",
          desc = "Wi-Fi, Bluetooth, hotspot and network probe",
          action = function() sm.push("hub_uplink", {}) end },
        { icon = "play", label = "muOS Apps", value = "SD1 / SD2",
          desc = "Discover and launch installed muOS applications",
          action = function() sm.push("hub_mapps", {}) end },
        { icon = "music", label = "Media Vault",
          desc = "Local media, Void Radio and the single IPTV service",
          action = function() sm.push("hub_media", {}) end },
        { icon = "uplink", label = "External tools", value = ">",
          desc = "VoidCast, BGM Normalizer and available optional tools",
          action = function() sm.push("hub_external", {}) end },
        { icon = "back", label = "Back", desc = "Return to previous scene",
          action = function() sm.back() end },
    },
})
