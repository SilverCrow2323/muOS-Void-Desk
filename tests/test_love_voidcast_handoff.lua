-- Run with: luajit tests/test_love_voidcast_handoff.lua
package.path = "love/?.lua;love/?/init.lua;" .. package.path

local function equal(actual, expected, label)
    if actual ~= expected then
        error((label or "assertion failed") .. ": expected " ..
            tostring(expected) .. ", got " .. tostring(actual))
    end
end

local request = nil
local quit_count = 0
local statuses = {}

package.preload["core.dashboard_screen"] = function()
    return { new = function(spec) return spec end }
end
package.preload["core.bridge"] = function()
    return {
        call = function(command, args, callback)
            request = { command = command, args = args, callback = callback }
        end,
    }
end
package.preload["core.scene_manager"] = function()
    return {
        push = function() error("VoidCast must not open the LÖVE IPTV prototype") end,
        back = function() end,
    }
end
package.preload["core.nodes"] = function()
    return { color_for = function() return { 1, 0, 1 } end }
end
package.preload["core.widgets"] = function() return {} end
package.preload["core.external"] = function()
    return { launch = function() error("VoidCast must use its session hand-off") end }
end

love = {
    event = {
        quit = function() quit_count = quit_count + 1 end,
    },
}

local media = require("scenes.hub_media")
local item = media.items[2]
equal(item.label, "VoidCast IPTV", "Media menu entry")
equal(item.value, "OUTDESK", "Media entry identifies the bundled Outdesk app")

local scene = {
    set_status = function(message) statuses[#statuses + 1] = message end,
}
local result = item.action(scene)
equal(result, "Launching VoidCast...", "action feedback")
equal(request.command, "voidcast_launch", "service hand-off command")
equal(next(request.args), nil, "hand-off has no extra arguments")
equal(type(request.callback), "function", "service callback registered")
equal(quit_count, 0, "frontend stays alive until service accepts hand-off")
equal(statuses[1], "Handing off to VoidCast IPTV...", "initial status")

request.callback({ ok = true, handoff = true, note = "handoff accepted" })
equal(quit_count, 1, "accepted hand-off releases LÖVE")
equal(statuses[2], "Launching VoidCast...", "accepted hand-off status")

request = nil
statuses = {}
quit_count = 0
item.action(scene)
request.callback({ ok = false, error = "device only" })
equal(quit_count, 0, "rejected hand-off keeps LÖVE open")
equal(statuses[2], "VoidCast failed: device only", "rejection is visible")

print("LÖVE VoidCast hand-off: all tests passed")

request = nil
statuses = {}
quit_count = 0
item.action(scene)
request.callback({ ok = false, reason = "device-only" })
equal(quit_count, 0, "device-only rejection keeps LÖVE open")
equal(statuses[2], "VoidCast failed: device-only", "device-only reason is visible")
