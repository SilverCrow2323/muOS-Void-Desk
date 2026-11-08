local dashboard = require("core.dashboard_screen")
local bridge = require("core.bridge")
local sm = require("core.scene_manager")
local nodes = require("core.nodes")
local widgets = require("core.widgets")

local state = {
    system = {},
    network = {},
    media = {},
    tailscale = {},
    syncthing = {},
    errors = {},
}

local function refresh(scene, silent)
    state.errors = {}
    local pending = 5
    local function done()
        pending = pending - 1
        if pending <= 0 and not silent then
            scene.set_status("Diagnostic snapshot complete")
        end
    end
    local function failed(name, resp)
        state.errors[#state.errors + 1] = name .. ": " ..
            tostring(resp.error or resp.message or "unavailable")
    end

    bridge.call("system_status", {}, function(resp)
        if resp.ok then state.system = resp.system or {}
        else failed("System", resp) end
        done()
    end)
    bridge.call("network_status", {}, function(resp)
        if resp.ok then state.network = resp.network or {}
        else failed("Network", resp) end
        done()
    end)
    bridge.call("media_status", {}, function(resp)
        if resp.ok then state.media = resp.media or {}
        else failed("Media", resp) end
        done()
    end)
    bridge.call("tailscale_status", {}, function(resp)
        if resp.ok then state.tailscale = resp
        else failed("Tailscale", resp) end
        done()
    end)
    bridge.call("syncthing_status", {}, function(resp)
        if resp.ok then state.syncthing = resp
        else failed("Syncthing", resp) end
        done()
    end)
    if not silent then scene.set_status("Running diagnostic checks...") end
end

local function network_label()
    local wifi = state.network.wifi or {}
    if wifi.connected then
        return tostring(wifi.ssid or "Wi-Fi") .. " · " .. tostring(wifi.ip or "—")
    end
    return "Wi-Fi disconnected"
end

local function disk_label()
    local disk = state.system.disk or {}
    local root = disk[1]
    if not root then return "—" end
    return string.format("%.1f GB free", root.free_gb or 0)
end

return dashboard.new({
    title = "VOID DIAGNOSTICS",
    node_idx = 6,
    widget_height = 142,
    row_height = 46,
    status = "Read-only system and service checks",

    on_enter = function(scene) refresh(scene, false) end,
    on_update = function(scene, dt)
        scene._t = (scene._t or 0) + dt
        if scene._t > 12 then scene._t = 0; refresh(scene, true) end
    end,

    widgets_draw = function(scene, alpha)
        local W = love.graphics.getWidth()
        local nc = nodes.color_for(6)
        local system = state.system
        local ram = system.ram or {}
        local wifi = state.network.wifi or {}
        local bt = state.network.bt or {}
        local ts = state.tailscale
        local sync = state.syncthing

        widgets.status_card(12, 62, (W - 40) / 2, 58, "cpu",
            "System", string.format("CPU %.0f%% · RAM %.0f%%",
                system.cpu or 0, ram.pct or 0),
            nc, "CHECKED", alpha)
        widgets.status_card(20 + (W - 40) / 2, 62, (W - 40) / 2, 58, "wifi",
            "Network", network_label(),
            wifi.connected and {0.4, 0.9, 0.5} or {0.8, 0.6, 0.35},
            wifi.connected and "ONLINE" or "OFFLINE", alpha)
        widgets.info_row(20, 130, W - 40, "Disk", disk_label(), nc, alpha)
        widgets.info_row(20, 150, W - 40, "Bluetooth",
            bt.on and "Enabled" or "Disabled", nc, alpha)
        widgets.info_row(20, 170, W - 40, "Tailscale",
            ts.installed and tostring(ts.backend or "Installed") or "Not installed",
            {0.35, 0.8, 1.0}, alpha)
        widgets.info_row(20, 190, W - 40, "Syncthing",
            sync.available and "Running" or "Not configured",
            sync.available and {0.4, 0.9, 0.5} or {0.8, 0.6, 0.35}, alpha)
    end,

    items = {
        {icon = "refresh", label = "Run checks again",
         desc = "Refresh system, network and service status",
         action = function(scene) refresh(scene, false); return "Checking..." end},
        {icon = "uplink", label = "Tailscale manager",
         desc = "Open native Uplink controls",
         action = function() sm.push("hub_tailscale", {}) end},
        {icon = "refresh-cw", label = "Syncthing manager",
         desc = "Open native folder and device controls",
         action = function() sm.push("hub_syncthing", {}) end},
        {icon = "back", label = "Back",
         desc = "Return to previous scene",
         action = function() sm.back() end},
    },
})
