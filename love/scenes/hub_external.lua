local dashboard = require("core.dashboard_screen")
local sm        = require("core.scene_manager")
local nodes     = require("core.nodes")
local widgets   = require("core.widgets")
local ext       = require("core.external")

local category = "all"
local scene_ref = nil
local status_msg = "Loading external tools..."

local function refresh(scene, silent)
    if not silent then scene.set_status("Loading external tools...") end
    ext.load(function(ok)
        if ok then
            scene.set_status(string.format("%d tools available", #ext.state.tools))
        else
            scene.set_status("Error: " .. (ext.state.error or "load failed"))
        end
    end)
end

local function items_for(cat)
    local list = {}
    local all = ext.state.tools
    for _, t in ipairs(all) do
        if cat == "all" or t.category == cat then
            table.insert(list, {
                badge = (t.icon or "?"):sub(1,1):upper(),
                label = t.name or t.id,
                desc = (t.desc or "") .. (t.exists and "" or " [NOT INSTALLED]"),
                action = function(scene)
                    if not t.exists then
                        scene.set_status("Not installed: " .. t.name)
                        return "Not installed"
                    end
                    scene.set_status("Launching " .. t.name .. "...")
                    ext.launch(t.id, function(resp)
                        if resp.ok then
                            scene.set_status("Launched: " .. t.name)
                        else
                            scene.set_status("Failed: " .. (resp.error or "unknown"))
                        end
                    end)
                    return "Launching..."
                end,
            })
        end
    end
    -- Back entry
    table.insert(list, {
        badge = "<", label = "Back",
        desc = "Return to Nexus",
        action = function() sm.switch("nexus", {}) end,
    })
    return list
end

local config = {
    title = "EXTERNAL TOOLS",
    node_idx = 4,   -- toolbox color
    widget_height = 130,
    status = "External apps & tools",

    on_enter = function(scene)
        scene_ref = scene
        refresh(scene, false)
    end,

    on_update = function(scene, dt)
        scene._t = (scene._t or 0) + dt
        if scene._t > 6 then scene._t = 0; refresh(scene, true) end
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
            "Tools", string.format("%d total", total),
            nc, "EXT", alpha)
        widgets.status_card(12 + (W-40)/2 + 8, 62, (W-40)/2, 56, "folder",
            "Installed", string.format("%d ready", installed),
            (installed > 0 and {0.4,0.9,0.5} or {0.55,0.58,0.62}),
            installed > 0 and "OK" or "MISS", alpha)
        widgets.info_row(20, 128, W-40, "Category", category:upper(), nc, alpha)
        widgets.info_row(20, 148, W-40, "Status", status_msg, nc, alpha)
    end,

    -- Items are rebuilt on the fly by menu_screen if we use a function;
    -- but dashboard uses static list. Use on_enter to mutate scene._items.
    items = {},
}
local scene = dashboard.new(config)

-- Override enter to rebuild items based on loaded tools
local base_enter = scene.enter
function scene.enter(args)
    base_enter(args)
    -- Build initial items (they will update when load completes)
    scene._items = items_for(category)
    -- Patch input handler to use dynamic items
    -- (dashboard's static items list is captured at construction; we hook
    --  the refresh callback to update the internal list by reconstructing)
    if scene._replace_items then scene._replace_items(scene._items) end
end

-- Provide accessor for dashboard to grab current items
scene._get_items = function() return items_for(category) end

return scene
