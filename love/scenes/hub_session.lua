local dashboard = require("core.dashboard_screen")
local bridge    = require("core.bridge")
local sm        = require("core.scene_manager")
local config    = require("core.config")
local nodes     = require("core.nodes")
local widgets   = require("core.widgets")

local state = {
    sessions = {},
    disk_free_gb = 0,
    ram_pct = 0,
}

local function refresh(scene, silent)
    if not silent then scene.set_status("Checking sessions...") end
    bridge.call("session_list", {}, function(resp)
        if resp.ok then state.sessions = resp.sessions or {} end
    end)
    bridge.call("system_status", {}, function(resp)
        if resp.ok and resp.system then
            state.disk_free_gb = (resp.system.disk or {})[1] and resp.system.disk[1].free_gb or 0
            state.ram_pct = (resp.system.ram or {}).pct or 0
            if not silent then scene.set_status("Desktop ready") end
        end
    end)
end

local function installed(id)
    for _, s in ipairs(state.sessions) do
        if s.id == id then return s.installed end
    end
    return false
end

local function play_bootanim_and_launch(scene, sess_id, sess_name)
    local show = config.get("show_bootanim", true)
    local function launch()
        bridge.call("session_launch", { id = sess_id }, function(resp)
            if resp.ok then
                scene.set_status(sess_name .. ": " .. (resp.note or "running"))
            else
                scene.set_status(sess_name .. ": " .. (resp.error or "failed"))
            end
        end)
    end
    if show then
        sm.switch("bootanim", {
            next = "hub_session", name = sess_name, duration = 2.5,
            on_complete = launch,
        })
    else
        launch()
    end
    return "Launching " .. sess_name .. "..."
end

return dashboard.new({
    title = "START SESSION",
    node_idx = 0,
    widget_height = 128,
    status = "Desktop environments",

    on_enter = function(scene) refresh(scene, false) end,
    on_update = function(scene, dt)
        scene._t = (scene._t or 0) + dt
        if scene._t > 6 then scene._t = 0; refresh(scene, true) end
    end,

    widgets_draw = function(scene, alpha)
        local W = love.graphics.getWidth()
        local nc = nodes.color_for(0)
        local cy, ch = 62, 60
        local cw = (W - 32) / 3

        local xfce_col = installed("xfce") and {0.40, 0.90, 0.50} or {0.55, 0.58, 0.62}
        widgets.status_card(12, cy, cw - 4, ch, "start",
            "XFCE", installed("xfce") and "installed" or "not installed",
            xfce_col, installed("xfce") and "READY" or "MISS", alpha)

        widgets.status_card(12 + cw, cy, cw - 4, ch, "window",
            "IceWM", "coming soon",
            {0.55, 0.58, 0.62}, "SOON", alpha)

        widgets.status_card(12 + 2*cw, cy, cw - 4, ch, "desktop",
            "LXDE", "coming soon",
            {0.55, 0.58, 0.62}, "SOON", alpha)

        widgets.info_row(20, 132, W - 40, "Disk free",
                         string.format("%.1f GB", state.disk_free_gb or 0),
                         (state.disk_free_gb > 1 and {0.4, 0.9, 0.5} or {1, 0.5, 0.4}),
                         alpha)
        widgets.info_row(20, 152, W - 40, "RAM used",
                         string.format("%d%%", state.ram_pct or 0), nc, alpha)
    end,

    items = {
        { icon = "start", label = "Launch XFCE Desktop",
          desc = "Full desktop environment (with boot animation)",
          action = function(scene)
              if not installed("xfce") then
                  scene.set_status("XFCE not installed — use Install below")
                  return "XFCE not installed"
              end
              return play_bootanim_and_launch(scene, "xfce", "XFCE")
          end },
        { icon = "plus", label = "Install XFCE Desktop",
          desc = "Auto-install on PC via pkexec (sudo prompt)",
          action = function(scene)
              scene.set_status("Installing XFCE (may prompt sudo)...")
              bridge.call("xfce_install", {}, function(resp)
                  if resp.ok then
                      scene.set_status(resp.note or "XFCE installed")
                      refresh(scene, true)
                  else
                      scene.set_status("Install: " .. (resp.error or "failed"))
                  end
              end)
              return "Installing XFCE..."
          end },
        { icon = "window", label = "IceWM session",
          desc = "Light window manager (~10MB RAM)",
          action = function(scene) scene.set_status("IceWM: coming soon"); return "IceWM: coming soon" end },
        { icon = "desktop", label = "LXDE session",
          desc = "Lightweight full desktop",
          action = function(scene) scene.set_status("LXDE: coming soon"); return "LXDE: coming soon" end },
        { icon = "refresh", label = "Repair desktop image",
          desc = "Verify and repair the chroot",
          action = function(scene) scene.set_status("Repair: coming soon"); return "Repair: coming soon" end },
        { icon = "back", label = "Back",
          desc = "Return to Nexus",
          action = function() sm.back() end },
    },
})
