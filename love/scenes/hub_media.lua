local menu_screen = require("core.menu_screen")
local sm = require("core.scene_manager")

return menu_screen.new({
    title = "MEDIA VAULT",
    node_idx = 2,
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
