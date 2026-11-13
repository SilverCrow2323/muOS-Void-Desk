local sm = require("core.scene_manager")
local bridge = require("core.bridge")
local input = require("core.input")
local theme = require("theme.loader")
local chrome = require("core.chrome")
local font = require("core.font")
local nodes = require("core.nodes")
local jobs = require("core.jobs")
local config = require("core.config")

local scene = {}
local state = {
    city = "", city_mode = false, osk = false, osk_index = 1,
    data = nil, status = "Load a city forecast.", job_id = nil, loading = false,
}
local KEYS = {
    "A","B","C","D","E","F","G","H",
    "I","J","K","L","M","N","O","P",
    "Q","R","S","T","U","V","W","X",
    "Y","Z","SPACE","BACK","DONE",
}
local COLS = 8
local cache_fonts = {}
local function cached_font(size)
    if not cache_fonts[size] then cache_fonts[size] = love.graphics.newFont(size) end
    return cache_fonts[size]
end

local function weather_label(code)
    local labels = {
        [0]="Clear sky",[1]="Mainly clear",[2]="Partly cloudy",[3]="Overcast",
        [45]="Fog",[48]="Rime fog",[51]="Light drizzle",[53]="Drizzle",
        [55]="Dense drizzle",[56]="Freezing drizzle",[57]="Freezing drizzle",
        [61]="Light rain",[63]="Rain",[65]="Heavy rain",[66]="Freezing rain",
        [67]="Heavy freezing rain",[71]="Light snow",[73]="Snow",[75]="Heavy snow",
        [77]="Snow grains",[80]="Rain showers",[81]="Showers",[82]="Heavy showers",
        [85]="Snow showers",[86]="Heavy snow showers",[95]="Thunderstorm",
        [96]="Thunderstorm / hail",[99]="Thunderstorm / heavy hail",
    }
    return labels[tonumber(code) or -1] or "Unknown conditions"
end

local function refresh_cache()
    if state.loading then return end
    state.loading = true
    bridge.call("weather_cache", {}, function(resp)
        state.loading = false
        if resp.ok and resp.cached then
            state.data = resp
            state.city = resp.city or state.city
            state.status = "Forecast updated " .. tostring(resp.updated or "")
        elseif resp.ok then
            state.status = "No cached forecast · press Y to choose a city."
        else
            state.status = "Weather cache: " .. tostring(resp.error or "unavailable")
        end
    end)
end

local function request_forecast()
    local city = state.city:gsub("^%s+",""):gsub("%s+$","")
    if city == "" then
        state.status = "Enter a city name first."
        return
    end
    if state.job_id then
        local current = jobs.active[tostring(state.job_id)]
        if current and (current.status=="running" or current.status=="starting") then
            jobs.show_job(state.job_id)
            return
        end
    end
    state.status = "Preparing forecast for " .. city .. "..."
    config.set("weather_city", city)
    state.city_mode = false
    state.osk = false
    love.keyboard.setTextInput(false)
    bridge.call("job_start", {
        service_task = "weather_refresh",
        city = city,
        name = "Weather · " .. city,
        hub = "toolbox",
        description = "Resolve the city and fetch current conditions plus a seven-day forecast.",
        reason = "Weather information is fetched only when requested and cached locally for the next visit.",
        icon = "cloud-sun",
        animation = "download",
        can_background = true,
    }, function(resp)
        if resp.ok and resp.job then
            state.job_id = tostring(resp.job.id)
            state.status = "Fetching " .. city .. " forecast..."
        else
            state.status = "Weather unavailable: " .. tostring(resp.error or "unknown error")
        end
    end)
end

local function type_key(key)
    if key == "SPACE" then
        state.city = state.city .. " "
    elseif key == "BACK" then
        if utf8 and utf8.offset then
            local pos = utf8.offset(state.city, -1)
            if pos then state.city = state.city:sub(1,pos-1) end
        else
            state.city = state.city:sub(1,-2)
        end
    elseif key == "DONE" then
        state.osk = false
        state.city_mode = false
        love.keyboard.setTextInput(false)
    else
        state.city = state.city .. key:lower()
    end
    if #state.city > 80 then state.city = state.city:sub(1,80) end
end

function scene.textinput(value)
    if not state.city_mode or state.osk then return end
    if #state.city + #value <= 80 then state.city = state.city .. value end
end

local function handle_keyboard(action)
    local row = math.floor((state.osk_index-1)/COLS)
    local col = (state.osk_index-1)%COLS
    local rows = math.ceil(#KEYS/COLS)
    if action=="left" then col=(col-1)%COLS
    elseif action=="right" then col=(col+1)%COLS
    elseif action=="up" then row=math.max(0,row-1)
    elseif action=="down" then row=math.min(rows-1,row+1)
    elseif action=="a" then
        local key=KEYS[state.osk_index]
        if key then
            type_key(key)
            if key=="DONE" then return end
        end
    elseif action=="b" then
        state.osk=false
        state.city_mode=false
        love.keyboard.setTextInput(false)
        return
    end
    state.osk_index=math.max(1,math.min(#KEYS,row*COLS+col+1))
end

function scene.enter()
    input.clear()
    state.city = tostring(config.get("weather_city", state.city) or state.city)
    state.city_mode=false
    state.osk=false
    state.job_id=nil
    state.status="Loading saved forecast..."
    refresh_cache()
    input.on("press",function(action)
        if state.osk then
            handle_keyboard(action)
            return
        end
        if state.city_mode then
            if action=="r1" then
                state.osk=true
                state.osk_index=1
            elseif action=="start" or action=="a" then
                request_forecast()
            elseif action=="x" then
                state.city=""
            elseif action=="b" then
                state.city_mode=false
                love.keyboard.setTextInput(false)
            end
            return
        end
        if action=="y" then
            state.city_mode=true
            state.city=""
            love.keyboard.setTextInput(true)
        elseif action=="a" or action=="start" then
            request_forecast()
        elseif action=="r1" then
            refresh_cache()
        elseif action=="b" or action=="menu" then
            sm.back()
        end
    end)
end

function scene.leave()
    love.keyboard.setTextInput(false)
end

function scene.update(dt)
    scene._poll=(scene._poll or 0)+dt
    if scene._poll>=0.7 then
        scene._poll=0
        if state.job_id then
            local job=jobs.active[tostring(state.job_id)]
            if job and (job.status=="done" or job.status=="error") then
                state.job_id=nil
                state.status=job.status=="done" and "Forecast ready." or
                    ("Weather request failed · "..tostring(job.message or "see process log"))
                refresh_cache()
            end
        end
    end
end

function scene.draw()
    local W,H=love.graphics.getDimensions()
    local th=theme.get()
    local accent=nodes.color_for(6)
    local data=state.data or {}
    local current=data.current or {}
    love.graphics.clear(th.bg[1],th.bg[2],th.bg[3],1)
    chrome.draw_header({theme=th,title="VOID-DESK",subtitle="ATMOSPHERE / WEATHER",status_icons={"cloud-sun","wifi","battery"}})

    love.graphics.setColor(0.045,0.06,0.085,0.98)
    love.graphics.rectangle("fill",12,68,W-24,48,7)
    love.graphics.setColor(accent[1],accent[2],accent[3],0.72)
    love.graphics.rectangle("line",12,68,W-24,48,7)
    love.graphics.setFont(cached_font(12))
    love.graphics.setColor(0.93,0.96,1,1)
    local location_label = state.city ~= "" and state.city:upper() or "SELECT A CITY"
    love.graphics.print("LOCATION  /  "..location_label,24,77)
    love.graphics.setFont(cached_font(9))
    love.graphics.setColor(0.55,0.68,0.8,1)
    love.graphics.print(state.city_mode and "TYPE CITY · R1 ON-SCREEN KEYS · START SEARCH" or "Y CHANGE CITY  ·  A UPDATE  ·  R1 RELOAD CACHE",24,96)

    love.graphics.setColor(0.05,0.075,0.105,0.98)
    love.graphics.rectangle("fill",12,124,W-24,108,8)
    love.graphics.setColor(accent[1],accent[2],accent[3],0.62)
    love.graphics.rectangle("line",12,124,W-24,108,8)
    love.graphics.setFont(cached_font(34))
    love.graphics.setColor(0.96,0.98,1,1)
    love.graphics.print(current.temperature_2m and (tostring(math.floor(current.temperature_2m+0.5)).."°") or "--°",26,136)
    love.graphics.setFont(cached_font(12))
    love.graphics.setColor(0.72,0.82,0.91,1)
    love.graphics.print(weather_label(current.weather_code),116,146)
    love.graphics.setFont(cached_font(9))
    love.graphics.setColor(0.56,0.68,0.79,1)
    love.graphics.print(tostring(data.city or "No forecast")..(data.country and (", "..data.country) or ""),116,166)
    love.graphics.print("FEELS "..tostring(current.apparent_temperature or "--").."°",116,186)
    love.graphics.print("HUMIDITY "..tostring(current.relative_humidity_2m or "--").."%",116,202)
    love.graphics.print("WIND "..tostring(current.wind_speed_10m or "--").." km/h",W*0.60,186)
    love.graphics.print("RAIN "..tostring(current.precipitation or "--").." mm",W*0.60,202)

    love.graphics.setFont(cached_font(11))
    love.graphics.setColor(0.88,0.93,0.98,1)
    love.graphics.print("SEVEN-DAY OUTLOOK",20,244)
    local days=data.days or {}
    local row_y=264
    for i=1,math.min(#days,7) do
        local d=days[i]
        local y=row_y+(i-1)*19
        love.graphics.setColor(0.055,0.08,0.11,0.94)
        love.graphics.rectangle("fill",16,y,W-32,17,4)
        love.graphics.setFont(cached_font(9))
        love.graphics.setColor(0.76,0.84,0.91,1)
        love.graphics.print(tostring(d.date or "--"),24,y+4)
        love.graphics.setColor(0.58,0.7,0.81,1)
        love.graphics.print(weather_label(d.code),W*0.29,y+4)
        love.graphics.setColor(0.94,0.96,1,1)
        love.graphics.printf(tostring(d.high or "--").."° / "..tostring(d.low or "--").."°",W*0.70,y+4,W*0.14,"right")
        love.graphics.setColor(0.48,0.69,0.87,1)
        love.graphics.printf(tostring(d.rain_probability or "--").."%",W*0.86,y+4,W*0.10,"right")
    end
    if #days==0 then
        love.graphics.setFont(cached_font(11))
        love.graphics.setColor(0.6,0.7,0.8,1)
        love.graphics.printf("No forecast cached. Choose a city and press A.",20,302,W-40,"center")
    end

    if state.osk then
        local kb_y=H-155
        love.graphics.setColor(0.03,0.045,0.065,0.99)
        love.graphics.rectangle("fill",12,kb_y,W-24,118,7)
        local cell_w=(W-52)/COLS
        for i,key in ipairs(KEYS) do
            local r=math.floor((i-1)/COLS)
            local col=(i-1)%COLS
            local x=22+col*cell_w
            local y=kb_y+7+r*26
            local selected=i==state.osk_index
            love.graphics.setColor(selected and accent[1]*0.36 or 0.08,selected and accent[2]*0.36 or 0.10,selected and accent[3]*0.36 or 0.14,1)
            love.graphics.rectangle("fill",x,y,cell_w-3,22,3)
            love.graphics.setColor(selected and accent[1] or 0.29,selected and accent[2] or 0.39,selected and accent[3] or 0.5,1)
            love.graphics.rectangle("line",x,y,cell_w-3,22,3)
            love.graphics.setFont(cached_font(8))
            love.graphics.setColor(0.91,0.95,1,1)
            love.graphics.printf(key,x+1,y+7,cell_w-5,"center")
        end
    end

    love.graphics.setFont(cached_font(9))
    love.graphics.setColor(0.56,0.67,0.77,1)
    love.graphics.printf(state.status,20,H-60,W-40,"left")
    chrome.draw_footer({theme=th,hints={
        {icon="dpad",label="Navigate"},
        {icon="btn_y",label="Change city"},
        {icon="btn_a",label="Refresh"},
        {icon="r1",label="On-screen keys"},
        {icon="btn_b",label="Back"},
    }})
end

return scene
