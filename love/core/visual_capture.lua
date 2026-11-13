-- F12 capture and repeatable full-scene screenshot pass for the experimental LÖVE UI.
-- captureScreenshot runs after the current love.draw frame (LÖVE 11.0+).
local json = require("lib.json")
local capture = {}

local pending = false
local sequence = 0
local batch = nil

local BATCH_SCENES = {
    { name = "bootanim", args = {} },
    { name = "intro", args = { duration = 1.0 } },
    { name = "nexus", args = {} },
    { name = "hub_session", args = {} },
    { name = "hub_forge", args = {} },
    { name = "hub_apt", args = {} },
    { name = "hub_uplink", args = {} },
    { name = "hub_tailscale", args = {} },
    { name = "hub_syncthing", args = {} },
    { name = "hub_media", args = {} },
    { name = "void_radio", args = {} },
    { name = "media_library", args = {} },
    { name = "hub_workshop", args = {} },
    { name = "hub_diagnostics", args = {} },
    { name = "hub_monitor", args = {} },
    { name = "hub_toolbox", args = {} },
    { name = "hub_notes", args = {} },
    { name = "hub_rss", args = {} },
    { name = "hub_weather", args = {} },
    { name = "hub_mapps", args = {} },
    { name = "hub_external", args = {} },
    { name = "hub_settings", args = {} },
    { name = "hub_display_fx", args = {} },
    { name = "hub_info", args = {} },
    { name = "hub_iptv", args = {} },
    { name = "hub_calendar", args = {} },
    { name = "hub_shell", args = {} },
    { name = "tool_calc", args = {} },
    { name = "tool_clock", args = {} },
    { name = "tool_editor", args = {} },
    { name = "tablet_overview", scene = "nexus", overlay = "tablet", page = 1, args = {} },
    { name = "tablet_processes", scene = "nexus", overlay = "tablet", page = 2, args = {} },
    { name = "tablet_system", scene = "nexus", overlay = "tablet", page = 3, args = {} },
    { name = "tablet_network", scene = "nexus", overlay = "tablet", page = 4, args = {} },
    { name = "tablet_media", scene = "nexus", overlay = "tablet", page = 5, args = {} },
    { name = "tablet_activity", scene = "nexus", overlay = "tablet", page = 6, args = {} },
    { name = "operation_overlay", scene = "hub_toolbox", overlay = "operation", args = {} },
}

local function app_dir()
    return os.getenv("VOIDDESK_APP_DIR") or "."
end

local function output_dir()
    return app_dir() .. "/data/visual-captures"
end

local function safe_token(value)
    local token = tostring(value or "screen"):gsub("[^%w_-]+", "-")
    token = token:gsub("^[%-_]+", ""):gsub("[%-_]+$", "")
    if token == "" then token = "screen" end
    return token:sub(1, 48)
end

local function shell_quote(value)
    return "'" .. tostring(value):gsub("'", "'\\''") .. "'"
end

local function ensure_output_dir()
    local command = "mkdir -p " .. shell_quote(output_dir())
    local ok, why, code = os.execute(command)
    if ok == true or ok == 0 or code == 0 then
        return true
    end
    return false, tostring(why or code or "mkdir failed")
end

local function write_atomic(path, contents)
    local temporary = path .. ".tmp"
    local f, err = io.open(temporary, "wb")
    if not f then return false, err end
    local ok, write_err = f:write(contents)
    local close_ok, close_err = f:close()
    if not ok or not close_ok then
        os.remove(temporary)
        return false, write_err or close_err
    end
    local renamed, rename_err = os.rename(temporary, path)
    if not renamed then
        os.remove(temporary)
        return false, rename_err
    end
    return true
end

local function save_frame(image, screen_name, mode)
    local screen = safe_token(screen_name)
    local stamp = os.date("!%Y%m%dT%H%M%S")
    sequence = sequence + 1
    local stem = string.format("love__%s__%s_%03d", screen, stamp, sequence)
    local dir = output_dir()
    local image_path = dir .. "/" .. stem .. ".png"
    local metadata_path = dir .. "/" .. stem .. ".json"

    local encoded = image:encode("png")
    local saved, save_err = write_atomic(image_path, encoded:getString())
    if not saved then error(save_err or "cannot save PNG") end

    local width, height = image:getDimensions()
    local payload = {
        engine = "love",
        screen = screen,
        capture_mode = mode or "manual",
        timestamp_utc = os.date("!%Y-%m-%dT%H:%M:%SZ"),
        width = width,
        height = height,
        image = stem .. ".png",
        version = "10.5.4",
    }
    local meta_ok, meta_err = write_atomic(
        metadata_path, json.encode(payload) .. "\n")
    if not meta_ok then error(meta_err or "cannot save metadata") end
    return "data/visual-captures/" .. stem .. ".png", payload
end

local function queue_capture(screen_name, mode, callback)
    if pending then
        return false, "a screenshot is already being saved"
    end
    local dir_ok, dir_err = ensure_output_dir()
    if not dir_ok then
        return false, "cannot create screenshot directory: " .. tostring(dir_err)
    end
    pending = true

    local ok, err = pcall(love.graphics.captureScreenshot, function(image)
        local saved, result = pcall(save_frame, image, screen_name, mode)
        pending = false
        if saved then
            print("[visual-capture] saved " .. result)
        else
            print("[visual-capture] failed: " .. tostring(result))
        end
        if callback then callback(saved, result) end
    end)

    if not ok then
        pending = false
        return false, err
    end
    return true
end

function capture.capture(scene_name)
    return queue_capture(scene_name, "manual")
end

local function write_batch_manifest()
    if not batch then return end
    local manifest = {
        engine = "love",
        mode = "all-scenes",
        version = "10.5.4",
        started_utc = batch.started_utc,
        completed_utc = os.date("!%Y-%m-%dT%H:%M:%SZ"),
        requested = #batch.scenes,
        captured = batch.captured,
        failed = batch.failed,
    }
    local ok, err = write_atomic(
        output_dir() .. "/love-batch-manifest.json",
        json.encode(manifest) .. "\n")
    if not ok then
        print("[visual-capture] cannot write batch manifest: " .. tostring(err))
    end
    print(string.format(
        "[visual-capture] batch complete: %d/%d captured, %d failed",
        #batch.captured, #batch.scenes, #batch.failed))
end

local function finish_batch()
    write_batch_manifest()
    batch = nil
    love.event.quit()
end

local function add_failed(name, reason)
    table.insert(batch.failed, {
        screen = name,
        error = tostring(reason or "scene could not be entered"),
    })
end

local function seed_global_overlay(target)
    local jobs = package.loaded["core.jobs"]
    local tablet = package.loaded["core.tablet"]
    if jobs then
        jobs.active = {}
        jobs.focus_id = nil
        jobs.overlay_open = false
        jobs.poll_timer = 0
        jobs.POLL_INTERVAL = 10
    end
    if tablet then
        tablet.active = false
        tablet.slide = 0
        tablet.poll = 0
        tablet.scroll = 0
    end

    if target.overlay == "tablet" and tablet and jobs then
        local visual_job = {
            id = "visual-capture-job",
            name = "Download system runtime",
            hub = "THE FORGE",
            status = "running",
            started = love.timer.getTime(),
            progress = 64,
            phase = "DOWNLOADING",
            message = "Receiving verified package chunks",
            detail = "runtime-aarch64.tar.zst · 14.2 / 22.0 MB",
            description = "Downloading the matching AArch64 runtime into the staging area.",
            reason = "The selected desktop operation needs the runtime before package assembly.",
            icon = "download",
            animation = "download",
            severity = "info",
            indeterminate = false,
            can_background = true,
            color = {0.24, 0.72, 0.96},
        }
        jobs.active[visual_job.id] = visual_job
        tablet.system = {
            model = "RG35XX H",
            kernel = "6.1.73-muos",
            uptime = "4h 12m",
            ram = {pct = 42, used_mb = 860, total_mb = 2048},
            disk = {{free_gb = 18.4, total_gb = 64.0}},
        }
        tablet.network = {
            wifi = {connected = true, ssid = "QWASAR-LINK", ip = "192.168.1.42"},
            bt = {on = true, count = 2},
            hotspot = {on = false},
            info = {gateway = "192.168.1.1"},
        }
        tablet.media = {
            now_playing = "Void Radio · Night Drive",
            volume = 42,
            paused = false,
            library_count = 128,
            recordings = 3,
        }
        tablet.radio = {}
        tablet.iptv = {state = "idle"}
        tablet.active = true
        tablet.slide = 1
        tablet.page = target.page or 1
        tablet.poll = 0
        tablet.scroll = 0
    elseif target.overlay == "operation" and jobs then
        local visual_job = {
            id = "visual-capture-operation",
            name = "Install desktop runtime",
            hub = "START SESSION",
            status = "running",
            started = love.timer.getTime(),
            progress = 64,
            phase = "EXTRACTING",
            message = "Unpacking verified runtime files",
            detail = "lib/runtime · 14.2 / 22.0 MB",
            description = "Preparing the selected runtime inside the isolated desktop image.",
            reason = "XFCE and the selected desktop session require this runtime before launch.",
            icon = "package",
            animation = "extract",
            severity = "info",
            indeterminate = false,
            can_background = true,
            color = {0.24, 0.72, 0.96},
        }
        jobs.active[visual_job.id] = visual_job
        jobs.focus_id = visual_job.id
        jobs.overlay_open = true
    end
end

local function switch_to_next_scene()
    if not batch then return end
    if batch.index > #batch.scenes then
        finish_batch()
        return
    end

    local target = batch.scenes[batch.index]
    local scene_name = target.scene or target.name
    local ok, result = pcall(batch.manager.switch, scene_name, target.args)
    if not ok or result ~= true then
        add_failed(target.name, ok and batch.manager.last_error()
            or result)
        batch.index = batch.index + 1
        switch_to_next_scene()
        return
    end

    seed_global_overlay(target)
    batch.current = target
    batch.elapsed = 0
    batch.phase = "settle"
end

function capture.start_batch(scene_manager, settle_seconds)
    if batch then return false, "batch capture is already running" end
    local dir_ok, dir_err = ensure_output_dir()
    if not dir_ok then
        return false, "cannot create screenshot directory: " .. tostring(dir_err)
    end
    batch = {
        manager = scene_manager,
        scenes = BATCH_SCENES,
        index = 1,
        current = nil,
        elapsed = 0,
        settle_seconds = tonumber(settle_seconds)
            or tonumber(os.getenv("VOIDDESK_CAPTURE_SETTLE"))
            or 0.85,
        phase = "settle",
        started_utc = os.date("!%Y-%m-%dT%H:%M:%SZ"),
        captured = {},
        failed = {},
    }
    print("[visual-capture] starting full LÖVE scene pass")
    switch_to_next_scene()
    return true
end

function capture.update(dt)
    if not batch or pending or batch.phase ~= "settle" then return end
    batch.elapsed = batch.elapsed + dt
    if batch.elapsed < batch.settle_seconds then return end

    local target = batch.current
    local draw_error = batch.manager.current_error
        and batch.manager.current_error()
    if draw_error then
        add_failed(target.name, draw_error)
        batch.index = batch.index + 1
        switch_to_next_scene()
        return
    end

    batch.phase = "capture"
    local ok, err = queue_capture(target.name, "automated", function(saved, result)
        if not batch then return end
        if saved then
            table.insert(batch.captured, {
                screen = target.name,
                path = result,
            })
        else
            add_failed(target.name, result)
        end
        batch.index = batch.index + 1
        switch_to_next_scene()
    end)

    if not ok then
        add_failed(target.name, err)
        batch.index = batch.index + 1
        switch_to_next_scene()
    end
end

function capture.is_pending()
    return pending
end

function capture.is_batch_running()
    return batch ~= nil
end

return capture
