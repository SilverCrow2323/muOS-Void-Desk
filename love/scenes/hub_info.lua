local dashboard = require("core.dashboard_screen")
local bridge    = require("core.bridge")
local sm        = require("core.scene_manager")
local nodes     = require("core.nodes")
local widgets   = require("core.widgets")

local state = {
    os = "—", machine = "—", hostname = "—", ip = "—", disk_free_gb = 0,
}

local function refresh(scene)
    bridge.call("system_info", {}, function(resp)
        if resp.ok and resp.info then
            state.os = resp.info.os or "—"
            state.machine = resp.info.machine or "—"
            state.hostname = resp.info.hostname or "—"
            state.ip = resp.info.ip or "—"
            state.disk_free_gb = resp.info.disk_free_gb or 0
            scene.set_status("Ready")
        end
    end)
end

return dashboard.new({
    title = "INFO & ABOUT",
    node_idx = 8,
    widget_height = 130,
    status = "Project archive",

    on_enter = function(scene) refresh(scene) end,

    widgets_draw = function(scene, alpha)
        local W = love.graphics.getWidth()
        local nc = nodes.color_for(8)

        widgets.status_card(12, 62, (W - 40)/2, 56, "info",
            "VoidDesk", "v10.5.1 (NEXUS)", nc, "BUILD", alpha)
        widgets.status_card(12 + (W-40)/2 + 8, 62, (W - 40)/2, 56, "globe",
            "Platform", state.machine, {0.4, 0.85, 0.9},
            state.os:upper(), alpha)

        widgets.info_row(20, 128, W - 40, "Hostname", state.hostname, nc, alpha)
        widgets.info_row(20, 148, W - 40, "IP", state.ip, {0.4, 0.9, 0.5}, alpha)
        widgets.info_row(20, 168, W - 40, "Disk free",
                         string.format("%.1f GB", state.disk_free_gb),
                         {0.75, 0.80, 0.85}, alpha)
    end,

    items = {
        { badge = "A", label = "About VoidDesk",
          desc = "Version, credits, ecosystem",
          action = function(scene)
              scene.set_status("VoidDesk v10.5.1 · LÖVE 11.5 · SPDW Factory")
              return "About"
          end },
        { badge = "M", label = "Controls guide",
          desc = "D-pad, A, B, M and gestures",
          action = function(scene)
              scene.set_status("D-pad: navigate  ·  A: open  ·  B: back  ·  M: notifications")
              return "Controls guide"
          end },
        { badge = "P", label = "Platform check",
          desc = "Refresh OS/machine/IP info",
          action = function(scene) refresh(scene); return "Refreshing..." end },
        { badge = "<", label = "Back",
          desc = "Return to Nexus",
          action = function() sm.switch("nexus", {}) end },
    },
})
