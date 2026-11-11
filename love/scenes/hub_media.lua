local dashboard = require("core.dashboard_screen")
local bridge    = require("core.bridge")
local sm        = require("core.scene_manager")
local nodes     = require("core.nodes")
local widgets   = require("core.widgets")
local ext       = require("core.external")

local state = { volume = 0, library_count = 0, recordings = 0 }

local function refresh(scene, silent)
    bridge.call("media_status", {}, function(resp)
        if resp.ok and resp.media then
            state.volume = resp.media.volume or 0
            state.library_count = resp.media.library_count or 0
            state.recordings = resp.media.recordings or 0
            if not silent then scene.set_status("Ready") end
        end
    end)
end

return dashboard.new({
    title = "MEDIA VAULT",
    node_idx = 2,
    widget_height = 128,
    row_height = 50,
    status = "Media control center",

    on_enter = function(scene) refresh(scene, false) end,
    on_update = function(scene, dt)
        scene._t = (scene._t or 0) + dt
        if scene._t > 4 then scene._t = 0; refresh(scene, true) end
    end,

    widgets_draw = function(scene, alpha)
        local W = love.graphics.getWidth()
        local nc = nodes.color_for(2)
        widgets.stat_bar(12, 72, W - 24, 20, "Volume",
                         string.format("%d%%", state.volume), state.volume, nc, alpha)
        widgets.info_row(20, 110, W-40, "Library",
                         string.format("%d files", state.library_count), nc, alpha)
        widgets.info_row(20, 130, W-40, "Recordings",
                         string.format("%d files", state.recordings),
                         {0.4,0.85,0.5}, alpha)
    end,

    items = {
        { icon = "music", label = "Void Radio", desc = "Curated stations, favourites and recent streams",
          action = function() sm.push("hub_radio", {}) end },
        { icon = "video", label = "VoidCast IPTV", value = "LIVE",
          desc = "TV streams and EPG guide (LÖVE prototype)",
          action = function() sm.push("hub_iptv", {}) end },
        { icon = "folder", label = "Media Library", desc = "Browse local audio/video on SD1, SD2 and Void Desk Data",
          action = function() sm.push("hub_media_library", {}) end },
        { icon = "music", label = "BGM Normalizer", value = "PY",
          desc = "LUFS-normalize music to OGG",
          action = function(scene)
              scene.set_status("Launching BGM Normalizer...")
              ext.launch("bgm_normalizer", function(resp)
                  if resp.ok then scene.set_status("BGM Normalizer launched")
                  else scene.set_status("Failed: " .. (resp.error or "?")) end
              end)
              return "Launching..."
          end },
        { icon = "back", label = "Back", desc = "Return to Nexus",
          action = function() sm.back() end },
    },
})
