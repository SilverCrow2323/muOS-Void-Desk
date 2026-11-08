local dashboard = require("core.dashboard_screen")
local bridge = require("core.bridge")
local sm = require("core.scene_manager")
local nodes = require("core.nodes")
local widgets = require("core.widgets")

local state = {
    available = false,
    state = "Checking",
    url = "—",
    id = "—",
    connected = 0,
    folders = {},
    devices = {},
    mode = "folders",
    message = "",
}

local function refresh(scene, silent)
    if not silent then scene.set_status("Checking muOS Syncthing service...") end
    bridge.call("syncthing_status", {}, function(resp)
        if not resp.ok then
            state.available = false
            state.message = resp.error or "Syncthing query failed"
            scene.set_status("Syncthing: " .. state.message)
            return
        end
        state.available = resp.available == true
        state.state = resp.state or (state.available and "Running" or "Not configured")
        state.url = resp.url or "—"
        state.id = resp.id or "—"
        state.connected = resp.connected or 0
        state.folders = resp.folders or {}
        state.devices = resp.devices or {}
        state.message = resp.message or ""
        local count = state.mode == "devices" and #state.devices or #state.folders
        scene.set_status(state.available and
            (tostring(state.connected) .. " connected · " .. tostring(count) ..
             (state.mode == "devices" and " devices" or " folders")) or
            (state.message ~= "" and state.message or "Syncthing unavailable"))
        scene._items = items_for()
    end)
end

local function run_action(scene, action, folder, device, label)
    scene.set_status(label or "Syncthing...")
    bridge.call("syncthing_action", {
        action = action,
        folder = folder or "",
        device = device or "",
    }, function(resp)
        if resp.ok then
            scene.set_status("Syncthing action completed")
            refresh(scene, true)
        else
            scene.set_status(resp.error or "Syncthing action failed")
        end
    end)
    return label or "Working..."
end

function items_for()
    local items = {
        {
            icon = "refresh", label = "Refresh Syncthing",
            desc = "Read folders, devices and sync status from muOS",
            action = function(scene) refresh(scene, false); return "Refreshing..." end,
        },
        {
            icon = "users",
            label = state.mode == "folders" and "Show devices" or "Show folders",
            value = state.mode == "folders" and tostring(#state.folders) or tostring(#state.devices),
            desc = "Switch between shared folders and remote devices",
            action = function(scene)
                state.mode = state.mode == "folders" and "devices" or "folders"
                scene._items = items_for()
                scene.set_status(state.mode == "devices" and "Remote devices" or "Shared folders")
                return state.mode == "devices" and "Devices" or "Folders"
            end,
        },
    }

    if state.mode == "folders" then
        for _, folder in ipairs(state.folders) do
            local label = tostring(folder.label or folder.id or "Folder")
            local folder_id = tostring(folder.id or "")
            local paused = folder.paused == true
            local pct = tonumber(folder.pct) or -1
            table.insert(items, {
                icon = paused and "play" or "pause",
                label = (paused and "Resume: " or "Pause: ") .. label,
                value = pct >= 0 and (tostring(pct) .. "%") or (paused and "PAUSED" or "SYNC"),
                desc = tostring(folder.path or folder_id),
                action = function(scene)
                    return run_action(scene, "toggle_folder", folder_id, "",
                        paused and "Resuming folder..." or "Pausing folder...")
                end,
            })
            table.insert(items, {
                icon = "scan", label = "Rescan: " .. label,
                desc = "Request an immediate local folder scan",
                action = function(scene)
                    return run_action(scene, "scan", folder_id, "", "Rescanning folder...")
                end,
            })
            table.insert(items, {
                icon = "refresh-cw", label = "Override: " .. label,
                desc = "Publish local changes to connected devices",
                action = function(scene)
                    return run_action(scene, "override", folder_id, "", "Overriding folder...")
                end,
            })
        end
    else
        for _, device in ipairs(state.devices) do
            local name = tostring(device.name or device.id or "Device")
            local device_id = tostring(device.id or "")
            local paused = device.paused == true
            table.insert(items, {
                icon = paused and "play" or "pause",
                label = (paused and "Resume: " or "Pause: ") .. name,
                value = paused and "PAUSED" or (device.connected and "ONLINE" or "OFFLINE"),
                desc = tostring(device.address or device_id),
                action = function(scene)
                    return run_action(scene, "toggle_device", "", device_id,
                        paused and "Resuming device..." or "Pausing device...")
                end,
            })
        end
    end

    table.insert(items, {
        icon = "back", label = "Back",
        desc = "Return to Uplink",
        action = function() sm.back() end,
    })
    return items
end

local config = {
    title = "SYNCTHING",
    node_idx = 5,
    widget_height = 132,
    row_height = 46,
    status = "Native muOS Web Service manager",
    on_enter = function(scene) refresh(scene, false) end,
    on_update = function(scene, dt)
        scene._t = (scene._t or 0) + dt
        if scene._t > 8 then
            scene._t = 0
            refresh(scene, true)
        end
    end,
    widgets_draw = function(scene, alpha)
        local W = love.graphics.getWidth()
        local nc = nodes.color_for(5)
        local total = state.mode == "devices" and #state.devices or #state.folders
        local label = state.mode == "devices" and "Devices" or "Folders"
        widgets.status_card(12, 62, (W - 40) / 2, 58, "refresh-cw",
            "Syncthing", state.state, state.available and {0.4, 0.9, 0.5} or {0.65, 0.55, 0.4},
            state.available and "READY" or "OFFLINE", alpha)
        widgets.status_card(20 + (W - 40) / 2, 62, (W - 40) / 2, 58, "users",
            label, tostring(total) .. " configured",
            nc, tostring(state.connected) .. " online", alpha)
        widgets.info_row(20, 130, W - 40, "Local API",
            state.url, {0.35, 0.8, 1.0}, alpha)
        widgets.info_row(20, 150, W - 40, "Device ID",
            state.id, nc, alpha)
        if not state.available then
            local message = state.message ~= "" and state.message or
                "Enable Syncthing in muOS Web Services"
            if #message > 70 then message = message:sub(1, 67) .. "..." end
            widgets.info_row(20, 170, W - 40, "Setup", message,
                {0.9, 0.7, 0.35}, alpha)
        end
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
