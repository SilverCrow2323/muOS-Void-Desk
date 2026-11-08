local dashboard = require("core.dashboard_screen")
local bridge = require("core.bridge")
local sm = require("core.scene_manager")
local nodes = require("core.nodes")
local widgets = require("core.widgets")

local state = {
    installed = false,
    backend = "Checking",
    peers = {},
    taildrop = {},
    auth_url = "",
    tailnet = "",
    self = {},
    autostart = false,
    error = "",
}

local function refresh(scene, silent)
    if not silent then scene.set_status("Reading Tailscale service...") end
    bridge.call("tailscale_status", {}, function(resp)
        if not resp.ok then
            state.error = resp.error or "service query failed"
            scene.set_status("Tailscale: " .. state.error)
            return
        end
        state.installed = resp.installed == true
        state.backend = resp.backend or (state.installed and "Stopped" or "Not installed")
        state.peers = resp.peers or {}
        state.taildrop = resp.taildrop or {}
        state.auth_url = resp.auth_url or ""
        state.tailnet = resp.tailnet or ""
        state.self = resp.self or {}
        state.autostart = resp.autostart == true
        state.error = resp.error or ""
        local label = state.installed and state.backend or "service files missing"
        scene.set_status(label .. " · " .. tostring(#state.peers) .. " peers")
    end)
end

local function run_action(scene, action, value, label)
    scene.set_status(label or "Working...")
    bridge.call("tailscale_action", { action = action, value = value or "" }, function(resp)
        if resp.ok then
            if resp.job then
                scene.set_status("Setup job #" .. tostring(resp.job.id) .. " started")
            else
                scene.set_status(resp.message or resp.output or "Done")
            end
            refresh(scene, true)
        else
            scene.set_status(resp.error or resp.output or "Tailscale action failed")
        end
    end)
    return label or "Working..."
end

local function items_for()
    local items = {
        {
            icon = "refresh", label = "Refresh service status",
            desc = "Daemon, tailnet, peers and Taildrop",
            action = function(scene) refresh(scene, false); return "Refreshing..." end,
        },
        {
            icon = "play", label = "Start / repair service",
            desc = "Use Rt manager; never spawn a second tailscaled",
            action = function(scene) return run_action(scene, "start", "", "Starting service...") end,
        },
        {
            icon = "qr-code", label = "Log in to Tailscale",
            desc = "Start QR authorization; refresh to read the auth URL",
            action = function(scene) return run_action(scene, "login", "", "Starting login...") end,
        },
        {
            icon = "wifi-off", label = "Disconnect this device",
            desc = "Disable the tailnet connection without stopping the panel",
            action = function(scene) return run_action(scene, "disconnect", "", "Disconnecting...") end,
        },
    }
    for _, peer in ipairs(state.peers) do
        if peer.exit_node and peer.ip and peer.ip ~= "" then
            table.insert(items, {
                icon = "route",
                label = "Exit node: " .. tostring(peer.name or "Device"),
                value = peer.online and "ONLINE" or "OFFLINE",
                desc = tostring(peer.ip) .. " · " .. tostring(peer.os or "peer"),
                action = function(scene)
                    if not peer.online then
                        scene.set_status("This exit node is offline")
                        return "Offline"
                    end
                    return run_action(scene, "exit_node", peer.ip, "Selecting exit node...")
                end,
            })
        end
    end
    table.insert(items, {
        icon = "x-circle", label = "Clear exit node",
        desc = "Return to the normal network route",
        action = function(scene) return run_action(scene, "exit_node", "", "Clearing exit node...") end,
    })
    table.insert(items, {
        icon = "calendar-clock",
        label = state.autostart and "Disable start at boot" or "Enable start at boot",
        desc = "Manage muOS User Init Scripts through Rt:Tailscale-M",
        action = function(scene)
            local action = state.autostart and "autostart_off" or "autostart_on"
            return run_action(scene, action, "", "Updating boot startup...")
        end,
    })
    table.insert(items, {
        icon = "refresh-cw", label = "Restart Tailscale services",
        desc = "Restart through the upstream service manager",
        action = function(scene) return run_action(scene, "restart", "", "Restarting...") end,
    })
    table.insert(items, {
        icon = "back", label = "Back",
        desc = "Return to Uplink",
        action = function() sm.back() end,
    })
    return items
end

local config = {
    title = "TAILSCALE",
    node_idx = 5,
    widget_height = 142,
    row_height = 46,
    status = "Native service integration",
    on_enter = function(scene)
        refresh(scene, false)
    end,
    on_update = function(scene, dt)
        scene._t = (scene._t or 0) + dt
        if scene._t > 6 then
            scene._t = 0
            refresh(scene, true)
        end
    end,
    widgets_draw = function(scene, alpha)
        local W = love.graphics.getWidth()
        local nc = nodes.color_for(5)
        local peer_count = #state.peers
        local online = 0
        for _, peer in ipairs(state.peers) do
            if peer.online then online = online + 1 end
        end
        widgets.status_card(12, 62, (W - 40) / 2, 58, "network",
            "Backend", state.backend, nc, state.installed and "READY" or "MISSING", alpha)
        widgets.status_card(20 + (W - 40) / 2, 62, (W - 40) / 2, 58, "users",
            "Peers", string.format("%d / %d online", online, peer_count),
            online > 0 and {0.4, 0.9, 0.5} or {0.55, 0.58, 0.62},
            online > 0 and "UP" or "—", alpha)
        widgets.info_row(20, 130, W - 40, "Tailnet",
            state.tailnet ~= "" and state.tailnet or "Not authenticated", nc, alpha)
        local auth = state.auth_url
        if auth == "" then auth = state.error ~= "" and state.error or "No pending authorization" end
        if #auth > 64 then auth = auth:sub(1, 61) .. "..." end
        widgets.info_row(20, 150, W - 40, "Auth", auth, {0.35, 0.8, 1.0}, alpha)
    end,
    items = {},
}

local scene = dashboard.new(config)
local base_enter = scene.enter
function scene.enter(args)
    base_enter(args)
    scene._items = items_for()
end
scene._get_items = function()
    return items_for()
end

return scene
