local dashboard = require("core.dashboard_screen")
local config    = require("core.config")
local theme     = require("theme.loader")
local sm        = require("core.scene_manager")
local nodes     = require("core.nodes")
local widgets   = require("core.widgets")
local qwasar_profile = require("core.qwasar_profile")

local function get(k, d) return config.get(k, d) end
local function set(k, v) config.set(k, v) end

return dashboard.new({
    title = "SETTINGS",
    node_idx = 7,
    widget_height = 176,
    status = "Configuration",

    widgets_draw = function(scene, alpha)
        local W = love.graphics.getWidth()
        local nc = nodes.color_for(7)

        local engine = get("engine", "love")
        local theme_n = get("theme", "cyberpunk")
        local lang = get("lang", "en")
        local show_ba = get("show_bootanim", true) and "ON" or "OFF"
        local profile_status = qwasar_profile.status()
        local profile_label = profile_status.loaded
            and (profile_status.name or profile_status.id)
            or "Built-in defaults"

        -- highlight engine in the box
        local ecol = (engine == "love") and {0.40, 0.85, 1.0} or {0.90, 0.70, 0.30}
        widgets.status_card(12, 62, (W - 40) / 2, 52, "gear",
            "Engine", engine:upper(), ecol,
            engine == "love" and "LÖVE" or "PY", alpha)
        widgets.status_card(12 + (W - 40)/2 + 8, 62, (W - 40) / 2, 52, "info",
            "Theme", theme_n, nc, "CUSTOM", alpha)

        widgets.info_row(20, 124, W - 40, "Language", lang:upper(), nc, alpha)
        widgets.info_row(20, 144, W - 40, "Boot animation", show_ba,
                         (get("show_bootanim", true) and {0.4, 0.9, 0.5} or {0.55, 0.58, 0.62}),
                         alpha)
        widgets.info_row(20, 164, W - 40, "QWASAR profile",
                         profile_label, nc, alpha)
    end,

    items = {
        { badge = "E", label = "Frontend engine",
          desc = "Toggle PY (Pygame, stable) <-> LOVE (this UI)",
          action = function(scene)
              local cur = get("engine", "love")
              local nxt = (cur == "py") and "love" or "py"
              set("engine", nxt)
              scene.set_status("Engine: " .. nxt:upper() .. " — restart to apply")
              return "Engine: " .. nxt
          end },
        { badge = "T", label = "Theme",
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
        { badge = "L", label = "Language",
          desc = "English / Italiano",
          action = function(scene)
              local cur = get("lang", "en")
              local nxt = (cur == "en") and "it" or "en"
              set("lang", nxt)
              scene.set_status("Language: " .. nxt:upper() .. " (restart to apply)")
              return "Language: " .. nxt
          end },
        { badge = "B", label = "Boot animation",
          desc = "Toggle on/off when launching XFCE",
          action = function(scene)
              local cur = get("show_bootanim", true)
              set("show_bootanim", not cur)
              scene.set_status("Boot animation: " .. (cur and "OFF" or "ON"))
              return "Bootanim: " .. (cur and "OFF" or "ON")
          end },
        { badge = "P", label = "Preview boot animation",
          desc = "See the tunnel effect now",
          action = function(scene)
              sm.switch("bootanim", {
                  next = "hub_settings", name = "VOID-DESK", duration = 2.5,
              })
              return "Preview..."
          end },
        { badge = "X", label = "Display FX",
          desc = "CRT scanlines / vignette / glitch / aberration",
          action = function(scene)
              sm.switch("hub_display_fx", {})
          end },
        { badge = "<", label = "Back",
          desc = "Return to Nexus",
          action = function() sm.switch("nexus", {}) end },
    },
})
