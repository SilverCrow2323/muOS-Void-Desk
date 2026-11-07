local dashboard = require("core.dashboard_screen")
local bridge    = require("core.bridge")
local sm        = require("core.scene_manager")
local nodes     = require("core.nodes")
local widgets   = require("core.widgets")
local ext       = require("core.external")

local state = {
    uptime_s = 0,
    ram_pct = 0,
    disk_free_gb = 0,
    notes_count = 0,
    text_files = 0,
    apps_count = 0,
}

local function refresh(scene, silent)
    bridge.call("system_status", {}, function(resp)
        if resp.ok and resp.system then
            local s = resp.system
            state.uptime_s = s.uptime_s or 0
            state.ram_pct = (s.ram or {}).pct or 0
            local d = s.disk or {}
            state.disk_free_gb = d[1] and d[1].free_gb or 0
            if not silent then scene.set_status("Toolbox ready") end
        end
    end)
    bridge.call("toolbox_stats", {}, function(resp)
        if resp.ok then
            state.notes_count = resp.notes_count or 0
            state.text_files = resp.text_files or 0
            state.apps_count = resp.apps_count or 0
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

local function launch_file_gd_x(scene)
    scene.set_status("Launching File-GD X...")
    ext.launch("file_gd_x", function(resp)
        if resp.ok then
            scene.set_status("File-GD X launched")
        else
            scene.set_status("Failed: " .. (resp.error or "unknown"))
        end
    end)
    return "Launching File-GD X..."
end

return dashboard.new({
    title = "RT:TOOLBOX",
    node_idx = 4,
    widget_height = 128,
    status = "Productivity tools",

    on_enter = function(scene) refresh(scene, false) end,
    on_update = function(scene, dt)
        scene._t = (scene._t or 0) + dt
        if scene._t > 6 then
            scene._t = 0
            refresh(scene, true)
        end
    end,

    widgets_draw = function(scene, alpha)
        local W = love.graphics.getWidth()
        local nc = nodes.color_for(4)

        widgets.status_card(12, 62, (W-40)/2, 56, "text",
            "Notes", string.format("%d saved", state.notes_count),
            nc, "TXT", alpha)

        widgets.status_card(12 + (W-40)/2 + 8, 62, (W-40)/2, 56, "folder",
            "Text files", string.format("%d in data/", state.text_files),
            {0.4, 0.85, 0.9}, "DATA", alpha)

        widgets.info_row(20, 126, W-40, "Uptime",
                         fmt_uptime(state.uptime_s),
                         {0.75, 0.80, 0.85}, alpha)

        widgets.info_row(20, 146, W-40, "RAM",
                         string.format("%d%%", state.ram_pct), nc, alpha)
    end,

    items = {
        { badge = "F", label = "File Manager (File-GD X)",
          desc = "Launch File-GD X dual-pane file manager",
          action = function(scene) return launch_file_gd_x(scene) end },

        { badge = "C", label = "Calculator",
          desc = "Scientific + RPN styles",
          action = function(scene)
              scene.set_status("Calculator: coming soon")
              return "Calculator"
          end },

        { badge = "T", label = "Clock",
          desc = "Digital or analog with alarms",
          action = function(scene)
              scene.set_status("Clock: coming soon")
              return "Clock"
          end },

        { badge = "A", label = "Calendar",
          desc = "Events and reminders",
          action = function(scene)
              scene.set_status("Calendar: coming soon")
              return "Calendar"
          end },

        { badge = "N", label = "Notes",
          desc = "Quick notes board",
          action = function(scene)
              scene.set_status("Notes: coming soon")
              return "Notes"
          end },

        { badge = "E", label = "Text editor",
          desc = "VOID EDIT — D-pad native",
          action = function(scene)
              scene.set_status("Editor: coming soon")
              return "Editor"
          end },

        { badge = "S", label = "Shell terminal",
          desc = "Real PTY with on-screen keyboard",
          action = function(scene)
              scene.set_status("Shell: coming soon")
              return "Shell"
          end },

        { badge = "R", label = "RSS reader",
          desc = "News, tech, anime feeds",
          action = function(scene)
              scene.set_status("RSS: coming soon")
              return "RSS"
          end },

        { badge = "W", label = "Weather",
          desc = "Forecasts for monitored cities",
          action = function(scene)
              scene.set_status("Weather: coming soon")
              return "Weather"
          end },

        { badge = "X", label = "External tools",
          desc = "VoidCast, BGM Normalizer, Tailscale, prototypes",
          action = function() sm.switch("hub_external", {}) end },

        { badge = "<", label = "Back",
          desc = "Return to Nexus",
          action = function() sm.switch("nexus", {}) end },
    },
})
