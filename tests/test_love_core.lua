-- Regression tests for experimental LÖVE frontend foundations.
package.path = "love/?.lua;love/?/init.lua;" .. package.path

local function equal(actual, expected, message)
    if actual ~= expected then
        error((message or "assertion failed") .. ": expected "
            .. tostring(expected) .. ", got " .. tostring(actual))
    end
end

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
