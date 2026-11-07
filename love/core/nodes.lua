-- Node metadata: type, size, orbit speed, ring kind.
local nodes = {}

nodes.COLOR = {
    [0]  = { 1.00, 0.80, 0.47 },  -- START SESSION (sun, amber)
    [3]  = { 0.94, 0.35, 0.24 },  -- FORGE
    [5]  = { 0.31, 0.80, 1.00 },  -- UPLINK
    [2]  = { 0.90, 0.31, 0.75 },  -- MEDIA VAULT
    [6]  = { 0.69, 0.43, 0.94 },  -- WORKSHOP
    [4]  = { 0.37, 0.82, 0.55 },  -- TOOLBOX
    [1]  = { 0.88, 0.88, 0.92 },  -- MUOS APPS
    [7]  = { 0.39, 0.51, 0.82 },  -- SETTINGS
    [8]  = { 0.59, 0.63, 0.71 },  -- INFO
    [9]  = { 0.84, 0.31, 0.14 },  -- END NODE
    [10] = { 1.00, 0.71, 0.20 },  -- GAMES (hidden)
    [11] = { 0.24, 0.90, 0.78 },  -- DEVELOP (hidden)
    [12] = { 0.78, 0.59, 1.00 },  -- COMMUNITY (hidden)
    [13] = { 1.00, 0.47, 0.63 },  -- OUTERDESK (hidden)
    [14] = { 0.31, 0.31, 0.35 },  -- LEGACY (hidden)
}

nodes.PLANET_FILE = {
    start="start.png", window="muos.png", speaker="media_vault.png",
    forge="the_forge.png", toolbox="rt_toolbox.png", uplink="net_sphere.png",
    workshop="workshop.png", gear="settings.png", book="info.png",
    power="end.png",
    games="games.png", develop="develop.png", community="community.png",
    outerdesk="outerdesk.png", legacy="legacy.png",
}

-- LIST defines order, ring, type, size, extras.
-- type: "sun" | "planet" | "satellite"
-- ring_kind: "dust" | "signal" | "double" | nil
nodes.LIST = {
    -- Ring 1: SUN only
    { idx=0, name="START SESSION", icon="start",    ring=1,
      type="sun",    size=34, orbit_mult=1.0,
      scene=nil,    anim="sun" },

    -- Ring 2: inner planets (larger, mid-size)
    { idx=3, name="THE FORGE",     icon="forge",    ring=2,
      type="planet", size=22, ring_kind="dust",  ring_tilt=0.38,
      orbit_mult=1.0, rot_speed=0.5, scene="hub_forge", anim="burn" },
    { idx=5, name="UPLINK",        icon="uplink",   ring=2,
      type="planet", size=18, ring_kind="signal", ring_tilt=0.55,
      orbit_mult=1.2, rot_speed=0.8, scene=nil, anim="wave" },
    { idx=2, name="MEDIA VAULT",   icon="speaker",  ring=2,
      type="planet", size=20, ring_kind="double", ring_tilt=0.30,
      orbit_mult=1.1, rot_speed=0.6, scene=nil, anim="bars" },
    { idx=6, name="WORKSHOP",      icon="workshop", ring=2,
      type="planet", size=15, ring_kind=nil,
      orbit_mult=1.0, rot_speed=0.9, scene=nil, anim="sparks" },

    -- Ring 3: outer planets (smaller) + satellite
    { idx=4, name="TOOLBOX",       icon="toolbox",  ring=3,
      type="planet", size=14, moon=true,
      orbit_mult=1.0, rot_speed=1.0, scene=nil, anim="scan" },
    { idx=1, name="MUOS APPS",     icon="window",   ring=3,
      type="satellite", size=9, orbit_mult=2.5,
      scene=nil, anim="grid" },
    { idx=7, name="SETTINGS",      icon="gear",     ring=3,
      type="planet", size=13, ring_kind=nil,
      orbit_mult=1.0, rot_speed=1.2, scene=nil, anim="gear" },
    { idx=8, name="INFO",          icon="book",     ring=3,
      type="planet", size=12, ring_kind=nil,
      orbit_mult=1.0, rot_speed=0.7, scene=nil, anim="pages" },
    { idx=9, name="END NODE",      icon="power",    ring=3,
      type="planet", size=7, ring_kind=nil,
      orbit_mult=0.7, rot_speed=0.4, scene="quit", anim="dark" },

    -- Hidden nodes (kept for future)
    { idx=10, name="GAMES",     icon="games",     ring=2, hidden=true,
      type="planet", size=16, rot_speed=0.7, scene=nil },
    { idx=11, name="DEVELOP",   icon="develop",   ring=2, hidden=true,
      type="planet", size=14, rot_speed=0.9, scene=nil },
    { idx=12, name="COMMUNITY", icon="community", ring=3, hidden=true,
      type="planet", size=13, rot_speed=0.8, scene=nil },
    { idx=13, name="OUTERDESK", icon="outerdesk", ring=3, hidden=true,
      type="planet", size=15, rot_speed=0.6, scene=nil },
    { idx=14, name="LEGACY",    icon="legacy",    ring=4, hidden=true,
      type="planet", size=10, rot_speed=0.5, scene=nil },
}

function nodes.color_for(idx) return nodes.COLOR[idx] or {0.5,0.5,0.5} end

function nodes.visible()
    local out = {}
    for _, n in ipairs(nodes.LIST) do
        if not n.hidden then table.insert(out, n) end
    end
    return out
end

function nodes.get(idx)
    for _, n in ipairs(nodes.LIST) do
        if n.idx == idx then return n end
    end
    return nil
end

local img_cache = {}
function nodes.image_for(icon_key)
    if img_cache[icon_key] ~= nil then return img_cache[icon_key] or nil end
    local fname = nodes.PLANET_FILE[icon_key]
    if not fname then img_cache[icon_key] = false; return nil end
    local ok, img = pcall(love.graphics.newImage, "assets/nexus_planets/" .. fname)
    if ok and img then
        img:setFilter("linear", "linear")
        img_cache[icon_key] = img
        return img
    end
    img_cache[icon_key] = false
    return nil
end

return nodes
