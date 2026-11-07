local dashboard = require("core.dashboard_screen")
local bridge    = require("core.bridge")
local sm        = require("core.scene_manager")
local nodes     = require("core.nodes")
local widgets   = require("core.widgets")
local ext       = require("core.external")
local jobs      = require("core.jobs")

local state = { uptime_s = 0, ram_pct = 0, notes_count = 0, text_files = 0 }

local function refresh(scene, silent)
    bridge.call("system_status", {}, function(resp)
        if resp.ok and resp.system then
            state.uptime_s = resp.system.uptime_s or 0
            state.ram_pct = (resp.system.ram or {}).pct or 0
            if not silent then scene.set_status("Ready") end
        end
    end)
    bridge.call("toolbox_stats", {}, function(resp)
        if resp.ok then
            state.notes_count = resp.notes_count or 0
            state.text_files = resp.text_files or 0
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
    widget_height = 128,
    row_height = 50,
    status = "Productivity tools",

    on_enter = function(scene) refresh(scene, false) end,
    on_update = function(scene, dt)
        scene._t = (scene._t or 0) + dt
        if scene._t > 6 then scene._t = 0; refresh(scene, true) end
    end,

    widgets_draw = function(scene, alpha)
        local W = love.graphics.getWidth()
        local nc = nodes.color_for(4)
        widgets.status_card(12, 62, (W-40)/2, 56, "text",
            "Notes", string.format("%d saved", state.notes_count), nc, "TXT", alpha)
        widgets.status_card(12 + (W-40)/2 + 8, 62, (W-40)/2, 56, "folder",
            "Text files", string.format("%d in data/", state.text_files),
            {0.4,0.85,0.9}, "DATA", alpha)
        widgets.info_row(20, 126, W-40, "Uptime", fmt_uptime(state.uptime_s),
                         {0.75,0.80,0.85}, alpha)
        widgets.info_row(20, 146, W-40, "RAM",
                         string.format("%d%%", state.ram_pct), nc, alpha)
    end,

    items = {
        { icon = "folder", label = "File Manager", value = "File-GD X",
          desc = "Dual-pane file manager with diagnostics",
          action = function(scene)
              scene.set_status("Starting File-GD X...")
              jobs.start_tool("file_gd_x", "File Manager", "toolbox",
                  function(resp)
                      if resp.ok then
                          scene.set_status("File-GD X started — SELECT for details")
                      else
                          scene.set_status("Failed: " .. (resp.error or "?"))
                      end
                  end)
              return "Starting..."
          end },
        { icon = "calc", label = "Calculator", desc = "Scientific + RPN styles",
          action = function() sm.push("tool_calc", {}) end },
        { icon = "clock", label = "Clock", value = "LIVE",
          desc = "Analog + digital with orbital seconds",
          action = function() sm.push("tool_clock", {}) end },
        { icon = "cal", label = "Calendar", desc = "Events and reminders",
          action = function(scene) scene.set_status("Calendar: soon"); return "Calendar" end },
        { icon = "text", label = "Notes", desc = "Quick notes board",
          action = function(scene) scene.set_status("Notes: soon"); return "Notes" end },
        { icon = "text", label = "Text editor", value = "NEW",
          desc = "VOID EDIT — animated typewriter mode",
          action = function() sm.push("tool_editor", {}) end },
        { icon = "terminal", label = "Shell terminal", desc = "Real PTY with on-screen keyboard",
          action = function(scene) scene.set_status("Shell: soon"); return "Shell" end },
        { icon = "globe", label = "RSS reader", desc = "News, tech, anime feeds",
          action = function(scene) scene.set_status("RSS: soon"); return "RSS" end },
        { icon = "sun", label = "Weather", desc = "Forecasts for monitored cities",
          action = function(scene) scene.set_status("Weather: soon"); return "Weather" end },
        { icon = "uplink", label = "External tools", value = ">",
          desc = "VoidCast, BGM Normalizer, Tailscale, prototypes",
          action = function() sm.push("hub_external", {}) end },
        { icon = "back", label = "Back", desc = "Return to Nexus",
          action = function() sm.back() end },
    },
})
