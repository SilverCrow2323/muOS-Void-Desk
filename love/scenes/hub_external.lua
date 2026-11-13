local dashboard = require("core.dashboard_screen")
local sm        = require("core.scene_manager")
local nodes     = require("core.nodes")
local widgets   = require("core.widgets")
local ext       = require("core.external")

local category = "all"
local status_msg = "Loading external tools..."
local categories_list = {"all", "media", "toolbox", "uplink", "workshop"}

local function publish_status(scene, message)
    status_msg = tostring(message or "")
    if scene and scene.set_status then
        scene.set_status(status_msg)
    end
end

local function refresh(scene, silent)
    if not silent then publish_status(scene, "Loading external tools...") end
    ext.load(function(ok)
        if ok then
            publish_status(scene, string.format("%d tools available", #ext.state.tools))
        else
            publish_status(scene, "Error: " .. (ext.state.error or "load failed"))
        end
    end)
end

local function items_for(cat)
    local list = {}
    local tools = ext.by_hub(cat == "all" and nil or cat)
    for _, t in ipairs(tools) do
        local native_badge = (t.native_engine == "love") and "LOVE" or "PY"
        table.insert(list, {
            icon = t.icon or "gear",
            label = t.name .. "  [" .. native_badge .. "]",
            desc = (t.desc or "") .. (t.exists and "" or "  [NOT INSTALLED]"),
            action = function(scene)
                if not t.exists then
                    publish_status(scene, "Not installed: " .. t.name)
                    return "Not installed"
                end
                publish_status(scene, "Launching " .. t.name .. "...")
                ext.launch(t.id, function(resp)
                    if resp.ok then
                        publish_status(scene, "Launched: " .. t.name)
                    else
                        publish_status(scene, "Failed: " .. (resp.error or "unknown"))
                    end
                end)
                return "Launching..."
            end,
        })
    end
    table.insert(list, {
        badge = "C", label = "Cycle category  [" .. category:upper() .. "]",
        desc = "all / media / toolbox / uplink / workshop",
        action = function(scene)
            local idx = 1
            for i, c in ipairs(categories_list) do if c == category then idx = i end end
            category = categories_list[(idx % #categories_list) + 1]
            publish_status(scene, "Category: " .. category)
            return "Category: " .. category
        end,
    })
    table.insert(list, {
        badge = "<", label = "Back",
        desc = "Return to Nexus",
        action = function() sm.back() end,
    })
    return list
end

local config = {
    title = "EXTERNAL TOOLS",
    node_idx = 4,
    widget_height = 108,
    status = "VoidDesk ecosystem apps",

    on_enter = function(scene) refresh(scene, false) end,

    on_update = function(scene, dt)
        scene._t = (scene._t or 0) + dt
        if scene._t > 8 then scene._t = 0; refresh(scene, true) end
    end,

    widgets_draw = function(scene, alpha)
        local W = love.graphics.getWidth()
        local nc = nodes.color_for(4)
        local total = #ext.state.tools
        local installed = 0
        for _, t in ipairs(ext.state.tools) do
            if t.exists then installed = installed + 1 end
        end
        widgets.status_card(12, 62, (W-40)/2, 56, "gear",
            "Tools", string.format("%d registered", total),
            nc, "REG", alpha)
        widgets.status_card(12 + (W-40)/2 + 8, 62, (W-40)/2, 56, "folder",
            "Installed", string.format("%d ready", installed),
            (installed > 0 and {0.4,0.9,0.5} or {0.55,0.58,0.62}),
            installed > 0 and "OK" or "MISS", alpha)
        widgets.info_row(20, 128, W-40, "Category", category:upper(), nc, alpha)
        widgets.info_row(20, 148, W-40, "Status", status_msg, nc, alpha)
    end,

    items = {},
}
local scene = dashboard.new(config)

-- Override to use dynamic items
local base_enter = scene.enter
function scene.enter(args)
    base_enter(args)
    scene._items = items_for(category)
end

scene._get_items = function() return items_for(category) end

return scene
