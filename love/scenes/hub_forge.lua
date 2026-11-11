local dashboard = require("core.dashboard_screen")
local bridge    = require("core.bridge")
local sm        = require("core.scene_manager")
local config    = require("core.config")
local nodes     = require("core.nodes")
local widgets   = require("core.widgets")

local state = {
    disk_free_gb = 0,
    ram_pct = 0,
    uptime_s = 0,
    kernel = "—",
}

local function refresh(scene, silent)
    if not silent then scene.set_status("Reading system state...") end
    bridge.call("system_status", {}, function(resp)
        if resp.ok and resp.system then
            local d = resp.system.disk or {}
            state.disk_free_gb = d[1] and d[1].free_gb or 0
            state.ram_pct = (resp.system.ram or {}).pct or 0
            state.uptime_s = resp.system.uptime_s or 0
            state.kernel = resp.system.kernel or "—"
            if not silent then scene.set_status("Ready") end
        else
            scene.set_status("State: " .. (resp.error or "failed"))
        end
    end)
end

local function fmt_uptime(s)
    s = s or 0
    local d = math.floor(s / 86400)
    local h = math.floor((s % 86400) / 3600)
    local m = math.floor((s % 3600) / 60)
    if d > 0 then return string.format("%dd%dh", d, h) end
    if h > 0 then return string.format("%dh%dm", h, m) end
    return string.format("%dm", m)
end

return dashboard.new({
    title = "THE FORGE",
    node_idx = 3,
    widget_height = 140,
    status = "Installer & updater",

    on_enter = function(scene) refresh(scene, false) end,
    on_update = function(scene, dt)
        scene._t = (scene._t or 0) + dt
        if scene._t > 5 then scene._t = 0; refresh(scene, true) end
    end,

    background_draw = require("effects.forge_bg").draw,
    widgets_draw = function(scene, alpha)
        local W = love.graphics.getWidth()
        local nc = nodes.color_for(3)

        widgets.status_card(12, 62, (W - 40)/2, 60, "pkg",
            "Apt cache", "run Update or Clean",
            nc, "READY", alpha)
        widgets.status_card(12 + (W-40)/2 + 8, 62, (W - 40)/2, 60, "disk",
            "Disk", string.format("%.1f GB free", state.disk_free_gb),
            (state.disk_free_gb > 1 and {0.4, 0.9, 0.5} or {1, 0.5, 0.4}),
            state.disk_free_gb > 1 and "OK" or "LOW", alpha)

        widgets.info_row(20, 132, W - 40, "RAM used",
                         string.format("%d%%", state.ram_pct or 0), nc, alpha)
        widgets.info_row(20, 152, W - 40, "Uptime",
                         fmt_uptime(state.uptime_s), {0.75, 0.80, 0.85}, alpha)
    end,

    items = {
        { icon = "pkg", label = "APT Package Manager",
          desc = "Search, install, remove and maintain XFCE packages",
          action = function(scene)
              if sm.push("hub_apt", {}) then
                  return "Opening APT manager..."
              end
              scene.set_status("APT manager: " .. tostring(sm.last_error() or "cannot open"))
              return "APT manager unavailable"
          end },
        { icon = "pkg", label = "Install XFCE Desktop",
          desc = "Install or repair the optional Debian/Ubuntu desktop image",
          action = function(scene)
              scene.set_status("Installing XFCE desktop...")
              bridge.call("xfce_install", {}, function(resp)
                  if resp.ok then
                      scene.set_status(resp.note or "XFCE installation started")
                      refresh(scene, true)
                  else
                      scene.set_status("Install: " .. (resp.error or "failed"))
                  end
              end)
              return "Installing XFCE..."
          end },
        { icon = "play", label = "Launch XFCE Desktop",
          desc = "Hand off the handheld display to the installed desktop",
          action = function(scene)
              scene.set_status("Handing off to XFCE...")
              bridge.call("session_launch", {id = "xfce"}, function(resp)
                  if resp.ok then
                      scene.set_status(resp.note or "Starting XFCE...")
                      if resp.handoff then love.event.quit() end
                  else
                      scene.set_status("Launch: " .. (resp.error or "failed"))
                  end
              end)
              return "Launching XFCE..."
          end },
        { icon = "refresh", label = "Package maintenance",
          desc = "Update, upgrade or clean the XFCE image package cache",
          action = function()
              if sm.push("hub_apt", {tab = "SYSTEM"}) then
                  return "Opening package maintenance..."
              end
              return "APT maintenance unavailable"
          end },
        { icon = "terminal", label = "Shell terminal",
          desc = "Open the non-blocking local service terminal",
          action = function()
              if sm.push("hub_shell", {}) then return "Opening shell..." end
              return "Shell unavailable"
          end },
        { icon = "pkg", label = "Install htop",
          desc = "Interactive process viewer in the XFCE image",
          action = function(scene)
              scene.set_status("Installing htop...")
              bridge.call("job_start", {
                  apt_action = "install", packages = {"htop"},
                  name = "apt: htop", hub = "forge",
              }, function(resp)
                  scene.set_status(resp.ok and
                      ("Job #" .. tostring(resp.job.id) .. " started")
                      or ("Install: " .. (resp.error or "failed")))
              end)
              return "Installing htop..."
          end },
        { icon = "pkg", label = "Install ncdu",
          desc = "Disk usage analyser in the XFCE image",
          action = function(scene)
              scene.set_status("Installing ncdu...")
              bridge.call("job_start", {
                  apt_action = "install", packages = {"ncdu"},
                  name = "apt: ncdu", hub = "forge",
              }, function(resp)
                  scene.set_status(resp.ok and
                      ("Job #" .. tostring(resp.job.id) .. " started")
                      or ("Install: " .. (resp.error or "failed")))
              end)
              return "Installing ncdu..."
          end },
        { icon = "pkg", label = "Install ffmpeg",
          desc = "Audio/video toolkit in the XFCE image",
          action = function(scene)
              scene.set_status("Installing ffmpeg...")
              bridge.call("job_start", {
                  apt_action = "install", packages = {"ffmpeg"},
                  name = "apt: ffmpeg", hub = "forge",
              }, function(resp)
                  scene.set_status(resp.ok and
                      ("Job #" .. tostring(resp.job.id) .. " started")
                      or ("Install: " .. (resp.error or "failed")))
              end)
              return "Installing ffmpeg..."
          end },
        { icon = "pkg", label = "Install curl",
          desc = "HTTP client in the XFCE image",
          action = function(scene)
              scene.set_status("Installing curl...")
              bridge.call("job_start", {
                  apt_action = "install", packages = {"curl"},
                  name = "apt: curl", hub = "forge",
              }, function(resp)
                  scene.set_status(resp.ok and
                      ("Job #" .. tostring(resp.job.id) .. " started")
                      or ("Install: " .. (resp.error or "failed")))
              end)
              return "Installing curl..."
          end },
        { icon = "download", label = "Check Void Desk releases",
          desc = "Read the latest public GitHub release metadata",
          action = function(scene)
              scene.set_status("Checking GitHub releases...")
              bridge.call("gh_fetch_releases", {}, function(resp)
                  if resp.ok then
                      scene.set_status(resp.tag and ("Latest: " .. resp.tag)
                          or "No published releases yet")
                  else
                      scene.set_status("Release check: " .. (resp.error or "failed"))
                  end
              end)
              return "Checking releases..."
          end },
        { icon = "terminal", label = "Shell & CLI tools",
          desc = "Open the shell for supported command-line utilities",
          action = function()
              if sm.push("hub_shell", {}) then return "Opening shell..." end
              return "Shell unavailable"
          end },
        { icon = "back", label = "Back",
          desc = "Return to Nexus",
          action = function() sm.back() end },

    },
})
