local dashboard = require("core.dashboard_screen")
local bridge    = require("core.bridge")
local sm        = require("core.scene_manager")
local nodes     = require("core.nodes")
local widgets   = require("core.widgets")
local ext       = require("core.external")

local state = {
    wifi    = { connected = false, ssid = "—", signal = 0, ip = "—" },
    bt      = { on = false, count = 0 },
    hotspot = { on = false, ssid = "—" },
    info    = { hostname = "—", gateway = "—" },
}

local function refresh(scene, silent)
    bridge.call("network_status", {}, function(resp)
        if resp.ok and resp.network then
            state.wifi    = resp.network.wifi    or state.wifi
            state.bt      = resp.network.bt      or state.bt
            state.hotspot = resp.network.hotspot or state.hotspot
            state.info    = resp.network.info    or state.info
            if not silent then scene.set_status("Ready") end
        end
    end)
end

return dashboard.new({
    title = "UPLINK",
    node_idx = 5,
    widget_height = 158,
    row_height = 46,
    status = "Network control",

    on_enter = function(scene) refresh(scene, false) end,
    on_update = function(scene, dt)
        scene._t = (scene._t or 0) + dt
        if scene._t > 5 then scene._t = 0; refresh(scene, true) end
    end,

    widgets_draw = function(scene, alpha)
        local W = love.graphics.getWidth()
        local nc = nodes.color_for(5)
        local cy, ch = 62, 68
        local cw = (W - 40) / 3
        local gap = 8

        local w_c = state.wifi.connected and {0.40,0.90,0.50} or {0.55,0.58,0.62}
        widgets.status_card(12, cy, cw, ch, "wifi", "Wi-Fi",
            state.wifi.ssid or "—", w_c,
            state.wifi.connected and "ON" or "OFF", alpha)

        local b_c = state.bt.on and {0.35,0.75,0.95} or {0.55,0.58,0.62}
        widgets.status_card(12 + cw + gap, cy, cw, ch, "bluetooth",
            "Bluetooth", string.format("%d paired", state.bt.count or 0),
            b_c, state.bt.on and "ON" or "OFF", alpha)

        local h_c = state.hotspot.on and {1.0,0.72,0.20} or {0.55,0.58,0.62}
        widgets.status_card(12 + 2*(cw+gap), cy, cw, ch, "signal",
            "Hotspot", state.hotspot.on and (state.hotspot.ssid or "active") or "off",
            h_c, state.hotspot.on and "ON" or "OFF", alpha)

        widgets.info_row(20, 138, W-40, "IP",
                         state.wifi.ip or "—", {0.4,0.9,0.5}, alpha)
        widgets.info_row(20, 156, W-40, "Hostname",
                         state.info.hostname or "—", nc, alpha)
    end,

    items = {
        { icon = "wifi", label = "Scan Wi-Fi",
          value = state.wifi.connected and "ON" or "OFF",
          desc = "Find and connect to available networks",
          action = function(scene)
              scene.set_status("Scanning Wi-Fi...")
              bridge.call("wifi_scan", {}, function(resp)
                  if resp.ok then
                      scene.set_status(string.format("Found %d networks", #(resp.networks or {})))
                  else
                      scene.set_status("Wi-Fi: " .. (resp.error or resp.reason or "failed"))
                  end
              end)
              return "Scanning..."
          end },
        { icon = "bluetooth", label = "Bluetooth",
          value = state.bt.on and "ON" or "OFF",
          desc = "Pair controllers, headphones, keyboards",
          action = function(scene)
              scene.set_status("Scanning Bluetooth...")
              bridge.call("bt_scan", {}, function(resp)
                  if resp.ok then
                      scene.set_status(string.format("Found %d devices", #(resp.devices or {})))
                  else
                      scene.set_status("BT: " .. (resp.error or resp.reason or "failed"))
                  end
              end)
              return "Scanning..."
          end },
        { icon = "signal", label = "Hotspot",
          value = state.hotspot.on and "ON" or "OFF",
          desc = "Share your connection as a Wi-Fi AP",
          action = function(scene)
              bridge.call("hotspot_toggle", {}, function(resp)
                  scene.set_status("Hotspot: " .. (resp.state or resp.error or "toggling"))
              end)
              return "Toggling..."
          end },
        { icon = "uplink", label = "Rt:Tailscale-M", value = "LOVE",
          desc = "Tailscale VPN: QR login, exit nodes, peers",
          action = function(scene)
              scene.set_status("Launching Rt:Tailscale-M...")
              ext.launch("rt_tailscale_m", function(resp)
                  if resp.ok then scene.set_status("Rt:Tailscale-M launched")
                  else scene.set_status("Failed: " .. (resp.error or "?")) end
              end)
              return "Launching..."
          end },
        { icon = "globe", label = "Network Probe", desc = "Diagnostics: IP, gateway, latency",
          action = function(scene)
              bridge.call("system_info", {}, function(resp)
                  if resp.ok then
                      local i = resp.info or {}
                      scene.set_status("IP: " .. (i.ip or "n/a") .. "  host: " .. (i.hostname or "?"))
                  else
                      scene.set_status("Probe: " .. (resp.error or "?"))
                  end
              end)
              return "Probing..."
          end },
        { icon = "refresh", label = "Refresh", desc = "Re-query network state",
          action = function(scene) refresh(scene, false); return "Refreshing..." end },
        { icon = "back", label = "Back", desc = "Return to Nexus",
          action = function() sm.back() end },
    },
})
