local dashboard = require("core.dashboard_screen")
local config    = require("core.config")
local theme     = require("theme.loader")
local sm        = require("core.scene_manager")
local nodes     = require("core.nodes")
local widgets   = require("core.widgets")

local function get(k, d) return config.get(k, d) end
local function set(k, v) config.set(k, v) end

local function rebuild_items(scene)
    return {
        { icon = "gear", label = "Frontend engine",
          value = get("engine", "love"):upper(),
          desc = "PY (Pygame) / LOVE — restart required",
          action = function(sc)
              local nxt = (get("engine", "love") == "py") and "love" or "py"
              set("engine", nxt)
              sc.set_status("Engine: " .. nxt:upper() .. " — restart required")
              return "Engine: " .. nxt
          end },
        { icon = "star", label = "Theme",
          value = get("theme", "cyberpunk"):upper(),
          desc = "Cyberpunk / Crimson / Stealth / Green",
          action = function(sc)
              local themes = {"cyberpunk", "crimson", "stealth", "green"}
              local cur = get("theme", "cyberpunk")
              local idx = 1
              for i, t in ipairs(themes) do if t == cur then idx = i end end
              local nxt = themes[idx % #themes + 1]
              set("theme", nxt); theme.apply(nxt)
              sc.set_status("Theme: " .. nxt)
              return "Theme: " .. nxt
          end },
        { icon = "globe", label = "Language",
          value = get("lang", "en"):upper(),
          desc = "English / Italiano",
          action = function(sc)
              local nxt = (get("lang", "en") == "en") and "it" or "en"
              set("lang", nxt)
              sc.set_status("Language: " .. nxt:upper() .. " (restart to apply)")
              return "Lang: " .. nxt
          end },
        { icon = "list", label = "Default view",
          value = get("view_mode", "list"):upper(),
          desc = "list / grid / guide — IPTV & file list default",
          action = function(sc)
              local opts = {"list", "grid", "guide"}
              local cur = get("view_mode", "list")
              local idx = 1
              for i, t in ipairs(opts) do if t == cur then idx = i end end
              local nxt = opts[idx % #opts + 1]
              set("view_mode", nxt)
              sc.set_status("View: " .. nxt)
              return "View: " .. nxt
          end },
        { icon = "music", label = "Player backend",
          value = get("player_backend", "auto"):upper(),
          desc = "auto / mpv / ffplay — media playback",
          action = function(sc)
              local opts = {"auto", "mpv", "ffplay"}
              local cur = get("player_backend", "auto")
              local idx = 1
              for i, t in ipairs(opts) do if t == cur then idx = i end end
              local nxt = opts[idx % #opts + 1]
              set("player_backend", nxt)
              sc.set_status("Player: " .. nxt)
              return "Player: " .. nxt
          end },
        { icon = "download", label = "Player cache",
          value = tostring(get("player_cache_secs", 5)) .. "s",
          desc = "Buffer for shaky streams (0-30s)",
          action = function(sc)
              local cur = get("player_cache_secs", 5)
              local nxt = (cur + 5) % 35
              set("player_cache_secs", nxt)
              sc.set_status("Cache: " .. nxt .. "s")
              return "Cache: " .. nxt .. "s"
          end },
        { icon = "clock", label = "EPG cache age",
          value = tostring(get("epg_max_age_hours", 12)) .. "h",
          desc = "Redownload EPG beyond this age",
          action = function(sc)
              local cur = get("epg_max_age_hours", 12)
              local nxt = ((cur + 6) % 60) + 1
              set("epg_max_age_hours", nxt)
              sc.set_status("EPG cache: " .. nxt .. "h")
              return "EPG: " .. nxt .. "h"
          end },
        { icon = "globe", label = "User agent",
          value = (get("user_agent", "VLC/3.0"):sub(1, 10)),
          desc = "HTTP user-agent for streams",
          action = function(sc) sc.set_status("Edit in data/desk_config.json"); return "Config file" end },
        { icon = "download", label = "Recordings dir",
          value = get("rec_dir", "/mnt/mmc"):sub(-6),
          desc = "Where PVR saves recordings",
          action = function(sc)
              local cur = get("rec_dir", "/mnt/mmc/MUOS/voidcast")
              local nxt = cur:find("mmc") and "/mnt/sdcard/MUOS/voidcast" or "/mnt/mmc/MUOS/voidcast"
              set("rec_dir", nxt)
              sc.set_status("Rec dir: " .. nxt)
              return "Rec: " .. nxt:sub(-10)
          end },
        { icon = "image", label = "Channel logos",
          value = get("show_logos", true) and "ON" or "OFF",
          desc = "Download tvg-logo from playlists",
          action = function(sc)
              local cur = get("show_logos", true)
              set("show_logos", not cur)
              sc.set_status("Logos: " .. (cur and "OFF" or "ON"))
              return "Logos: " .. (cur and "OFF" or "ON")
          end },
        { icon = "play", label = "Boot animation",
          value = get("show_bootanim", true) and "ON" or "OFF",
          desc = "Play tunnel animation when launching XFCE",
          action = function(sc)
              local cur = get("show_bootanim", true)
              set("show_bootanim", not cur)
              sc.set_status("Bootanim: " .. (cur and "OFF" or "ON"))
              return "Bootanim: " .. (cur and "OFF" or "ON")
          end },
        { icon = "video", label = "Preview boot animation",
          desc = "Show the tunnel now",
          action = function()
              sm.switch("bootanim", {
                  next = "hub_settings", name = "VOID-DESK", duration = 2.5,
              })
              return "Preview..."
          end },
        { icon = "back", label = "Back", desc = "Return to Nexus",
          action = function() sm.back() end },
    }
end

local scene = dashboard.new({
    title = "SETTINGS",
    node_idx = 7,
    widget_height = 128,
    row_height = 46,
    status = "Configuration",
    items = {},

    widgets_draw = function(sc, alpha)
        local W = love.graphics.getWidth()
        local nc = nodes.color_for(7)
        local engine = get("engine", "love")
        local ecol = (engine == "love") and {0.40,0.85,1.0} or {0.90,0.70,0.30}
        widgets.status_card(12, 62, (W-40)/2, 56, "gear",
            "Engine", engine:upper(), ecol,
            engine == "love" and "LOVE" or "PY", alpha)
        widgets.status_card(12 + (W-40)/2 + 8, 62, (W-40)/2, 56, "info",
            "Theme", get("theme","cyberpunk"), nc, "CUSTOM", alpha)
        widgets.info_row(20, 126, W-40, "Language",
                         get("lang","en"):upper(), nc, alpha)
        widgets.info_row(20, 146, W-40, "Boot animation",
                         get("show_bootanim", true) and "ON" or "OFF",
                         get("show_bootanim", true) and {0.4,0.9,0.5} or {0.55,0.58,0.62},
                         alpha)
    end,
})

scene._get_items = function() return rebuild_items(scene) end

return scene
