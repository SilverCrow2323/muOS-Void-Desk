local dashboard = require("core.dashboard_screen")
local bridge    = require("core.bridge")
local sm        = require("core.scene_manager")
local widgets   = require("core.widgets")
local nodes     = require("core.nodes")
local font      = require("core.font")

local state = {
    volume = 0,
    now_playing = nil,
    library_count = 0,
    recordings = 0,
}

local function refresh(scene, silent)
    bridge.call("media_status", {}, function(resp)
        if resp.ok and resp.media then
            local m = resp.media
            state.volume = m.volume or 0
            state.now_playing = m.now_playing
            state.library_count = m.library_count or 0
            state.recordings = m.recordings or 0
            if not silent then scene.set_status("Media state updated") end
        end
    end)
end

return dashboard.new({
    title = "MEDIA VAULT",
    node_idx = 2,
    widget_height = 150,
    status = "Media control center",

    on_enter = function(self) refresh(self, false) end,
    on_update = function(self, dt)
        self._t = (self._t or 0) + dt
        if self._t > 4 then self._t = 0; refresh(self, true) end
    end,

    widgets_draw = function(scene, alpha)
        local W = love.graphics.getWidth()
        local nc = nodes.color_for(2)

        -- Now playing card
        love.graphics.setColor(0.05, 0.06, 0.08, 0.92 * alpha)
        love.graphics.rectangle("fill", 12, 62, W - 24, 54, 6)
        love.graphics.setColor(nc[1], nc[2], nc[3], 0.55 * alpha)
        love.graphics.setLineWidth(1.5)
        love.graphics.rectangle("line", 12, 62, W - 24, 54, 6)

        local f_lbl = font.bold(9) or love.graphics.newFont(9)
        local f_title = font.bold(14) or love.graphics.newFont(14)
        local f_sub = font.regular(11) or love.graphics.newFont(11)

        love.graphics.setFont(f_lbl)
        love.graphics.setColor(nc[1], nc[2], nc[3], alpha)
        love.graphics.print("NOW PLAYING", 22, 68)

        local np = state.now_playing
        if np then
            love.graphics.setFont(f_title)
            love.graphics.setColor(0.95, 0.95, 0.95, alpha)
            love.graphics.print(np.title or "—", 22, 80)
            love.graphics.setFont(f_sub)
            love.graphics.setColor(0.65, 0.70, 0.78, alpha)
            love.graphics.print(np.artist or "—", 22, 99)
        else
            love.graphics.setFont(f_title)
            love.graphics.setColor(0.55, 0.60, 0.66, alpha)
            love.graphics.print("Nothing playing", 22, 84)
        end

        -- Volume bar
        widgets.stat_bar(12, 122, W - 24, 20, "Volume",
                         string.format("%d%%", state.volume),
                         state.volume, nc, alpha)

        -- Library info strip
        love.graphics.setColor(0.04, 0.05, 0.07, 0.9 * alpha)
        love.graphics.rectangle("fill", 12, 148, W - 24, 22, 4)
        love.graphics.setFont(f_sub)
        love.graphics.setColor(0.72, 0.78, 0.84, alpha)
        love.graphics.print(string.format(
            "Library: %d files   ·   Recordings: %d",
            state.library_count, state.recordings), 20, 154)
    end,

    items = {
        { badge = "R", label = "Void Radio",
          desc = "Internet radio stations",
          action = function(scene) scene.set_status("Radio: coming soon"); return "Radio: coming soon" end },
        { badge = "T", label = "VoidCast IPTV",
          desc = "TV streams and EPG guide",
          action = function(scene) scene.set_status("IPTV: coming soon"); return "IPTV: coming soon" end },
        { badge = "L", label = "Media Library",
          desc = "Browse local audio/video on SD",
          action = function(scene) scene.set_status("Library: coming soon"); return "Library: coming soon" end },
        { badge = "M", label = "BGM Normalizer",
          desc = "Loudness-normalize background music",
          action = function(scene) scene.set_status("BGM: coming soon"); return "BGM: coming soon" end },
        { badge = "<", label = "Back",
          desc = "Return to Nexus",
          action = function() sm.switch("nexus", {}) end },
    },
})
