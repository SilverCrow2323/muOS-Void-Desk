-- External tools registry (engine-agnostic)
local bridge = require("core.bridge")

local ext = {}
ext.state = { tools = {}, loaded = false, loading = false, error = nil }

function ext.load(on_done)
    if ext.state.loaded or ext.state.loading then
        if on_done then on_done(ext.state.loaded) end
        return
    end
    ext.state.loading = true
    bridge.call("list_external", {}, function(resp)
        ext.state.loading = false
        if resp.ok then
            ext.state.tools = resp.tools or {}
            ext.state.loaded = true
            ext.state.error = nil
        else
            ext.state.error = resp.error or "load failed"
        end
        if on_done then on_done(resp.ok) end
    end)
end

function ext.by_hub(hub)
    local out = {}
    for _, t in ipairs(ext.state.tools) do
        if not hub or t.hub == hub then
            table.insert(out, t)
        end
    end
    return out
end

function ext.get(tool_id)
    for _, t in ipairs(ext.state.tools) do
        if t.id == tool_id then return t end
    end
    return nil
end

function ext.launch(tool_id, on_done)
    bridge.call("launch_external", { id = tool_id }, function(resp)
        if on_done then on_done(resp) end
    end)
end

return ext
