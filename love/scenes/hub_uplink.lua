local dashboard = require("core.dashboard_screen")
local bridge    = require("core.bridge")
local sm        = require("core.scene_manager")
local widgets   = require("core.widgets")
local nodes     = require("core.nodes")
local font      = require("core.font")
local ext = require("core.external")

local state = {
    wifi    = { connected = false, ssid = "—", signal = 0, ip = "—" },
    bt      = { on = false, count = 0 },
    hotspot = { on = false, ssid = "—" },
    info    = { hostname = "—", gateway = "—" },
}

local function refresh(scene, silent)
    if not silent then scene.set_status("Querying network...") end
    bridge.call("network_status", {}, function(resp)
        if resp.ok and resp.network then
            state.wifi    = resp.network.wifi    or state.wifi
            state.bt      = resp.network.bt      or state.bt
            state.hotspot = resp.network.hotspot or state.hotspot
            state.info    = resp.network.info    or state.info
            if not silent then scene.set_status("Network state updated") end
        else
            scene.set_status("Network: " .. (resp.error or resp.reason or "unavailable"))
        end
    end)
end

return dashboard.new({
    title = "UPLINK",
    node_idx = 5,
    widget_height = 158,
    status = "Network control center",

    on_enter = function(self) refresh(self, false) end,
    on_update = function(self, dt)
        self._t = (self._t or 0) + dt
        if self._t > 5 then self._t = 0; refresh(self, true) end
    end,

    widgets_draw = function(scene, alpha)
        local W = love.graphics.getWidth()
        local nc = nodes.color_for(5)

        -- Row 1: 3 status cards
        local cy = 62
        local ch = 68
        local cw = (W - 40) / 3
        local gap = 8

        local w_c = state.wifi.connected and {0.40, 0.90, 0.50} or {0.55, 0.58, 0.62}
        widgets.status_card(12, cy, cw, ch, "wifi",
            "Wi-Fi", state.wifi.ssid or "—",
            w_c, state.wifi.connected and "ON" or "OFF", alpha)

        local b_c = state.bt.on and {0.35, 0.75, 0.95} or {0.55, 0.58, 0.62}
        widgets.status_card(12 + cw + gap, cy, cw, ch, "bluetooth",
            "Bluetooth", string.format("%d paired", state.bt.count or 0),
            b_c, state.bt.on and "ON" or "OFF", alpha)

        local h_c = state.hotspot.on and {1.00, 0.72, 0.20} or {0.55, 0.58, 0.62}
        widgets.status_card(12 + 2 * (cw + gap), cy, cw, ch, "signal",
            "Hotspot", state.hotspot.on and (state.hotspot.ssid or "active") or "off",
            h_c, state.hotspot.on and "ON" or "OFF", alpha)

        -- Row 2: info panel
        local iy = cy + ch + 6
        local ih = 52
        love.graphics.setColor(0.05, 0.06, 0.08, 0.92 * alpha)
        love.graphics.rectangle("fill", 12, iy, W - 24, ih, 6)
        love.graphics.setColor(nc[1], nc[2], nc[3], 0.45 * alpha)
        love.graphics.setLineWidth(1)
        love.graphics.rectangle("line", 12, iy, W - 24, ih, 6)

        local col_w = (W - 32) / 2
        local f_lbl = font.bold(9) or love.graphics.newFont(9)
        love.graphics.setFont(f_lbl)
        love.graphics.setColor(nc[1], nc[2], nc[3], alpha)
        love.graphics.print("NETWORK", 20, iy + 4)

        widgets.info_row(20, iy + 18, col_w - 8, "IP",
                         state.wifi.ip or "—", {0.40, 0.90, 0.50}, alpha)
        widgets.info_row(20, iy + 33, col_w - 8, "Signal",
                         string.format("%d%%", state.wifi.signal or 0),
                         nc, alpha)
        widgets.info_row(20 + col_w, iy + 18, col_w - 8, "Hostname",
                         state.info.hostname or "—", {0.85, 0.88, 0.92}, alpha)
        widgets.info_row(20 + col_w, iy + 33, col_w - 8, "Gateway",
                         state.info.gateway or "—", {0.85, 0.88, 0.92}, alpha)
    end,

    items = {
        { badge = "W", label = "Scan Wi-Fi networks",
          desc = "Find and connect to available networks",
          action = function(scene)
              bridge.call("wifi_scan", {}, function(resp)
                  if resp.ok then
                      scene.set_status(string.format("Found %d networks", #(resp.networks or {})))
                  else
                      scene.set_status("Wi-Fi: " .. (resp.error or resp.reason or "failed"))
                  end
              end)
              return "Scanning Wi-Fi..."
          end },
        { badge = "B", label = "Bluetooth devices",
          desc = "Pair controllers, headphones, keyboards",
          action = function(scene)
              bridge.call("bt_scan", {}, function(resp)
                  if resp.ok then
                      scene.set_status(string.format("Found %d devices", #(resp.devices or {})))
                  else
                      scene.set_status("BT: " .. (resp.error or resp.reason or "failed"))
                  end
              end)
              return "Scanning Bluetooth..."
          end },
        { badge = "H", label = "Toggle hotspot",
          desc = "Share your connection as a Wi-Fi AP",
          action = function(scene)
              bridge.call("hotspot_toggle", {}, function(resp)
                  scene.set_status("Hotspot: " .. (resp.state or resp.error or "toggling"))
              end)
              return "Toggling hotspot..."
          end },
        { badge = "R", label = "Refresh network info",
          desc = "Re-query IP, signal and gateway",
          action = function(scene) refresh(scene, false); return "Refreshing..." end },
        { badge = "<", label = "Back",
          desc = "Return to Nexus",
          action = function() sm.switch("nexus", {}) end },
    },
})
