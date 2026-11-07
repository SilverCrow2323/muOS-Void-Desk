local dashboard = require("core.dashboard_screen")
local bridge    = require("core.bridge")
local sm        = require("core.scene_manager")
local nodes     = require("core.nodes")
local widgets   = require("core.widgets")

local state = { os="—", machine="—", hostname="—", ip="—", disk_free_gb=0 }

local function refresh(scene)
    bridge.call("system_info", {}, function(resp)
        if resp.ok and resp.info then
            state.os = resp.info.os or "—"
            state.machine = resp.info.machine or "—"
            state.hostname = resp.info.hostname or "—"
            state.ip = resp.info.ip or "—"
            state.disk_free_gb = resp.info.disk_free_gb or 0
            scene.set_status("Ready")
        end
    end)
end

local function rebuild_items(scene)
    return {
        { icon = "info", label = "About project",
          desc = "VoidDesk v10.5.1 — credits, stack, ecosystem",
          action = function(sc)
              sc.set_status("VoidDesk v10.5.1 · LÖVE 11.5 · Pygame 2.6 · SPDW Factory")
              return "About"
          end },
        { icon = "book", label = "Technical manual",
          desc = "Chapters: setup, chroot, bootanim, tools",
          action = function(sc) sc.set_status("Manual: docs in README.md"); return "Manual" end },
        { icon = "gamepad", label = "Controls guide",
          desc = "D-pad, A, B, L1/R1, SELECT, TAB",
          action = function(sc)
              sc.set_status("D-pad nav · A open · B back · SELECT jobs · TAB overlay")
              return "Controls"
          end },
        { icon = "code", label = "Manifesto",
          desc = "A signal from the VOID",
          action = function(sc)
              sc.set_status("The void does not stare back. It compiles.")
              return "Manifesto"
          end },
        { icon = "refresh", label = "Check updates",
          desc = "VoidDesk releases from GitHub",
          action = function(sc)
              bridge.call("gh_fetch_releases", {}, function(resp)
                  if resp.ok then
                      sc.set_status("Latest: " .. (resp.tag or "?"))
                  else
                      sc.set_status("Update: " .. (resp.error or "?"))
                  end
              end)
              return "Checking..."
          end },
        { icon = "globe", label = "Platform check",
          desc = "Refresh OS/machine/IP info",
          action = function(sc) refresh(sc); return "Refreshing..." end },
        { icon = "warn", label = "System log",
          desc = "Last lines of voiddesk.log",
          action = function(sc) sc.set_status("Logs: data/logs/"); return "Logs" end },
        { icon = "star", label = "Third-party credits",
          desc = "Debian/Ubuntu, Pygame, LÖVE, muOS, iptv-org, open-meteo",
          action = function(sc)
              sc.set_status("Credits: see README — full attribution available")
              return "Credits"
          end },
        { icon = "back", label = "Back", desc = "Return to Nexus",
          action = function() sm.back() end },
    }
end

local scene = dashboard.new({
    title = "INFO & ABOUT",
    node_idx = 8,
    widget_height = 130,
    row_height = 46,
    status = "Project archive",
    items = {},
    on_enter = function(sc) refresh(sc) end,
    widgets_draw = function(sc, alpha)
        local W = love.graphics.getWidth()
        local nc = nodes.color_for(8)
        widgets.status_card(12, 62, (W-40)/2, 56, "info",
            "VoidDesk", "v10.5.1 (NEXUS)", nc, "BUILD", alpha)
        widgets.status_card(12 + (W-40)/2 + 8, 62, (W-40)/2, 56, "globe",
            "Platform", state.machine, {0.4,0.85,0.9},
            state.os:upper(), alpha)
        widgets.info_row(20, 128, W-40, "Hostname", state.hostname, nc, alpha)
        widgets.info_row(20, 148, W-40, "IP", state.ip, {0.4,0.9,0.5}, alpha)
    end,
})

scene._get_items = function() return rebuild_items(scene) end

return scene
