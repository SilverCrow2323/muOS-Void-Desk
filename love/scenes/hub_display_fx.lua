-- ============================================================================
--  VOIDDESK // hub_display_fx
--  Settings submenu for the CRT post-process pass (core.crt_shader).
--  Real, individually tunable options — not just an on/off switch —
--  persisted to data/desk_config.json under "crt_fx".
-- ============================================================================
local dashboard = require("core.dashboard_screen")
local sm        = require("core.scene_manager")
local nodes     = require("core.nodes")
local widgets   = require("core.widgets")
local crt       = require("core.crt_shader")

local function fx() return crt.get_fx() end

local ABERR_LABEL = { [0] = "OFF", [1] = "LOW", [2] = "MED" }

return dashboard.new({
    title = "DISPLAY FX",
    node_idx = 7,
    widget_height = 120,
    status = "CRT post-process",

    widgets_draw = function(scene, alpha)
        local W = love.graphics.getWidth()
        local nc = nodes.color_for(7)
        local f = fx()
        local lvl = tonumber(f.aberration) or 0

        widgets.info_row(20, 64, W - 40, "Scanlines",
            (f.scanlines ~= false) and "ON" or "OFF",
            (f.scanlines ~= false) and {0.4, 0.9, 0.5} or {0.55, 0.58, 0.62}, alpha)
        widgets.info_row(20, 84, W - 40, "Vignette",
            (f.vignette ~= false) and "ON" or "OFF",
            (f.vignette ~= false) and {0.4, 0.9, 0.5} or {0.55, 0.58, 0.62}, alpha)
        widgets.info_row(20, 104, W - 40, "Signal glitch",
            (f.glitch == true) and "ON" or "OFF",
            (f.glitch == true) and {0.9, 0.5, 0.9} or {0.55, 0.58, 0.62}, alpha)
        widgets.info_row(20, 124, W - 40, "Chromatic aberration",
            ABERR_LABEL[lvl] or "OFF", nc, alpha)
    end,

    items = {
        { badge = "S", label = "Scanlines", desc = "Horizontal CRT line darkening",
          action = function(scene)
              local f = fx()
              f.scanlines = not (f.scanlines ~= false)
              crt.set_fx(f)
              return "Scanlines: " .. (f.scanlines and "ON" or "OFF")
          end },
        { badge = "V", label = "Vignette", desc = "Soft corner darkening",
          action = function(scene)
              local f = fx()
              f.vignette = not (f.vignette ~= false)
              crt.set_fx(f)
              return "Vignette: " .. (f.vignette and "ON" or "OFF")
          end },
        { badge = "G", label = "Signal glitch", desc = "Occasional scanline tear",
          action = function(scene)
              local f = fx()
              f.glitch = not (f.glitch == true)
              crt.set_fx(f)
              return "Glitch: " .. (f.glitch and "ON" or "OFF")
          end },
        { badge = "A", label = "Chromatic aberration",
          desc = "Off / Low / Medium — OFF recommended on small screens",
          action = function(scene)
              local f = fx()
              local lvl = tonumber(f.aberration) or 0
              lvl = (lvl + 1) % 3
              f.aberration = lvl
              crt.set_fx(f)
              return "Aberration: " .. ABERR_LABEL[lvl]
          end },
        { badge = "0", label = "Disable effect entirely",
          desc = "Turn off the whole CRT pass (toggle anytime with it)",
          action = function(scene)
              crt.set_enabled(not crt.is_enabled())
              return "CRT pass: " .. (crt.is_enabled() and "ON" or "OFF")
          end },
        { badge = "<", label = "Back", desc = "Return to Settings",
          action = function() sm.switch("hub_settings", {}) end },
    },
})
