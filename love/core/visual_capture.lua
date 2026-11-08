-- F12 frame capture for the experimental LÖVE frontend.
-- love.graphics.captureScreenshot invokes the callback after love.draw.
local json = require("lib.json")
local capture = {}
local pending = false
local sequence = 0

local function safe_token(value)
    local token = tostring(value or "screen"):gsub("[^%w_-]+", "-")
    token = token:gsub("^[%-_]+", ""):gsub("[%-_]+$", "")
    if token == "" then token = "screen" end
    return token:sub(1, 48)
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

function capture.capture(scene_name)
    if pending then
        return false, "a screenshot is already being saved"
    end
    pending = true

    local app_dir = os.getenv("VOIDDESK_APP_DIR") or "."
    local dir = app_dir .. "/data/visual-captures"
    local stamp = os.date("!%Y%m%dT%H%M%S")
    sequence = sequence + 1
    local screen = safe_token(scene_name)
    local stem = string.format("love__%s__%s_%03d", screen, stamp, sequence)
    local image_path = dir .. "/" .. stem .. ".png"
    local metadata_path = dir .. "/" .. stem .. ".json"

    local ok, err = pcall(love.graphics.captureScreenshot, function(image)
        local success, reason = pcall(function()
            local encoded = image:encode("png")
            local saved, save_err = write_atomic(image_path, encoded:getString())
            if not saved then
                error(save_err or "cannot save PNG")
            end

            local width, height = image:getDimensions()
            local payload = {
                engine = "love",
                screen = screen,
                timestamp_utc = os.date("!%Y-%m-%dT%H:%M:%SZ"),
                width = width,
                height = height,
                image = stem .. ".png",
                version = "10.5.4",
            }
            local meta_ok, meta_err = write_atomic(
                metadata_path, json.encode(payload) .. "\n")
            if not meta_ok then
                error(meta_err or "cannot save metadata")
            end
        end)

        pending = false
        if success then
            print("[visual-capture] saved " .. image_path)
        else
            print("[visual-capture] failed: " .. tostring(reason))
        end
    end)

    if not ok then
        pending = false
        return false, err
    end
    return true
end

function capture.is_pending()
    return pending
end

return capture
