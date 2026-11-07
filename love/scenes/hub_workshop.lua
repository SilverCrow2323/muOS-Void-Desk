local menu_screen = require("core.menu_screen")
local bridge = require("core.bridge")
local sm = require("core.scene_manager")

return menu_screen.new({
    title = "WORKSHOP",
    node_idx = 6,
    items = {
        { badge = "S", label = "Device Stats",
          desc = "CPU, RAM, disk, uptime",
          action = function(scene)
              scene.set_status("Gathering stats...")
              bridge.call("system_info", {}, function(resp)
                  if resp.ok then
                      local i = resp.info or {}
                      scene.set_status(string.format(
                          "%s · %s · %.1f GB free",
                          i.os or "?", i.machine or "?", i.disk_free_gb or 0))
                  else
                      scene.set_status("Stats: " .. (resp.error or "failed"))
                  end
              end)
              return "Gathering stats..."
          end },
        { badge = "D", label = "Void Diag",
          desc = "Full system diagnostic scan",
          action = function(scene) scene.set_status("Diag: coming soon"); return "Diag: coming soon" end },
        { badge = "M", label = "Void Monitor",
          desc = "Live CPU/RAM/temp graphs",
          action = function(scene) scene.set_status("Monitor: coming soon"); return "Monitor: coming soon" end },
        { badge = "L", label = "Logs",
          desc = "View service and system logs",
          action = function(scene) scene.set_status("Logs: coming soon"); return "Logs: coming soon" end },
        { badge = "<", label = "Back",
          desc = "Return to Nexus",
          action = function() sm.switch("nexus", {}) end },
    },
})
