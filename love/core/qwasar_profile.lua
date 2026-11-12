-- Engine-neutral QWASAR composition snapshot loader.
-- This module reads data only; profiles never supply Lua code or callbacks.
local json = require("lib.json")
local profile = { data = nil, error = nil }

local function snapshot_path()
    local root = os.getenv("VOIDDESK_APP_DIR") or "."
    return root .. "/data/qwasar_effective_profile.json"
end

function profile.load(path)
    local f, err = io.open(path or snapshot_path(), "rb")
    if not f then
        profile.data = nil
        profile.error = "cannot open effective profile: " .. tostring(err)
        return nil, profile.error
    end

    local source = f:read("*a")
    f:close()

    local ok, decoded = pcall(json.decode, source or "")
    if not ok or type(decoded) ~= "table" then
        profile.data = nil
        profile.error = "effective profile contains invalid JSON"
        return nil, profile.error
    end
    if decoded.schemaVersion ~= "1.0"
        or type(decoded.workspaces) ~= "table"
        or type(decoded.profile) ~= "table" then
        profile.data = nil
        profile.error = "effective profile has an unsupported composition shape"
        return nil, profile.error
    end

    profile.data = decoded
    profile.error = nil
    return profile.data
end

function profile.get()
    return profile.data
end

function profile.status()
    if not profile.data then
        return {
            loaded = false,
            error = profile.error or "profile not loaded",
        }
    end
    return {
        loaded = true,
        id = profile.data.profile and profile.data.profile.id or "",
        name = profile.data.profile and profile.data.profile.name or "",
        workspace_count = #profile.data.workspaces,
        warning_count = #(profile.data.warnings or {}),
    }
end

return profile
