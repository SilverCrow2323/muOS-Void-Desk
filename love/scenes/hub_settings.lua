local menu_screen = require("core.menu_screen")
local config = require("core.config")
local theme = require("theme.loader")
local sm = require("core.scene_manager")

return menu_screen.new({
    title = "SETTINGS",
    node_idx = 7,
    items = {
        { badge = "T", label = "Theme",
          desc = "Cycle: cyberpunk, crimson, stealth, green",
          action = function(scene)
              local themes = {"cyberpunk", "crimson", "stealth", "green"}
              local cur = config.get("theme", "cyberpunk")
              local idx = 1
              for i, t in ipairs(themes) do if t == cur then idx = i end end
              local nxt = themes[idx % #themes + 1]
              config.set("theme", nxt)
              theme.apply(nxt)
              scene.set_status("Theme: " .. nxt)
              return "Theme: " .. nxt
          end },
        { badge = "E", label = "Frontend Engine",
          desc = "py = PyEngine (stable)  ·  love = LoveEngine (this UI)",
          action = function(scene)
              local cur = config.get("engine", "love")
              local nxt = (cur == "py") and "love" or "py"
              config.set("engine", nxt)
              scene.set_status("Engine: " .. nxt .. " (takes effect on restart)")
              return "Engine: " .. nxt
          end },
        { badge = "B", label = "Back",
          desc = "Return to Nexus",
          action = function() sm.switch("nexus", {}) end },
    },
})
