local sm = require("core.scene_manager")
local bridge = require("core.bridge")
local input = require("core.input")
local theme = require("theme.loader")
local chrome = require("core.chrome")
local font = require("core.font")
local nodes = require("core.nodes")
local jobs = require("core.jobs")

local scene = {}
local categories = {"all","news","tech","linux","gaming","retro","anime"}
local state = {
    category = 1, language = "all", items = {}, errors = {},
    selected = 1, first = 1, status = "Loading saved headlines...",
    loading = false, job_id = nil, cache_time = "",
    cached_category = nil, cached_language = nil,
}
local ROW_H = 42

local function refresh_cache()
    if state.loading then return end
    state.loading = true
    bridge.call("rss_cache", {}, function(resp)
        state.loading = false
        if resp.ok then
            state.items = resp.items or {}
            state.errors = resp.errors or {}
            state.selected = math.max(1, math.min(state.selected, math.max(1,#state.items)))
            state.cache_time = tostring(resp.updated or "")
            state.cached_category = resp.category or "all"
            state.cached_language = resp.language or "all"
            if resp.cached then
                state.status = string.format("%d headlines · %s", #state.items, tostring(resp.category or "all"))
            elseif #state.items == 0 then
                state.status = "No saved headlines. Press Y to update feeds."
            end
        else
            state.status = "RSS cache: " .. tostring(resp.error or "unavailable")
        end
    end)
end

local function cache_matches_filter()
    return state.cached_category == categories[state.category]
        and state.cached_language == state.language
end

local function request_refresh()
    if state.job_id then
        local current = jobs.active[tostring(state.job_id)]
        if current and (current.status == "running" or current.status == "starting") then
            jobs.show_job(state.job_id)
            return
        end
    end
    local category = categories[state.category]
    state.status = "Preparing " .. category .. " feeds..."
    bridge.call("job_start", {
        service_task = "rss_refresh",
        category = category,
        language = state.language,
        name = "Refresh RSS",
        hub = "toolbox",
        description = "Fetch a small selection of trusted RSS/Atom sources and cache recent headlines.",
        reason = "The selected public feeds need to be refreshed before their articles can be browsed offline.",
        icon = "rss",
        animation = "download",
        can_background = true,
    }, function(resp)
        if resp.ok and resp.job then
            state.job_id = tostring(resp.job.id)
            state.status = "Refreshing " .. category .. " feeds..."
        else
            state.status = "RSS refresh failed: " .. tostring(resp.error or "unknown error")
        end
    end)
end

local function open_selected()
    local item = state.items[state.selected]
    if not item or not item.url or not love.system then return end
    local ok, result = pcall(love.system.openURL, item.url)
    if not ok or result == false then
        state.status = "Unable to open article link on this platform."
    else
        state.status = "Opening " .. tostring(item.source or "article") .. "..."
    end
end

local function change_category(delta)
    state.category = ((state.category - 1 + delta) % #categories) + 1
    state.selected = 1
    state.first = 1
    state.status = "Filter: " .. categories[state.category]
end

function scene.enter()
    input.clear()
    state.selected, state.first = 1, 1
    state.job_id = nil
    state.status = "Loading saved headlines..."
    refresh_cache()
    input.on("press", function(action)
        if action == "up" then
            state.selected = math.max(1, state.selected - 1)
        elseif action == "down" then
            state.selected = math.min(cache_matches_filter() and #state.items or 0, state.selected + 1)
        elseif action == "left" or action == "l1" then
            change_category(-1)
        elseif action == "right" or action == "r1" then
            change_category(1)
        elseif action == "x" then
            state.language = state.language == "all" and "it" or
                (state.language == "it" and "en" or "all")
            state.status = "Language: " .. state.language:upper()
        elseif action == "y" or action == "start" then
            request_refresh()
        elseif action == "a" then
            if cache_matches_filter() then open_selected() else state.status = "Press Y to fetch this filter." end
        elseif action == "select" then
            refresh_cache()
        elseif action == "b" or action == "menu" then
            sm.back()
        end
    end)
end

function scene.update(dt)
    scene._poll = (scene._poll or 0) + dt
    if scene._poll >= 0.7 then
        scene._poll = 0
        if state.job_id then
            local job = jobs.active[tostring(state.job_id)]
            if job and (job.status == "done" or job.status == "error") then
                state.job_id = nil
                state.status = job.status == "done" and "Feeds updated." or
                    ("Refresh failed · " .. tostring(job.message or "see process log"))
                refresh_cache()
            end
        end
    end
end

function scene.draw()
    local W,H = love.graphics.getDimensions()
    local th = theme.get()
    local accent = nodes.color_for(4)
    love.graphics.clear(th.bg[1],th.bg[2],th.bg[3],1)
    chrome.draw_header({theme=th,title="VOID-DESK",subtitle="SIGNAL / RSS",status_icons={"rss","wifi","battery"}})

    love.graphics.setColor(0.045,0.06,0.082,0.98)
    love.graphics.rectangle("fill",12,68,W-24,54,7)
    love.graphics.setColor(accent[1],accent[2],accent[3],0.72)
    love.graphics.rectangle("line",12,68,W-24,54,7)
    love.graphics.setFont(font.bold(13) or love.graphics.newFont(13))
    love.graphics.setColor(0.92,0.96,1,1)
    love.graphics.print("CATEGORY  /  "..categories[state.category]:upper(),24,78)
    love.graphics.setFont(font.regular(9) or love.graphics.newFont(9))
    love.graphics.setColor(0.53,0.68,0.8,1)
    love.graphics.print("LANGUAGE "..state.language:upper().."  ·  "..#state.items.." HEADLINES",24,99)

    local top,bottom = 132,H-84
    local matches_filter = cache_matches_filter()
    local visible_items = matches_filter and state.items or {}
    local visible = math.max(1,math.floor((bottom-top)/ROW_H))
    state.first = math.max(1,math.min(state.selected-visible+1,math.max(1,#visible_items-visible+1)))
    for i=state.first,math.min(#visible_items,state.first+visible-1) do
        local item = visible_items[i]
        local y = top+(i-state.first)*ROW_H
        local selected = i==state.selected
        love.graphics.setColor(selected and 0.11 or 0.055,selected and 0.15 or 0.075,selected and 0.20 or 0.105,0.98)
        love.graphics.rectangle("fill",16,y,W-32,ROW_H-4,5)
        love.graphics.setColor(selected and accent[1] or 0.22,selected and accent[2] or 0.32,selected and accent[3] or 0.42,selected and 0.95 or 0.4)
        love.graphics.rectangle("line",16,y,W-32,ROW_H-4,5)
        love.graphics.setFont(font.bold(10) or love.graphics.newFont(10))
        love.graphics.setColor(0.91,0.95,1,1)
        love.graphics.printf(tostring(item.title or "Untitled"):sub(1,130),26,y+5,W-52,"left")
        love.graphics.setFont(font.regular(8) or love.graphics.newFont(8))
        love.graphics.setColor(0.55,0.68,0.79,1)
        love.graphics.printf(tostring(item.source or "").."  ·  "..tostring(item.published or ""),26,y+23,W-52,"left")
    end
    if #visible_items==0 then
        love.graphics.setFont(font.bold(13) or love.graphics.newFont(13))
        love.graphics.setColor(0.68,0.77,0.86,1)
        love.graphics.printf(matches_filter and "NO HEADLINES CACHED" or "FILTER NOT CACHED",24,210,W-48,"center")
        love.graphics.setFont(font.regular(10) or love.graphics.newFont(10))
        love.graphics.printf(matches_filter and "Choose a category and press Y to fetch trusted feeds." or "Press Y to refresh this category and language.",24,236,W-48,"center")
    end
    love.graphics.setFont(font.regular(9) or love.graphics.newFont(9))
    love.graphics.setColor(0.56,0.66,0.76,1)
    love.graphics.printf(state.status,20,H-75,W-40,"left")
    chrome.draw_footer({theme=th,hints={
        {icon="dpad",label="Browse"},
        {icon="l1",label="Category"},
        {icon="btn_x",label="Language"},
        {icon="btn_y",label="Refresh"},
        {icon="btn_a",label="Open article"},
        {icon="btn_b",label="Back"},
    },right_text="RSS / ATOM"})
end

return scene
