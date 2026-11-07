local menu_screen = require("core.menu_screen")
local bridge = require("core.bridge")
local sm = require("core.scene_manager")

return menu_screen.new({
    title = "INFO & ABOUT",
    node_idx = 8,
    items = {
        { badge = "A", label = "About VoidDesk",
          desc = "Version, credits, ecosystem",
          action = function(scene)
              scene.set_status("VoidDesk v10.5.1 · LÖVE 11.5 · SPDW Factory")
              return "VoidDesk v10.5.1 · LÖVE 11.5 · SPDW Factory"
          end },
        { badge = "P", label = "Platform check",
          desc = "OS, machine, disk free",
          action = function(scene)
              bridge.call("system_info", {}, function(resp)
                  if resp.ok then
                      local i = resp.info or {}
                      scene.set_status(string.format("%s %s · %.1f GB free",
                          i.os or "?", i.machine or "?", i.disk_free_gb or 0))
                  else
                      scene.set_status("Platform: " .. (resp.error or "failed"))
                  end
              end)
              return "Checking platform..."
          end },
        { badge = "<", label = "Back",
          desc = "Return to Nexus",
          action = function() sm.switch("nexus", {}) end },
    },
})
