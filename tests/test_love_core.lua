-- Regression tests for experimental LÖVE frontend foundations.
package.path = "love/?.lua;love/?/init.lua;" .. package.path

local function equal(actual, expected, message)
    if actual ~= expected then
        error((message or "assertion failed") .. ": expected "
            .. tostring(expected) .. ", got " .. tostring(actual))
    end
end

-- Every visible NEXUS node must point to an existing scene and texture.
local nodes = require("core.nodes")
local visible_nodes = nodes.visible()
equal(#visible_nodes, 10, "visible NEXUS node count")
local function file_exists(path)
    local handle = io.open(path, "rb")
    if handle then handle:close(); return true end
    return false
end
for _, node in ipairs(visible_nodes) do
    if node.scene ~= "quit" then
        assert(file_exists("love/scenes/" .. node.scene .. ".lua"),
               "missing scene for NEXUS node " .. node.name .. ": "
                   .. tostring(node.scene))
    end
    local texture = nodes.PLANET_FILE[node.icon]
    assert(texture, "missing texture mapping for NEXUS node " .. node.name)
    assert(file_exists("love/assets/nexus_planets/" .. texture),
           "missing texture file for NEXUS node " .. node.name .. ": "
               .. tostring(texture))
end

-- The QWASAR adapter may reorder mapped workspaces, hide them or disable
-- them, but it must preserve the legacy node identity and recovery entry.
local qwasar_workspaces = {
    { id = "start-session", order = 0, enabled = true, visible = true },
    { id = "the-forge", order = 1, enabled = true, visible = true },
    { id = "uplink", order = 2, enabled = false, visible = true },
    { id = "media-vault", order = 3, enabled = true, visible = true },
    { id = "rt-toolbox", order = 4, enabled = true, visible = false },
    { id = "settings", order = 5, enabled = true, visible = true },
    { id = "info-community", order = 6, enabled = true, visible = true },
    { id = "end-node", order = 7, enabled = true, visible = true },
}
local applied, apply_err = nodes.apply_profile({
    profile = { id = "test-profile", name = "Test profile" },
    workspaces = qwasar_workspaces,
})
equal(applied, true, "QWASAR profile should configure NEXUS")
local profiled_nodes = nodes.visible()
local expected_ids = { 0, 3, 5, 2, 7, 8, 9, 6, 1 }
equal(#profiled_nodes, #expected_ids, "hidden workspace should be omitted")
for i, expected_idx in ipairs(expected_ids) do
    equal(profiled_nodes[i].idx, expected_idx,
          "profile workspace order must preserve stable NEXUS node IDs")
end
local disabled_uplink = nodes.get(5)
equal(disabled_uplink.profile_enabled, false,
      "disabled workspace remains represented as disabled")
local hidden_toolbox = nodes.get(4)
equal(hidden_toolbox.profile_visible, false,
      "hidden workspace is removed from visible NEXUS nodes")
local protected_end = nodes.get(9)
equal(protected_end.profile_visible, true,
      "END NODE remains visible when present in a valid profile")


-- Every release-critical subscene must exist on disk.
assert(file_exists("love/scenes/hub_apt.lua"),
       "missing native APT manager scene")
assert(file_exists("love/scenes/hub_tailscale.lua"),
       "missing native Tailscale scene")
assert(file_exists("love/scenes/hub_syncthing.lua"),
       "missing native Syncthing scene")
assert(file_exists("love/scenes/hub_diagnostics.lua"),
       "missing native diagnostics scene")
assert(file_exists("love/scenes/hub_monitor.lua"),
       "missing native system monitor scene")

-- The integrated login screen must be able to generate a real QR matrix.
local qr = require("lib.qr")
local qr_ok, qr_matrix, qr_size = qr.encode(
    "https://login.tailscale.com/a/voiddesk-regression-check")
equal(qr_ok, true, "Tailscale login QR should encode")
equal(qr_size, #qr_matrix, "QR matrix size should match its row count")

-- A child scene should load on demand even when main.lua did not register it.
local sm = require("core.scene_manager")
local entered_value = nil
package.preload["scenes.lazy_probe"] = function()
    return {
        enter = function(args)
            entered_value = args and args.value
        end,
    }
end
sm.register("base_probe", {
    enter = function() end,
    save_state = function() return { selected = 3 } end,
})
equal(sm.switch("base_probe", {}), true, "base scene should open")
equal(sm.push("lazy_probe", { value = 42 }), true, "lazy scene should open")
equal(entered_value, 42, "lazy scene should receive arguments")
equal(sm.is_registered("lazy_probe"), true, "lazy scene should be cached")
equal(sm.current_name(), "lazy_probe", "lazy scene should be current")
equal(sm.back(), true, "back should restore previous scene")
equal(sm.current_name(), "base_probe", "base scene should be restored")

-- A broken scene must be reported and must not crash the screenshot loop.
sm.register("broken_draw_probe", {
    enter = function() end,
    draw = function() error("synthetic draw failure") end,
})
equal(sm.switch("broken_draw_probe", {}), true, "broken scene should enter")
local draw_ok = sm.draw()
equal(draw_ok, false, "draw failure should be caught")
assert(tostring(sm.current_error()):find("synthetic draw failure", 1, true),
       "draw failure should remain inspectable")

-- The bridge has a single request/response file pair. Requests must queue.
local now = 0
love = {
    timer = {
        getTime = function() return now end,
        getDelta = function()
            now = now + 0.1
            return 0.1
        end,
    },
}
local json = require("lib.json")
local bridge = require("core.bridge")
bridge.init()

local root = assert(os.getenv("VOIDDESK_APP_DIR"),
                    "VOIDDESK_APP_DIR must point to a test directory")

-- LÖVE configuration writes must be atomic and fail without mutating memory.
local config = require("core.config")
config.load()
equal(config.set("theme", "megastructure"), true,
      "config should save a valid theme")
local config_file = assert(io.open(config.path(), "r"))
local saved_text = config_file:read("*a")
config_file:close()
local saved_data = json.decode(saved_text)
equal(saved_data.theme, "megastructure", "saved theme should be present")

-- New palette presets are registered and expose the common colour tokens.
local themes = require("theme.loader")
local theme_ids = {"megastructure", "manga_ink", "industrial", "terminal", "minimal"}
for _, id in ipairs(theme_ids) do
    local palette = themes.list()[id]
    assert(type(palette) == "table", "missing theme palette: " .. id)
    assert(type(palette.bg) == "table" and type(palette.accent) == "table",
           "incomplete theme palette: " .. id)
end

local data_dir = root .. "/data"
local held_dir = data_dir .. ".held"
assert(os.rename(data_dir, held_dir), "test must be able to hold the data directory")
equal(config.set("theme", "must-not-persist"), false,
      "config write should fail when the data directory is unavailable")
equal(config.get("theme"), "megastructure",
      "failed config write must preserve in-memory value")
assert(os.rename(held_dir, data_dir), "test must restore the data directory")
local verify_file = assert(io.open(config.path(), "r"))
local verify_text = verify_file:read("*a")
verify_file:close()
equal(verify_text, saved_text, "failed config write must preserve last good file")
local request_path = bridge.req_path()
local processing_path = root .. "/data/.love_request.processing"
local response_path = bridge.resp_path()
local first_result, second_result = nil, nil

local first_id = bridge.call("first_command", { value = 1 }, function(resp)
    first_result = resp
end)
local second_id = bridge.call("second_command", { value = 2 }, function(resp)
    second_result = resp
end)
equal(bridge.pending_count(), 2, "both requests should be tracked")

local function read_json(path)
    local file = assert(io.open(path, "r"), "expected file: " .. path)
    local body = file:read("*a")
    file:close()
    return json.decode(body)
end

local function write_json(path, value)
    local file = assert(io.open(path, "w"), "cannot write: " .. path)
    file:write(json.encode(value))
    file:close()
end

local first_request = read_json(request_path)
equal(first_request.id, first_id, "first request id")
equal(first_request.cmd, "first_command", "first request command")
equal(first_request.args.value, 1, "first request args")
assert(os.rename(request_path, processing_path), "service claims request one")
write_json(response_path, { id = first_id, ok = true, value = "one" })
bridge.poll()
equal(first_result and first_result.value, "one", "first callback result")
os.remove(processing_path)

local second_request = read_json(request_path)
equal(second_request.id, second_id, "second request id")
equal(second_request.cmd, "second_command", "second request command")
equal(second_request.args.value, 2, "second request args")
assert(os.rename(request_path, processing_path), "service claims request two")

write_json(response_path, { id = second_id + 99, ok = true, value = "stale" })
bridge.poll()
equal(second_result, nil, "stale responses must not complete a request")

write_json(response_path, { id = second_id, ok = true, value = "two" })
bridge.poll()
equal(second_result and second_result.value, "two", "second callback result")
equal(bridge.pending_count(), 0, "request queue should be empty")

os.remove(processing_path)
os.remove(request_path)
os.remove(response_path)
print("LÖVE frontend core tests: OK")
