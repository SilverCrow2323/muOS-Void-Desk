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
    data = { lang = "en", theme = "cyberpunk", home_style = "nexus" }
end

function config.get(k, default)
    local v = data[k]
    if v == nil then return default end
    return v
end

function config.set(k, v)
    data[k] = v
    local f = io.open(config.path(), "w")
    if f then
        f:write(json.encode(data))
        f:close()
    end
end

function config.data() return data end

return config
