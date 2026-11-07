-- IPTV state: channels, groups, EPG cache, favorites
local bridge = require("core.bridge")
local config = require("core.config")

local iptv = {}

iptv.state = {
    channels = {},
    groups = {},
    group_filter = "*",
    filtered = {},
    selected = 1,
    loaded = false,
    loading = false,
    epg_loaded = false,
    epg_loading = false,
    last_error = nil,
    now_playing = nil,
}

-- Ensure favorites set exists
local function favorites_list()
    local f = config.get("iptv_favorites", {})
    if type(f) ~= "table" then f = {} end
    return f
end

function iptv.is_favorite(url)
    return favorites_list()[url] == true
end

function iptv.toggle_favorite(url)
    local f = favorites_list()
    if f[url] then
        f[url] = nil
    else
        f[url] = true
    end
    config.set("iptv_favorites", f)
    return f[url] == true
end

function iptv.apply_filter()
    local st = iptv.state
    local g = st.group_filter
    if g == "*" or g == nil then
        st.filtered = st.channels
    else
        local out = {}
        for _, ch in ipairs(st.channels) do
            if ch.group == g then table.insert(out, ch) end
        end
        st.filtered = out
    end
    st.selected = 1
    if #st.filtered == 0 then st.selected = 0 end
end

function iptv.next_group(dir)
    local st = iptv.state
    if #st.groups == 0 then return end
    local list = {"*"}
    for _, g in ipairs(st.groups) do table.insert(list, g) end
    local idx = 1
    for i, g in ipairs(list) do if g == st.group_filter then idx = i end end
    idx = ((idx - 1 + dir) % #list) + 1
    st.group_filter = list[idx]
    iptv.apply_filter()
end

function iptv.load_playlist(url, on_done)
    local st = iptv.state
    st.loading = true
    st.last_error = nil
    bridge.call("iptv_load_playlist", { url = url }, function(resp)
        st.loading = false
        if resp.ok then
            st.channels = resp.channels or {}
            st.groups = resp.groups or {}
            st.loaded = true
            iptv.apply_filter()
            if on_done then on_done(true, resp) end
        else
            st.last_error = resp.error or "load failed"
            if on_done then on_done(false, resp) end
        end
    end)
end

function iptv.load_epg(urls, on_done)
    local st = iptv.state
    st.epg_loading = true
    bridge.call("iptv_load_epg", { urls = urls or {} }, function(resp)
        st.epg_loading = false
        if resp.ok then
            st.epg_loaded = true
        end
        if on_done then on_done(resp) end
    end)
end

function iptv.epg_for(channel, on_done)
    bridge.call("iptv_epg_for", { channel = channel }, function(resp)
        if on_done then on_done(resp.now, resp.next) end
    end)
end

function iptv.play(channel, on_done)
    local st = iptv.state
    bridge.call("iptv_play", {
        url = channel.url, name = channel.name,
    }, function(resp)
        if resp.ok then
            st.now_playing = channel
            config.set("iptv_last_channel", channel.url or "")
        end
        if on_done then on_done(resp) end
    end)
end

function iptv.stop(on_done)
    bridge.call("iptv_stop", {}, function(resp)
        iptv.state.now_playing = nil
        if on_done then on_done(resp) end
    end)
end

function iptv.current_channel()
    local st = iptv.state
    if st.selected < 1 or st.selected > #st.filtered then return nil end
    return st.filtered[st.selected]
end

function iptv.move_selection(delta)
    local st = iptv.state
    if #st.filtered == 0 then return end
    st.selected = math.max(1, math.min(#st.filtered, st.selected + delta))
end

function iptv.get_default_playlist(cb)
    bridge.call("iptv_get_config", {}, function(resp)
        if resp.ok then
            local cfg = resp.config or {}
            local url = cfg.playlist_url or
                "https://iptv-org.github.io/iptv/countries/it.m3u"
            if cb then cb(url, cfg) end
        else
            if cb then cb("https://iptv-org.github.io/iptv/countries/it.m3u", {}) end
        end
    end)
end

return iptv
