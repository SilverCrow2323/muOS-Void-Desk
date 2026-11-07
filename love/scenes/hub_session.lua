local menu_screen = require("core.menu_screen")
local bridge = require("core.bridge")
local sm = require("core.scene_manager")

return menu_screen.new({
    title = "START SESSION",
    node_idx = 0,
    items = {
        { badge = "X", label = "XFCE Desktop",
          desc = "Full desktop environment",
          action = function(scene)
              scene.set_status("Launching XFCE...")
              bridge.call("xfce_launch", {}, function(resp)
                  if resp.ok then
                      scene.set_status("XFCE: " .. (resp.note or "running"))
                  else
                      scene.set_status("XFCE: " .. (resp.error or "failed"))
                  end
              end)
              return "Launching XFCE..."
          end },
        { badge = "I", label = "IceWM",
          desc = "Light window manager (~10MB RAM)",
          action = function(scene)
              scene.set_status("IceWM: coming soon")
              return "IceWM: coming soon"
          end },
        { badge = "L", label = "LXDE",
          desc = "Lightweight full desktop",
          action = function(scene)
              scene.set_status("LXDE: coming soon")
              return "LXDE: coming soon"
          end },
        { badge = "R", label = "Repair desktop image",
          desc = "Verify and repair the chroot",
          action = function(scene)
              scene.set_status("Repair: coming soon")
              return "Repair: coming soon"
          end },
        { badge = "<", label = "Back",
          desc = "Return to Nexus",
          action = function() sm.switch("nexus", {}) end },
    },
})
