local nodes = {}

nodes.COLOR = {
    [0]={1.00,0.80,0.47}, [3]={0.94,0.35,0.24}, [5]={0.31,0.80,1.00},
    [2]={0.90,0.31,0.75}, [6]={0.69,0.43,0.94}, [4]={0.37,0.82,0.55},
    [1]={0.88,0.88,0.92}, [7]={0.39,0.51,0.82}, [8]={0.59,0.63,0.71},
    [9]={0.55,0.15,0.72}, [10]={1.00,0.71,0.20}, [11]={0.24,0.90,0.78},
    [12]={0.78,0.59,1.00}, [13]={1.00,0.47,0.63}, [14]={0.31,0.31,0.35},
}
nodes.PLANET_FILE = {
    start="start.png", window="muos.png", speaker="media_vault.png",
    forge="the_forge.png", toolbox="rt_toolbox.png", uplink="net_sphere.png",
    workshop="workshop.png", gear="settings.png", book="info.png",
    power="end.png", games="games.png", develop="develop.png",
    community="community.png", outerdesk="outerdesk.png", legacy="legacy.png",
}

-- END NODE alone on ring 4. Ring 1 = sun only, ring 2 = inner planets,
-- ring 3 = outer planets, ring 4 = END NODE comet alone.
nodes.LIST = {
    { idx=0, name="START SESSION", icon="start", ring=1,
      type="sun", size=34, scene="hub_session" },

    { idx=3, name="THE FORGE", icon="forge", ring=2,
      type="planet", size=22, surface="volcanic",
      ring_kind="asteroid_double", rot_speed=0.7,
      scene="hub_forge" },
    { idx=5, name="UPLINK", icon="uplink", ring=2,
      type="planet", size=18, surface="icy",
      rot_speed=0.9,
      orbit_mult=1.2, scene="hub_uplink" },
    { idx=2, name="MEDIA VAULT", icon="speaker", ring=2,
      type="planet", size=20, surface="ocean_clouds",
      ring_kind="thin", rot_speed=0.5,
      orbit_mult=1.1, scene="hub_media" },
    { idx=6, name="WORKSHOP", icon="workshop", ring=2,
      type="planet", size=15, surface="rocky_craters",
      rot_speed=1.0, scene="hub_workshop" },

    { idx=4, name="TOOLBOX", icon="toolbox", ring=3,
      type="planet", size=14, surface="rocky_craters",
      ring_kind="saturn_thick", moon=true, rot_speed=0.8, scene="hub_toolbox" },
    { idx=1, name="MUOS APPS", icon="window", ring=3,
      type="satellite", size=9, orbit_mult=2.5, scene="hub_mapps" },
    { idx=7, name="SETTINGS", icon="gear", ring=3,
      type="planet", size=13, surface="gas_bands",
      rot_speed=0.6, scene="hub_settings" },
    { idx=8, name="INFO", icon="book", ring=3,
      type="planet", size=12, surface="icy",
      rot_speed=0.4, scene="hub_info" },

    -- END NODE on its OWN outer orbit (ring 4), alone
    { idx=9, name="END NODE", icon="power", ring=4,
      type="comet", size=8, rot_speed=0.3, orbit_mult=0.5, scene="quit" },

    { idx=10, name="GAMES", icon="games", ring=2, hidden=true,
      type="planet", size=16, surface="gas_bands", rot_speed=0.7 },
    { idx=11, name="DEVELOP", icon="develop", ring=2, hidden=true,
      type="planet", size=14, surface="ocean_clouds", rot_speed=0.9 },
    { idx=12, name="COMMUNITY", icon="community", ring=3, hidden=true,
      type="planet", size=13, surface="rocky_craters", rot_speed=0.8 },
    { idx=13, name="OUTERDESK", icon="outerdesk", ring=3, hidden=true,
      type="planet", size=15, surface="icy", rot_speed=0.6 },
    { idx=14, name="LEGACY", icon="legacy", ring=4, hidden=true,
      type="planet", size=10, surface="volcanic", rot_speed=0.5 },
} 

for (base_position, node) in ipairs(nodes.LIST) do
    node.base_order = base_position
end

function nodes.color_for(idx) return nodes.COLOR[idx] or {0.5,0.5,0.5} end

-- Stable adapter from QWASAR workspace IDs to legacy NEXUS node identities.
-- Node indices, routes and orbital rings remain unchanged; only profile
-- visibility, enabled state, label and within-orbit navigation order change.
local WORKSPACE_BY_NODE = {
    [0] = "start-session",
    [3] = "the-forge",
    [5] = "uplink",
    [2] = "media-vault",
    [4] = "rt-toolbox",
    [7] = "settings",
    [8] = "info-community",
    [9] = "end-node",
}

function nodes.apply_profile(composition)
    if type(composition) ~= "table"
        or type(composition.workspaces) ~= "table" then
        return false, "invalid QWASAR workspace composition"
    end

    local by_id = {}
    for _, workspace in ipairs(composition.workspaces) do
        if type(workspace) == "table" and type(workspace.id) == "string" then
            by_id[workspace.id] = workspace
        end
    end

    for base_position, node in ipairs(nodes.LIST) do
        node.profile_enabled = true
        node.profile_visible = true
        node.profile_label = nil
        node.profile_order = 10000 + (node.base_order or base_position)

        local workspace_id = WORKSPACE_BY_NODE[node.idx]
        local workspace = workspace_id and by_id[workspace_id] or nil
        if workspace then
            node.profile_enabled = workspace.enabled ~= false
            node.profile_visible = workspace.visible ~= false
            node.profile_label = workspace.label
            node.profile_order = tonumber(workspace.order) or base_position
        end
    end

    nodes.profile_id = composition.profile and composition.profile.id or nil
    nodes.profile_name = composition.profile and composition.profile.name or nil
    table.sort(nodes.LIST, function(a, b)
        return (a.profile_order or 0) < (b.profile_order or 0)
    end)
    return true
end

function nodes.visible()
    local out = {}
    for _, n in ipairs(nodes.LIST) do
        if not n.hidden and n.profile_visible ~= false then
            table.insert(out, n)
        end
    end
    return out
end
function nodes.get(idx)
    for _, n in ipairs(nodes.LIST) do if n.idx == idx then return n end end
    return nil
end

local img_cache = {}
function nodes.image_for(icon_key)
    if img_cache[icon_key] ~= nil then return img_cache[icon_key] or nil end
    local fname = nodes.PLANET_FILE[icon_key]
    if not fname then img_cache[icon_key] = false; return nil end
    local ok, img = pcall(love.graphics.newImage, "assets/nexus_planets/" .. fname)
    if ok and img then img:setFilter("linear","linear"); img_cache[icon_key]=img; return img end
    img_cache[icon_key] = false; return nil
end

return nodes
