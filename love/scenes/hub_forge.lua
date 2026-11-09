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
          desc = "Install or repair the desktop chroot",
          action = function(scene)
              scene.set_status("Installing...")
              bridge.call("xfce_install", {}, function(resp)
                  if resp.ok then
                      scene.set_status(resp.note or "installed")
                      refresh(scene, true)
                  else
                      scene.set_status("Install: " .. (resp.error or "failed"))
                  end
              end)
              return "Installing..."
          end },
        { icon = "play", label = "Launch XFCE Desktop",
          desc = "Open the full desktop now",
          action = function(scene)
              scene.set_status("Launching XFCE...")
              bridge.call("xfce_launch", {}, function(resp)
                  if resp.ok then
                      scene.set_status("XFCE: " .. (resp.note or "running"))
                  else
                      scene.set_status("Launch: " .. (resp.error or "failed"))
                  end
              end)
              return "Launching..."
          end },
        { icon = "refresh", label = "Update system",
          desc = "apt update + upgrade in chroot",
          action = function(scene)
              scene.set_status("Updating...")
              bridge.call("apt_update", {}, function(resp)
                  if resp.ok then
                      scene.set_status("System updated")
                  else
                      scene.set_status("Update: " .. (resp.error or resp.reason or "failed"))
                  end
              end)
              return "Updating..."
          end },
        { icon = "trash", label = "Clean apt cache",
          desc = "Run safe APT cache cleanup inside the XFCE image",
          action = function() sm.push("hub_apt", {tab = "SYSTEM"}) end },
        { icon = "terminal", label = "Shell terminal",
          desc = "Open a terminal with on-screen keyboard",
          action = function() sm.push("hub_shell", {}) end },
        { icon = "pkg", label = "Install htop",

          desc = "Interactive process viewer (apt in XFCE chroot)",

          action = function(scene)

              local cmd = "sh bin/vd_apt_install.sh htop"

              bridge.call("job_start", { cmd = cmd, name = "apt: htop", hub = "forge" },

                function(resp)

                  if resp.ok then

                    scene.set_status("Installing htop (see SELECT overlay)")

                  else

                    scene.set_status("Install: " .. (resp.error or "failed"))

                  end

                end)

              return "Installing htop..."

          end },

        { icon = "pkg", label = "Install ncdu",

          desc = "Disk usage analyser (apt in XFCE chroot)",

          action = function(scene)

              local cmd = "sh bin/vd_apt_install.sh ncdu"

              bridge.call("job_start", { cmd = cmd, name = "apt: ncdu", hub = "forge" },

                function(resp)

                  if resp.ok then

                    scene.set_status("Installing ncdu (see SELECT overlay)")

                  else

                    scene.set_status("Install: " .. (resp.error or "failed"))

                  end

                end)

              return "Installing ncdu..."

          end },

        { icon = "pkg", label = "Install ffmpeg",

          desc = "Audio/video codec toolkit (apt in XFCE chroot)",

          action = function(scene)

              local cmd = "sh bin/vd_apt_install.sh ffmpeg"

              bridge.call("job_start", { cmd = cmd, name = "apt: ffmpeg", hub = "forge" },

                function(resp)

                  if resp.ok then

                    scene.set_status("Installing ffmpeg (see SELECT overlay)")

                  else

                    scene.set_status("Install: " .. (resp.error or "failed"))

                  end

                end)

              return "Installing ffmpeg..."

          end },

        { icon = "pkg", label = "Install curl",

          desc = "HTTP client (apt in XFCE chroot)",

          action = function(scene)

              local cmd = "sh bin/vd_apt_install.sh curl"

              bridge.call("job_start", { cmd = cmd, name = "apt: curl", hub = "forge" },

                function(resp)

                  if resp.ok then

                    scene.set_status("Installing curl (see SELECT overlay)")

                  else

                    scene.set_status("Install: " .. (resp.error or "failed"))

                  end

                end)

              return "Installing curl..."

          end },

        { icon = "pkg", label = "Void Installer", desc = "Install/reinstall software (L1: tabs)", action = function(s) s.set_status("Opening installer..."); bridge.call("comp_install", {}, function(r) s.set_status(r.ok and (r.note or "ready") or ("err: " .. (r.error or "?"))) end); return "Installer..." end },
        { icon = "start", label = "Startup apps", desc = "Programs that boot with the desktop", action = function(s) s.set_status("Opening startup..."); bridge.call("comp_autostart", {}, function(r) s.set_status(r.ok and (r.note or "ready") or ("err: " .. (r.error or "?"))) end); return "Startup..." end },
        { icon = "refresh", label = "Update Environments", desc = "apt update + upgrade", action = function(s) s.set_status("Updating..."); bridge.call("apt_update", {}, function(r) s.set_status(r.ok and "updated" or ("err: " .. (r.error or r.reason or "?"))) end); return "Updating..." end },
        { icon = "download", label = "Void-Desk Update", desc = "GitHub releases", action = function(s) s.set_status("Checking GitHub..."); bridge.call("gh_fetch_releases", {}, function(r) s.set_status(r.ok and ("latest: " .. (r.tag or "?")) or ("err: " .. (r.error or "?"))) end); return "Checking..." end },
        { icon = "terminal", label = "CLI Shooter", desc = "Terminal tools", action = function(s) s.set_status("Opening CLI..."); bridge.call("clihub_list", {}, function(r) s.set_status(r.ok and (r.note or "ready") or ("err: " .. (r.error or "?"))) end); return "CLI..." end },
        { icon = "back", label = "Back",
          desc = "Return to Nexus",
          action = function() sm.back() end },
    },
})
