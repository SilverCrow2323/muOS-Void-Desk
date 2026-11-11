local dashboard = require("core.dashboard_screen")
local bridge = require("core.bridge")
local sm = require("core.scene_manager")
local nodes = require("core.nodes")
local widgets = require("core.widgets")

local state = {
    stations = {},
    current = nil,
    status = "Loading station catalogue...",
    error = nil,
}

local function refresh(scene, silent)
    if not silent then
        state.status = "Loading station catalogue..."
        scene.set_status(state.status)
    end
    bridge.call("radio_list", {}, function(resp)
        if resp.ok then
            state.stations = resp.stations or {}
            state.error = nil
            state.status = string.format("%d stations available", #state.stations)
        else
            state.error = resp.error or "Radio catalogue unavailable"
            state.status = state.error
        end
        scene.set_status(state.status)
    end)
    bridge.call("radio_status", {}, function(resp)
        if resp.ok then
            state.current = resp.state == "playing" and resp.station or nil
            if resp.error and resp.error ~= "" then
                state.error = resp.error
            end
        end
    end)
end

local function items_for()
    local items = {}
    for _, station in ipairs(state.stations) do
        local selected = station
        table.insert(items, {
            icon = "music",
            label = tostring(selected.name or "Radio station"),
            desc = tostring(selected.category or "internet radio"),
            action = function(scene)
                state.status = "Starting " .. tostring(selected.name) .. "..."
                scene.set_status(state.status)
                bridge.call("radio_play", {id = selected.id}, function(resp)
                    if resp.ok then
                        state.current = resp.station
                        state.status = "Playing: " .. tostring(resp.station)
                    else
                        state.error = resp.error or "Playback failed"
                        state.status = state.error
                    end
                    scene.set_status(state.status)
                end)
                return "Starting radio..."
            end,
        })
    end
    table.insert(items, {
        icon = "stop",
        label = "Stop playback",
        desc = "Stop the background audio stream",
        action = function(scene)
            bridge.call("radio_stop", {}, function(resp)
                state.current = nil
                state.status = resp.ok and "Radio stopped"
                    or ("Stop failed: " .. (resp.error or "unknown error"))
                scene.set_status(state.status)
            end)
            return "Stopping radio..."
        end,
    })
    table.insert(items, {
        icon = "refresh",
        label = "Refresh stations",
        desc = "Reload the built-in station catalogue",
        action = function(scene)
            refresh(scene, false)
            return "Refreshing..."
        end,
    })
    table.insert(items, {
        icon = "back",
        label = "Back",
        desc = "Return to Media Vault",
        action = function() sm.back() end,
    })
    return items
end

local scene = dashboard.new({
    title = "VOID RADIO",
    node_idx = 2,
    widget_height = 104,
    row_height = 44,
    status = "Internet radio",
    on_enter = function(scene)
        refresh(scene, false)
    end,
    on_update = function(scene, dt)
        scene._t = (scene._t or 0) + dt
        if scene._t > 8 then
            scene._t = 0
            bridge.call("radio_status", {}, function(resp)
                if resp.ok then
                    state.current = resp.state == "playing" and resp.station or nil
                    if resp.error and resp.error ~= "" then
                        state.error = resp.error
                    end
                end
            end)
        end
    end,
    widgets_draw = function(scene, alpha)
        local W = love.graphics.getWidth()
        local nc = nodes.color_for(2)
        local playing = state.current ~= nil
        widgets.status_card(12, 62, W - 24, 54, "music",
            "Playback", state.current or "No station playing",
            playing and {0.4, 0.9, 0.5} or nc,
            playing and "LIVE" or "IDLE", alpha)
        widgets.info_row(20, 124, W - 40, "Status", state.status, nc, alpha)
    end,
    items = {},
})

scene._get_items = items_for
return scene
