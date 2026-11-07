local dashboard = require("core.dashboard_screen")
local bridge    = require("core.bridge")
local sm        = require("core.scene_manager")
local nodes     = require("core.nodes")
local widgets   = require("core.widgets")
local input     = require("core.input")

local state = {
    apps = {},
    selected = 1,
    source = "—",
    scan_error = nil,
}

local function refresh(scene, silent)
    if not silent then scene.set_status("Scanning muOS apps...") end
    bridge.call("list_muos_apps", {}, function(resp)
        if resp.ok then
            state.apps = resp.apps or {}
            state.source = resp.source or "—"
            state.scan_error = nil
            scene.set_status(string.format("%d apps found", #state.apps))
        else
            state.apps = {}
            state.source = resp.source or "—"
            state.scan_error = resp.error or resp.reason or "failed"
            scene.set_status(state.scan_error)
        end
    end)
end

local function launch_app(scene, idx)
    if idx < 1 or idx > #state.apps then return "No app" end
    local app = state.apps[idx]
    bridge.call("launch_muos_app", { path = app.path, name = app.name },
        function(resp)
            if resp.ok then
                scene.set_status("Launched: " .. app.name)
            else
                scene.set_status("Launch failed: " .. (resp.error or resp.reason or "?"))
            end
        end)
    return "Launching " .. app.name
end

return dashboard.new({
    title = "MUOS APPS",
    node_idx = 1,
    widget_height = 90,
    status = "Application discovery",

    on_enter = function(scene) refresh(scene, false) end,
    on_update = function(scene, dt)
        scene._t = (scene._t or 0) + dt
        if scene._t > 10 then scene._t = 0; refresh(scene, true) end
    end,

    widgets_draw = function(scene, alpha)
        local W = love.graphics.getWidth()
        local nc = nodes.color_for(1)

        widgets.status_card(12, 62, W - 24, 48, "window",
            "Applications", string.format("%d installed", #state.apps),
            (#state.apps > 0 and {0.4, 0.9, 0.5} or {0.55, 0.58, 0.62}),
            "FOUND", alpha)

        widgets.info_row(20, 116, W - 40, "Source", state.source,
                         (state.scan_error and {1, 0.5, 0.4} or nc), alpha)
    end,

    items = (function()
        -- Dynamic: shown in menu below. Static "scan" + "back" always.
        -- Apps are rendered manually inside the menu because the list changes.
        return {
            { icon = "refresh", label = "Rescan applications",
              desc = "Search again MUOS/application folder",
              action = function(scene) refresh(scene, false); return "Rescanning..." end },
            { icon = "play", label = "Launch selected app",
              desc = "Run the first app in the list",
              action = function(scene) return launch_app(scene, 1) end },
            { icon = "back", label = "Back",
              desc = "Return to Nexus",
              action = function() sm.switch("nexus", {}) end },
        }
    end)(),
})
