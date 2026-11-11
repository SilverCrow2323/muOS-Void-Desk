local dashboard = require("core.dashboard_screen")
local bridge    = require("core.bridge")
local sm        = require("core.scene_manager")
local nodes     = require("core.nodes")
local widgets   = require("core.widgets")

local state = {
    apps = {},
    source = "—",
    scan_error = nil,
}

local function refresh(scene, silent)
    if not silent then scene.set_status("Scanning muOS applications...") end
    bridge.call("list_muos_apps", {}, function(resp)
        if resp.ok then
            state.apps = resp.apps or {}
            state.source = resp.source or "SD1 + SD2"
            state.scan_error = nil
            scene.set_status(string.format("%d applications found", #state.apps))
        else
            state.apps = {}
            state.source = resp.source or "—"
            state.scan_error = resp.error or resp.reason or "Discovery unavailable"
            scene.set_status(state.scan_error)
        end
    end)
end

local function launch_app(scene, app)
    if type(app) ~= "table" or type(app.path) ~= "string" then
        scene.set_status("Invalid application entry")
        return "Invalid application"
    end

    scene.set_status("Returning to muOS to launch " .. tostring(app.name or "application") .. "...")
    bridge.call("launch_muos_app", { path = app.path }, function(resp)
        if resp.ok then
            scene.set_status(resp.note or ("Launching " .. tostring(app.name or "application")))
            if resp.handoff then love.event.quit() end
        else
            scene.set_status("Launch failed: " .. (resp.error or resp.reason or "unknown error"))
        end
    end)
    return "Preparing application hand-off..."
end

local function items_for()
    local items = {
        {
            icon = "refresh",
            label = "Rescan applications",
            desc = "Search the supported SD1 and SD2 muOS application roots",
            action = function(scene)
                refresh(scene, false)
                return "Rescanning..."
            end,
        },
    }

    for index, app in ipairs(state.apps) do
        local selected_app = app
        table.insert(items, {
            icon = "play",
            label = tostring(selected_app.name or "Unnamed application"),
            desc = tostring(selected_app.sd or "muOS") ..
                (selected_app.help and selected_app.help ~= ""
                    and ("  ·  " .. selected_app.help) or ""),
            action = function(scene)
                return launch_app(scene, selected_app)
            end,
        })
    end

    if #state.apps == 0 then
        table.insert(items, {
            icon = "info",
            label = state.scan_error and "Discovery unavailable" or "No applications found",
            desc = state.scan_error or "Use Rescan applications to check both SD cards",
            action = function(scene)
                scene.set_status(state.scan_error or "No muOS applications found")
                return "No applications available"
            end,
        })
    end

    table.insert(items, {
        icon = "back",
        label = "Back",
        desc = "Return to Nexus",
        action = function() sm.back() end,
    })
    return items
end

local scene = dashboard.new({
    title = "MUOS APPS",
    node_idx = 1,
    widget_height = 90,
    status = "Application discovery",

    on_enter = function(scene)
        refresh(scene, false)
    end,
    on_update = function(scene, dt)
        scene._t = (scene._t or 0) + dt
        if scene._t > 10 then
            scene._t = 0
            refresh(scene, true)
        end
    end,

    widgets_draw = function(scene, alpha)
        local W = love.graphics.getWidth()
        local nc = nodes.color_for(1)
        local count = #state.apps
        widgets.status_card(12, 62, W - 24, 48, "window",
            "Applications", string.format("%d installed", count),
            count > 0 and {0.4, 0.9, 0.5} or {0.55, 0.58, 0.62},
            count > 0 and "FOUND" or "EMPTY", alpha)

        widgets.info_row(20, 116, W - 40, "Source", state.source,
            state.scan_error and {1, 0.5, 0.4} or nc, alpha)
    end,

    items = {},
})

-- dashboard_screen asks this provider on every draw/input step. New scan
-- results therefore become real selectable entries without rebuilding the
-- scene or maintaining a second, manually rendered list.
scene._get_items = items_for

return scene
