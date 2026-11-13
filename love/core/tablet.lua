local bridge = require("core.bridge")
local jobs = require("core.jobs")
local tablet = {
    active = false,
    page = 1,
    scroll = 0,
    slide = 0,
    poll = 0,
    system = {},
    network = {},
    media = {},
    radio = {},
    iptv = {},
}
local pages = {"OVERVIEW", "PROCESSES", "SYSTEM", "NETWORK", "MEDIA", "ACTIVITY"}
local font_cache = {}

local function get_font(size)
    if not font_cache[size] then font_cache[size] = love.graphics.newFont(size) end
    return font_cache[size]
end

local function request_status()
    bridge.call("system_status", {}, function(resp)
        if resp.ok then tablet.system = resp.system or {} end
    end)
    bridge.call("network_status", {}, function(resp)
        if resp.ok then tablet.network = resp.network or {} end
    end)
    bridge.call("media_status", {}, function(resp)
        if resp.ok then tablet.media = resp.media or {} end
    end)
    bridge.call("radio_status", {}, function(resp)
        if resp.ok then tablet.radio = resp.status or {} end
    end)
    bridge.call("iptv_status", {}, function(resp)
        if resp.ok then tablet.iptv = resp.state and resp or resp or {} end
    end)
    jobs.refresh()
end

function tablet.toggle()
    tablet.active = not tablet.active
    tablet.slide = 0
    tablet.scroll = 0
    if tablet.active then
        tablet.page = 1
        tablet.poll = 0
        request_status()
    end
end

function tablet.update(dt)
    if tablet.active then
        tablet.slide = math.min(1, tablet.slide + dt * 5.5)
        tablet.poll = tablet.poll + dt
        if tablet.poll >= 3 then
            tablet.poll = 0
            request_status()
        end
    else
        tablet.slide = math.max(0, tablet.slide - dt * 6)
    end
end

local function change_page(delta)
    tablet.page = ((tablet.page - 1 + delta) % #pages) + 1
    tablet.scroll = 0
end

local function radio_playing()
    local status = tablet.radio or {}
    local state = tostring(status.state or status.status or ""):lower()
    return status.running == true or status.playing == true or state == "playing"
end

local function iptv_playing()
    local state = tostring((tablet.iptv or {}).state or ""):lower()
    return state == "playing" or state == "buffering"
end

local function current_media_label()
    if tablet.media.now_playing then return tostring(tablet.media.now_playing) end
    local radio = tablet.radio or {}
    if radio_playing() then
        return tostring(radio.name or radio.station or radio.title or radio.now_playing or "Void Radio")
    end
    local iptv = tablet.iptv or {}
    if iptv_playing() then
        local channel = iptv.channel
        if type(channel) == "table" then channel = channel.name end
        return tostring(channel or iptv.name or iptv.now_playing or "IPTV")
    end
    return "Nothing is playing"
end

local function stop_all_media()
    bridge.call("media_stop", {}, function(resp)
        if resp.ok then tablet.media.now_playing = nil end
    end)
    bridge.call("radio_action", {action="stop"}, function(resp)
        if resp.ok then tablet.radio = {} end
    end)
    bridge.call("iptv_stop", {}, function(resp)
        if resp.ok then tablet.iptv = {state="idle"} end
    end)
end

local function toggle_pause()
    if tablet.media.now_playing then
        bridge.call("media_action", {action="toggle_pause"}, function(resp)
            if resp.ok then
                tablet.media.paused = resp.data == true
            end
        end)
    elseif radio_playing() then
        bridge.call("radio_action", {action="toggle_pause"}, function(resp)
            if resp.ok then tablet.radio.paused = resp.pause == true end
        end)
    elseif iptv_playing() then
        bridge.call("iptv_action", {action="toggle_pause"}, function(resp)
            if resp.ok then tablet.iptv.paused = resp.data == true end
        end)
    else
        request_status()
    end
end

local function adjust_volume(delta)
    local current = tonumber(tablet.media.volume) or tonumber((tablet.radio or {}).volume) or 40
    local next_volume = math.max(0, math.min(100, current + delta))
    if tablet.media.now_playing then
        bridge.call("media_action", {action="volume", value=next_volume}, function(resp)
            if resp.ok then tablet.media.volume = resp.volume end
        end)
    elseif radio_playing() then
        bridge.call("radio_action", {action="volume", value=next_volume}, function(resp)
            if resp.ok then tablet.radio.volume = resp.volume end
        end)
    elseif iptv_playing() then
        bridge.call("iptv_action", {action="volume", value=next_volume}, function(resp)
            if resp.ok then tablet.media.volume = next_volume end
        end)
    end
end

function tablet.handle_action(action)
    if not tablet.active then return false end
    if action == "b" or action == "menu" then
        tablet.active = false
        return true
    elseif action == "l1" then
        change_page(-1)
        return true
    elseif action == "r1" then
        change_page(1)
        return true
    elseif action == "up" then
        tablet.scroll = math.max(0, tablet.scroll - 1)
        return true
    elseif action == "down" then
        tablet.scroll = tablet.scroll + 1
        return true
    elseif action == "left" or action == "right" then
        if tablet.page == 1 or tablet.page == 5 then
            adjust_volume(action == "right" and 5 or -5)
        end
        return true
    elseif action == "a" then
        if pages[tablet.page] == "PROCESSES" then
            local list = jobs.list_active()
            local job = list[math.min(#list, tablet.scroll + 1)]
            if job then
                jobs.show_job(job.id)
                tablet.active = false
            end
        elseif tablet.page == 1 or tablet.page == 5 then
            toggle_pause()
        else
            request_status()
        end
        return true
    elseif action == "x" and (tablet.page == 1 or tablet.page == 5) then
        stop_all_media()
        return true
    end
    return true
end

local function color_for_count(count)
    if count == 0 then return {0.34, 0.86, 0.62} end
    if count <= 2 then return {0.96, 0.76, 0.28} end
    if count <= 4 then return {1.00, 0.48, 0.22} end
    return {1.00, 0.23, 0.30}
end

local function card(x, y, w, h, title, accent)
    love.graphics.setColor(0.055, 0.075, 0.105, 0.98)
    love.graphics.rectangle("fill", x, y, w, h, 7)
    love.graphics.setColor(accent[1], accent[2], accent[3], 0.55)
    love.graphics.setLineWidth(1)
    love.graphics.rectangle("line", x, y, w, h, 7)
    love.graphics.setColor(accent[1], accent[2], accent[3], 1)
    love.graphics.print(title, x+12, y+9)
end

local function value_line(x, y, w, label, value, accent)
    love.graphics.setColor(0.55, 0.63, 0.72, 1)
    love.graphics.print(label, x, y)
    local f = get_font(13)
    love.graphics.setFont(f)
    local txt = tostring(value or "—")
    local tw = f:getWidth(txt)
    love.graphics.setColor(accent[1], accent[2], accent[3], 1)
    love.graphics.print(txt, x+w-tw, y)
    love.graphics.setFont(get_font(11))
end

local function draw_overview(x, y, w, h, t)
    local list = jobs.list_active()
    local count = jobs.total_running()
    local total, n = 0, 0
    for _, job in ipairs(list) do
        if job.status == "running" or job.status == "starting" then
            total = total + (tonumber(job.progress) or 0)
            n = n + 1
        end
    end
    local avg = n > 0 and total / n or 0
    local accent = color_for_count(count)
    local left_w = math.floor(w*0.48)
    card(x, y, left_w, h, "SYSTEM ACTIVITY", accent)
    local cx, cy = x+left_w*0.5, y+105
    love.graphics.setColor(accent[1], accent[2], accent[3], 0.12)
    love.graphics.circle("fill", cx, cy, 50)
    love.graphics.setColor(accent[1], accent[2], accent[3], 0.95)
    love.graphics.setLineWidth(4)
    love.graphics.circle("line", cx, cy, 36)
    love.graphics.arc("line", "open", cx, cy, 36, -math.pi/2,
        -math.pi/2 + math.pi*2*math.max(0, math.min(1, avg/100)))
    local angle = t*2.4
    love.graphics.setColor(0.76, 0.91, 1, 1)
    love.graphics.circle("fill", cx+math.cos(angle)*36, cy+math.sin(angle)*36, 4)
    local f = get_font(25)
    love.graphics.setFont(f)
    local txt = tostring(count)
    love.graphics.setColor(accent[1], accent[2], accent[3], 1)
    love.graphics.print(txt, cx-f:getWidth(txt)/2, cy-19)
    love.graphics.setFont(get_font(10))
    love.graphics.setColor(0.68, 0.76, 0.84, 1)
    love.graphics.printf(count == 1 and "PROCESS" or "PROCESSES",
        x+8, y+158, left_w-16, "center")
    love.graphics.setColor(0.47, 0.57, 0.67, 1)
    love.graphics.printf(n > 0 and string.format("Combined progress  %.0f%%", avg)
        or "No active operations", x+8, y+h-28, left_w-16, "center")

    local right_x = x+left_w+10
    local right_w = w-left_w-10
    card(right_x, y, right_w, math.floor((h-10)/2), "NOW PLAYING", {0.44,0.73,0.98})
    love.graphics.setColor(0.90,0.93,0.98,1)
    love.graphics.printf(current_media_label(),
        right_x+12, y+42, right_w-24, "left")
    love.graphics.setColor(0.56,0.65,0.74,1)
    love.graphics.print(string.format("Volume  %s%%   %s",
        tostring(tablet.media.volume or (tablet.radio or {}).volume or 0),
        tablet.media.paused and "PAUSED" or (radio_playing() and tablet.radio.paused and "PAUSED" or "PLAYING")), right_x+12, y+72)
    card(right_x, y+math.floor((h-10)/2)+10, right_w,
        math.floor((h-10)/2), "DEVICE SNAPSHOT", {0.40,0.82,0.68})
    local sys = tablet.system or {}
    local ram = sys.ram or {}
    local disk = sys.disk or {}
    value_line(right_x+12, y+math.floor((h-10)/2)+42, right_w-24,
        "RAM", string.format("%s%%", tostring(ram.pct or 0)), {0.40,0.82,0.68})
    value_line(right_x+12, y+math.floor((h-10)/2)+65, right_w-24,
        "STORAGE", disk[1] and string.format("%.1f GB free", disk[1].free_gb or 0)
            or "Unavailable", {0.40,0.82,0.68})
end

local function rows_for_page()
    local rows = {}
    if tablet.page == 2 then
        for _, job in ipairs(jobs.list_active()) do
            rows[#rows+1] = {
                title = job.name or "Background task",
                detail = string.format("%s  ·  %d%%  ·  %s",
                    tostring(job.phase or job.status or "running"),
                    tonumber(job.progress) or 0,
                    tostring(job.hub or "system")),
                color = job.status == "error" and {1,0.35,0.35} or
                    (job.color or {0.4,0.8,0.95}),
                id = job.id,
            }
        end
        if #rows == 0 then rows[1] = {title="No active processes",detail="Operations started from a tool appear here."} end
    elseif tablet.page == 3 then
        local s = tablet.system or {}
        local ram = s.ram or {}
        local disk = s.disk or {}
        rows = {
            {title="Device",detail=tostring(s.model or s.device or s.hostname or "muOS handheld")},
            {title="Kernel",detail=tostring(s.kernel or "Unavailable")},
            {title="Uptime",detail=tostring(s.uptime or s.uptime_s or "Unavailable")},
            {title="CPU",detail=tostring(s.cpu or "Live metrics update in the Monitor hub")},
            {title="Memory",detail=string.format("%s%% used  ·  %s / %s MB",
                tostring(ram.pct or 0),tostring(ram.used_mb or "—"),tostring(ram.total_mb or "—"))},
            {title="Storage",detail=disk[1] and string.format("%.1f GB free of %.1f GB",
                disk[1].free_gb or 0,disk[1].total_gb or 0) or "Unavailable"},
        }
    elseif tablet.page == 4 then
        local n = tablet.network or {}
        local wifi = n.wifi or {}
        local bt = n.bt or {}
        local hot = n.hotspot or {}
        rows = {
            {title="Wi-Fi",detail=(wifi.connected and "Connected · " or "Disconnected · ")..tostring(wifi.ssid or "—")},
            {title="Address",detail=tostring(wifi.ip or "—")},
            {title="Bluetooth",detail=bt.on and "Enabled" or "Disabled"},
            {title="Paired devices",detail=tostring(bt.count or 0)},
            {title="Hotspot",detail=hot.on and ("Active · "..tostring(hot.ssid or "")) or "Inactive"},
            {title="Gateway",detail=tostring((n.info or {}).gateway or "—")},
        }
    elseif tablet.page == 5 then
        rows = {
            {title="Now playing",detail=current_media_label()},
            {title="Volume",detail=tostring(tablet.media.volume or 0).."%"},
            {title="Media library",detail=tostring(tablet.media.library_count or 0).." indexed items"},
            {title="Playback control",detail="A pause/resume  ·  X stop all  ·  LEFT/RIGHT volume"},
        }
    else
        local history = require("core.notifications").items or {}
        for i = #history, math.max(1,#history-19), -1 do
            local entry = history[i]
            rows[#rows+1] = {title=entry.title or "Event",detail=entry.body or "",color=entry.level=="error" and {1,0.35,0.35} or nil}
        end
        if #rows == 0 then rows[1] = {title="No recent activity",detail="System notices and completed operations will appear here."} end
    end
    return rows
end

local function draw_rows(x, y, w, h)
    local rows = rows_for_page()
    local row_h = 54
    local visible = math.max(1, math.floor((h-12)/row_h))
    local max_scroll = math.max(0,#rows-visible)
    tablet.scroll = math.min(tablet.scroll,max_scroll)
    love.graphics.setScissor(x,y,w,h)
    for i=1,visible do
        local idx = tablet.scroll+i
        local row = rows[idx]
        if not row then break end
        local yy = y+(i-1)*row_h
        local selected = tablet.page==2 and i==1
        love.graphics.setColor(selected and 0.11 or 0.07,selected and 0.14 or 0.09,selected and 0.19 or 0.13,0.98)
        love.graphics.rectangle("fill",x+4,yy+2,w-8,row_h-5,5)
        love.graphics.setColor(row.color and row.color[1] or 0.28,row.color and row.color[2] or 0.53,row.color and row.color[3] or 0.68,0.95)
        love.graphics.rectangle("fill",x+4,yy+2,3,row_h-5,2)
        love.graphics.setFont(get_font(13))
        love.graphics.setColor(0.91,0.94,0.98,1)
        love.graphics.print(tostring(row.title or ""):sub(1,72),x+16,yy+8)
        love.graphics.setFont(get_font(10))
        love.graphics.setColor(0.59,0.67,0.75,1)
        love.graphics.print(tostring(row.detail or ""):sub(1,100),x+16,yy+29)
    end
    love.graphics.setScissor()
end

function tablet.draw()
    if tablet.slide <= 0.001 then return end
    local W,H = love.graphics.getDimensions()
    local pw,ph = math.min(W-22,700),math.min(H-26,448)
    local x = (W-pw)/2
    local target_y = (H-ph)/2
    local y = -ph + (target_y+ph)*tablet.slide
    local t = love.timer.getTime()
    local accent = {0.27,0.78,0.94}
    local bezel = {0.12,0.14,0.17}

    love.graphics.setColor(0,0,0,0.65*tablet.slide)
    love.graphics.rectangle("fill",0,0,W,H)
    -- dark graphite chassis
    love.graphics.setColor(bezel[1],bezel[2],bezel[3],1)
    love.graphics.rectangle("fill",x,y,pw,ph,16)
    love.graphics.setColor(0.34,0.39,0.45,1)
    love.graphics.setLineWidth(2)
    love.graphics.rectangle("line",x,y,pw,ph,16)
    love.graphics.setColor(0.035,0.055,0.078,1)
    love.graphics.rectangle("fill",x+9,y+10,pw-18,ph-20,10)
    -- tablet camera / speaker notch
    love.graphics.setColor(0.025,0.035,0.045,1)
    love.graphics.rectangle("fill",x+pw/2-34,y+2,68,7,4)
    love.graphics.setColor(0.18,0.24,0.29,1)
    love.graphics.circle("fill",x+pw/2+23,y+5,2)

    local sx,sy,sw,sh = x+20,y+22,pw-40,ph-44
    love.graphics.setColor(0.018,0.031,0.048,1)
    love.graphics.rectangle("fill",sx,sy,sw,sh,6)
    love.graphics.setColor(accent[1],accent[2],accent[3],0.35)
    love.graphics.rectangle("line",sx,sy,sw,sh,6)
    love.graphics.setFont(get_font(14))
    love.graphics.setColor(0.92,0.96,1,1)
    love.graphics.print("VOID DESK  //  SYSTEM TABLET",sx+13,sy+9)
    love.graphics.setFont(get_font(10))
    love.graphics.setColor(0.5,0.68,0.78,1)
    love.graphics.print(os.date("%H:%M  ·  %d %b"),sx+sw-115,sy+12)

    local tab_y=sy+34
    local tab_w=math.floor((sw-20)/#pages)
    for i,label in ipairs(pages) do
        local tx=sx+10+(i-1)*tab_w
        local active=i==tablet.page
        love.graphics.setColor(active and 0.12 or 0.05,active and 0.18 or 0.08,active and 0.23 or 0.13,1)
        love.graphics.rectangle("fill",tx,tab_y,tab_w-3,27,4)
        if active then
            love.graphics.setColor(accent[1],accent[2],accent[3],1)
            love.graphics.rectangle("fill",tx,tab_y+24,tab_w-3,3,1)
        end
        love.graphics.setFont(get_font(9))
        love.graphics.setColor(active and 0.92 or 0.54,active and 0.96 or 0.64,active and 1 or 0.72,1)
        love.graphics.printf(label,tx+2,tab_y+9,tab_w-7,"center")
    end

    local content_y=tab_y+36
    local content_h=sh-(content_y-sy)-48
    if tablet.page==1 then
        draw_overview(sx+10,content_y,sw-20,content_h,t)
    else
        draw_rows(sx+10,content_y,sw-20,content_h)
        local rows=rows_for_page()
        local visible=math.max(1,math.floor((content_h-12)/54))
        if #rows>visible then
            love.graphics.setFont(get_font(9))
            love.graphics.setColor(0.50,0.62,0.72,1)
            love.graphics.print(string.format("SCROLL  %d-%d / %d",
                tablet.scroll+1,math.min(#rows,tablet.scroll+visible),#rows),
                sx+16,content_y+content_h-11)
        end
    end

    local count=jobs.total_running()
    local hint="M / B CLOSE     L1/R1 PANELS     UP/DOWN SCROLL"
    if tablet.page==2 then hint=hint.."     A DETAILS" end
    if tablet.page==1 or tablet.page==5 then hint=hint.."     A PAUSE     X STOP     LEFT/RIGHT VOLUME" end
    love.graphics.setFont(get_font(9))
    love.graphics.setColor(0.50,0.62,0.72,1)
    love.graphics.print(hint,sx+12,sy+sh-18)
    love.graphics.setColor(1,1,1,1)
end

return tablet
