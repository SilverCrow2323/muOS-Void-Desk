local dashboard = require("core.dashboard_screen")
local config    = require("core.config")
local theme     = require("theme.loader")
local sm        = require("core.scene_manager")
local nodes     = require("core.nodes")
local widgets   = require("core.widgets")

local function get(k, d) return config.get(k, d) end
local function set(k, v) config.set(k, v) end

return dashboard.new({
    title = "SETTINGS",
    node_idx = 7,
    widget_height = 128,
    row_height = 38,
    status = "Configuration",

    widgets_draw = function(scene, alpha)
        local W = love.graphics.getWidth()
        local nc = nodes.color_for(7)
        local engine = get("engine", "love")
        local theme_n = get("theme", "cyberpunk")
        local ecol = (engine == "love") and {0.40,0.85,1.0} or {0.90,0.70,0.30}
        widgets.status_card(12, 62, (W-40)/2, 56, "gear",
            "Engine", engine:upper(), ecol,
            engine == "love" and "LOVE" or "PY", alpha)
        widgets.status_card(12 + (W-40)/2 + 8, 62, (W-40)/2, 56, "info",
            "Theme", theme_n, nc, "CUSTOM", alpha)
        widgets.info_row(20, 126, W-40, "Language", get("lang","en"):upper(), nc, alpha)
        widgets.info_row(20, 146, W-40, "Boot animation",
                         get("show_bootanim", true) and "ON" or "OFF",
                         get("show_bootanim", true) and {0.4,0.9,0.5} or {0.55,0.58,0.62},
                         alpha)
    end,

    items = {
        { icon = "gear", label = "Frontend engine",
          value = get("engine", "love"):upper(),
          desc = "PY (Pygame) / LOVE — restart to apply",
          action = function(scene)
              local cur = get("engine", "love")
              local nxt = (cur == "py") and "love" or "py"
              set("engine", nxt)
              scene.set_status("Engine: " .. nxt:upper() .. " — restart required")
              return "Engine: " .. nxt
          end },
        { icon = "star", label = "Theme",
          value = get("theme", "cyberpunk"):upper(),
          desc = "Cyberpunk / Crimson / Stealth / Green",
          action = function(scene)
              local themes = {"cyberpunk", "crimson", "stealth", "green"}
              local cur = get("theme", "cyberpunk")
              local idx = 1
              for i, t in ipairs(themes) do if t == cur then idx = i end end
              local nxt = themes[idx % #themes + 1]
              set("theme", nxt)
              theme.apply(nxt)
              scene.set_status("Theme: " .. nxt)
              return "Theme: " .. nxt
          end },
        { icon = "globe", label = "Language",
          value = get("lang", "en"):upper(),
          desc = "English / Italiano",
          action = function(scene)
              local cur = get("lang", "en")
              local nxt = (cur == "en") and "it" or "en"
              set("lang", nxt)
              scene.set_status("Language: " .. nxt:upper())
              return "Lang: " .. nxt
          end },
        { icon = "play", label = "Boot animation",
          value = get("show_bootanim", true) and "ON" or "OFF",
          desc = "Play tunnel animation when launching XFCE",
          action = function(scene)
              local cur = get("show_bootanim", true)
              set("show_bootanim", not cur)
              scene.set_status("Boot animation: " .. (cur and "OFF" or "ON"))
              return "Bootanim: " .. (cur and "OFF" or "ON")
          end },
        { icon = "video", label = "Preview boot animation",
          desc = "Show the tunnel effect now",
          action = function()
              sm.switch("bootanim", {
                  next = "hub_settings", name = "VOID-DESK", duration = 2.5,
              })
              return "Preview..."
          end },
        { icon = "back", label = "Back", desc = "Return to Nexus",
          action = function() sm.switch("nexus", {}) end },
    },
})
