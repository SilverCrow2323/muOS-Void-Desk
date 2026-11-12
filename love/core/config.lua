local json = require("lib.json")
local config = {}
local data = {}

local function app_dir()
    return os.getenv("VOIDDESK_APP_DIR") or "."
end

function config.path()
    return app_dir() .. "/data/desk_config.json"
end

function config.load()
    local f = io.open(config.path(), "r")
    if f then
        local s = f:read("*a") ; f:close()
        local ok, parsed = pcall(json.decode, s)
        if ok and type(parsed) == "table" then
            data = parsed
            return
        end
    end
    data = {
        lang = "en", theme = "cyberpunk", home_style = "nexus",
        engine = "love", bg_anim = true, sfx = true, music = true,
        muos_profile = "auto",
        show_bootanim = true,
    }
end

function config.get(k, default)
    local v = data[k]
    if v == nil then return default end
    return v
end

-- Persist to a sibling temporary file and atomically rename it over the
-- active config. A failed write leaves the last good file and memory intact.
function config.set(k, v)
    local candidate = {}
    for key, value in pairs(data) do candidate[key] = value end
    candidate[k] = v

    local ok, encoded = pcall(json.encode, candidate)
    if not ok or type(encoded) ~= "string" then return false end

    local path = config.path()
    local temporary = path .. ".tmp"
    os.remove(temporary)
    local f = io.open(temporary, "wb")
    if not f then return false end

    local wrote = f:write(encoded)
    local flushed = wrote and f:flush()
    local closed = f:close()
    if not wrote or not flushed or not closed then
        os.remove(temporary)
        return false
    end

    local renamed = os.rename(temporary, path)
    if not renamed then
        os.remove(temporary)
        return false
    end

    data = candidate
    return true
end

function config.data() return data end

return config
