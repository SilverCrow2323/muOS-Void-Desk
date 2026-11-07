local menu_screen = require("core.menu_screen")
local bridge = require("core.bridge")
local sm = require("core.scene_manager")

return menu_screen.new({
    title = "UPLINK",
    node_idx = 5,
    items = {
        { badge = "W", label = "Wi-Fi",
          desc = "Scan networks and connect",
          action = function(scene)
              scene.set_status("Scanning Wi-Fi...")
              bridge.call("wifi_scan", {}, function(resp)
                  if resp.ok then
                      scene.set_status(string.format("Wi-Fi: %d networks found", #(resp.networks or {})))
                  else
                      scene.set_status("Wi-Fi: " .. (resp.error or resp.reason or "failed"))
                  end
              end)
              return "Scanning Wi-Fi..."
          end },
        { badge = "B", label = "Bluetooth",
          desc = "Pair devices and audio",
          action = function(scene)
              scene.set_status("Scanning Bluetooth...")
              bridge.call("bt_scan", {}, function(resp)
                  if resp.ok then
                      scene.set_status(string.format("BT: %d devices", #(resp.devices or {})))
                  else
                      scene.set_status("BT: " .. (resp.error or resp.reason or "failed"))
                  end
              end)
              return "Scanning Bluetooth..."
          end },
        { badge = "H", label = "Hotspot",
          desc = "Share connection via Wi-Fi AP",
          action = function(scene)
              scene.set_status("Hotspot: coming soon")
              return "Hotspot: coming soon"
          end },
        { badge = "N", label = "Network Probe",
          desc = "Diagnostics: IP, gateway, latency",
          action = function(scene)
              scene.set_status("Probing network...")
              bridge.call("system_info", {}, function(resp)
                  if resp.ok then
                      local i = resp.info or {}
                      scene.set_status("IP: " .. (i.ip or "n/a") .. "  |  host: " .. (i.hostname or "?"))
                  else
                      scene.set_status("Probe: " .. (resp.error or "failed"))
                  end
              end)
              return "Probing network..."
          end },
        { badge = "<", label = "Back",
          desc = "Return to Nexus",
          action = function() sm.switch("nexus", {}) end },
    },
})
