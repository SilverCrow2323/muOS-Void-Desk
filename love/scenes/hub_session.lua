local bridge = require("core.bridge")
local sm = require("core.scene_manager")
local theme = require("theme.loader")
local input = require("core.input")
local chrome = require("core.chrome")
local font = require("core.font")
local icon = require("core.icon")
local jobs = require("core.jobs")
local effects = require("core.effects")

local scene = {}
local state = {
    sessions = {},
    disk_free_gb = 0,
    ram_pct = 0,
    selected = "xfce",
    detail_open = false,
    detail_action = 1,
    confirm_uninstall = false,
    status = "Desktop environments",
    elapsed = 0,
    enter_t = 0,
    busy = false,
}

local ENV = {
    {
        id = "xfce", name = "XFCE", subtitle = "FULL DESKTOP ENVIRONMENT",
        description = "A complete, modular desktop with window manager, panel, file manager and terminal.",
        detail = "The primary desktop environment. It runs in the isolated Ubuntu ARM64 image and hands the display to Xorg only after Void Desk has released the framebuffer.",
        why = "Best general-purpose environment for multitasking, file management and desktop applications.",
        accent = {0.28, 0.76, 0.94}, accent2 = {0.87, 0.48, 0.26},
        icon = "monitor", style = "graphite / electric blue",
        requirements = "Fresh install: 5 GB free · Wi-Fi · 10–20 minutes",
        role = "PRIMARY",
    },
    {
        id = "icewm", name = "IceWM", subtitle = "LIGHTWEIGHT WINDOW MANAGER",
        description = "A fast, minimal environment with a compact panel and very low memory use.",
        detail = "IceWM is installed inside the existing XFCE image. It shares the same root filesystem and can be selected independently at launch.",
        why = "Best for low memory use, fast navigation and a clean classic desktop.",
        accent = {0.36, 0.72, 0.98}, accent2 = {0.58, 0.84, 1.0},
        icon = "window", style = "cold steel / arctic blue",
        requirements = "Requires XFCE image · small additional download",
        role = "LIGHTWEIGHT",
    },
    {
        id = "lxde", name = "LXDE", subtitle = "LIGHTWEIGHT DESKTOP",
        description = "A traditional desktop shell with panel, Openbox and PCManFM.",
        detail = "LXDE adds a compact desktop shell to the existing XFCE image, without creating a second Ubuntu root filesystem.",
        why = "Best for a familiar desktop layout with modest resource consumption.",
        accent = {0.34, 0.82, 0.58}, accent2 = {0.66, 0.92, 0.48},
        icon = "layout-dashboard", style = "leaf green / soft graphite",
        requirements = "Requires XFCE image · small additional download",
        role = "COMPACT",
    },
}

local function env_by_id(id)
    for _, env in ipairs(ENV) do
        if env.id == id then return env end
    end
    return ENV[1]
end

local function session_state(id)
    for _, item in ipairs(state.sessions) do
        if item.id == id then return item end
    end
    return {id = id, installed = false}
end

local function installed(id)
    return session_state(id).installed == true
end

local function active_operation(id)
    local env = env_by_id(id)
    for _, job in ipairs(jobs.list_active()) do
        if job.status == "running" or job.status == "starting" then
            local expected = {
                ["Install " .. env.name] = true,
                ["Remove " .. env.name] = true,
                ["Check updates for " .. env.name] = true,
            }
            if expected[job.name] then return job end
        end
    end
    return nil
end

local function refresh(silent)
    if not silent then state.status = "Checking desktop environments..." end
    bridge.call("session_list", {}, function(resp)
        if resp.ok then
            state.sessions = resp.sessions or {}
            if not silent then state.status = "Environment catalogue updated" end
        else
            state.status = "Environment scan failed: " .. tostring(resp.error or "unknown error")
        end
    end)
    bridge.call("system_status", {}, function(resp)
        if resp.ok and resp.system then
            local disk = resp.system.disk or {}
            state.disk_free_gb = disk[1] and tonumber(disk[1].free_gb) or 0
            state.ram_pct = tonumber((resp.system.ram or {}).pct) or 0
        end
    end)
end

local function active_actions(env)
    local actions = {}
    local running = active_operation(env.id)
    -- IceWM and LXDE share the XFCE image. Surface its lifecycle instead
    -- of allowing a second base install while that dependency is running.
    if not running and env.id ~= "xfce" then
        running = active_operation("xfce")
    end
    if running then
        actions[#actions + 1] = {id = "view", label = "VIEW PROCESS", color = env.accent}
        actions[#actions + 1] = {id = "back", label = "BACK", color = {0.55,0.64,0.73}}
        return actions
    end
    if env.id ~= "xfce" and not installed("xfce") then
        actions[#actions + 1] = {
            id = "install_base", label = "INSTALL BASE", color = env.accent,
        }
        actions[#actions + 1] = {
            id = "back", label = "BACK", color = {0.55,0.64,0.73},
        }
        return actions
    end
    if installed(env.id) then
        actions[#actions + 1] = {id = "launch", label = "LAUNCH", color = env.accent}
        actions[#actions + 1] = {id = "uninstall", label = "UNINSTALL", color = {1.0,0.39,0.36}}
        actions[#actions + 1] = {id = "updates", label = "CHECK UPDATES", color = {0.97,0.72,0.30}}
    else
        actions[#actions + 1] = {id = "install", label = "INSTALL", color = env.accent}
        actions[#actions + 1] = {id = "updates", label = "CHECK UPDATES", color = {0.97,0.72,0.30}, disabled = true}
    end
    actions[#actions + 1] = {id = "back", label = "BACK", color = {0.55,0.64,0.73}}
    return actions
end

local function set_status(text)
    state.status = tostring(text or "")
end

local function run_action(action)
    local env = env_by_id(state.selected)
    if action.id == "back" then
        state.detail_open = false
        state.confirm_uninstall = false
        return
    end
    if action.disabled then
        set_status("Install this environment before checking for updates.")
        return
    end
    if action.id == "uninstall" then
        state.confirm_uninstall = true
        return
    end
    if action.id == "view" then
        local running = active_operation(env.id)
        if not running and env.id ~= "xfce" then
            running = active_operation("xfce")
        end
        if running then
            jobs.show_job(running.id)
            state.detail_open = false
        end
        return
    end
    if action.id == "install_base" then
        set_status("XFCE base required. Starting the shared image installation...")
        bridge.call("xfce_install", {}, function(resp)
            if resp.ok then
                state.status = resp.note or
                    "XFCE base installation started. Install IceWM/LXDE after it completes."
                refresh(true)
            else
                state.status = "XFCE base install failed: " ..
                    tostring(resp.error or "unknown error")
            end
        end)
        return
    end
    if action.id == "launch" then
        if not installed(env.id) then
            set_status(env.name .. " is not installed.")
            return
        end
        set_status("Preparing " .. env.name .. " session...")
        bridge.call("session_launch", {id = env.id}, function(resp)
            if resp.ok and resp.handoff then
                state.status = resp.note or ("Starting " .. env.name .. "...")
                love.event.quit()
            elseif resp.ok then
                state.status = resp.note or (env.name .. " started")
            else
                state.status = env.name .. ": " .. tostring(resp.error or "launch failed")
            end
        end)
        return
    end
    if action.id == "install" then
        if env.id == "xfce" then
            bridge.call("xfce_install", {}, function(resp)
                if resp.ok then
                    state.status = resp.note or "XFCE installation started"
                    refresh(true)
                else
                    state.status = "Install failed: " .. tostring(resp.error or "unknown error")
                end
            end)
        else
            bridge.call("env_install", {id = env.id}, function(resp)
                if resp.ok then
                    state.status = resp.note or (env.name .. " installation started")
                    refresh(true)
                else
                    state.status = "Install failed: " .. tostring(resp.error or "unknown error")
                end
            end)
        end
        return
    end
    if action.id == "updates" then
        bridge.call("env_update_check", {id = env.id}, function(resp)
            if resp.ok then
                state.status = resp.note or ("Update check started for " .. env.name)
            else
                state.status = "Update check: " .. tostring(resp.error or "unavailable")
            end
        end)
    end
end

local function confirm_uninstall()
    local env = env_by_id(state.selected)
    state.confirm_uninstall = false
    bridge.call("env_uninstall", {id = env.id}, function(resp)
        if resp.ok then
            state.status = resp.note or (env.name .. " removal started")
            refresh(true)
        else
            state.status = "Uninstall failed: " .. tostring(resp.error or "unknown error")
        end
    end)
end

local function open_details(id)
    state.selected = id
    state.detail_open = true
    state.detail_action = 1
    state.confirm_uninstall = false
end

local function palette()
    local th = theme.get()
    return th
end

local function draw_led(x, y, active, accent, t)
    local blink = active and (0.82 + 0.18 * math.sin(t * 3)) or 0.42
    love.graphics.setColor(accent[1], accent[2], accent[3], active and 0.17 or 0.06)
    love.graphics.circle("fill", x, y, 9)
    love.graphics.setColor(active and 0.34 or 0.35,
        active and 0.92 or 0.39, active and 0.58 or 0.44, blink)
    love.graphics.circle("fill", x, y, 4)
end

local function draw_card(env, x, y, w, h, selected, large, t)
    local ready = installed(env.id)
    local running = active_operation(env.id)
    local pulse = 0.5 + 0.5 * math.sin(t * 2.0)
    local accent = env.accent
    local bg = large and {0.045,0.064,0.088} or {0.055,0.071,0.092}
    love.graphics.setColor(bg[1],bg[2],bg[3],0.98)
    love.graphics.rectangle("fill",x,y,w,h,10)
    love.graphics.setColor(accent[1],accent[2],accent[3],selected and (0.82+0.15*pulse) or 0.40)
    love.graphics.setLineWidth(selected and 2.4 or 1.2)
    love.graphics.rectangle("line",x,y,w,h,10)
    love.graphics.setColor(accent[1],accent[2],accent[3],0.08)
    love.graphics.rectangle("fill",x+2,y+2,w-4,large and h*0.42 or h*0.36,8,8)

    local icon_size = large and math.min(76,h*0.28) or 42
    local icon_x = x + (large and 20 or 14)
    local icon_y = y + (large and 22 or 16)
    love.graphics.setColor(accent[1],accent[2],accent[3],0.16)
    love.graphics.circle("fill",icon_x+icon_size/2,icon_y+icon_size/2,icon_size*0.68)
    pcall(icon.draw,env.icon,icon_x,icon_y,icon_size,accent,{alpha=1})

    local title_size = large and 27 or 19
    local title_font = font.bold(title_size) or love.graphics.newFont(title_size)
    love.graphics.setFont(title_font)
    love.graphics.setColor(0.93,0.96,1,1)
    love.graphics.print(env.name,icon_x+icon_size+(large and 20 or 12),icon_y+2)

    local meta_font = font.mono(large and 11 or 9) or love.graphics.newFont(10)
    love.graphics.setFont(meta_font)
    love.graphics.setColor(accent[1],accent[2],accent[3],0.92)
    love.graphics.print(env.subtitle,icon_x+icon_size+(large and 20 or 12),icon_y+title_font:getHeight()+7)

    local led_x = x+w-(large and 28 or 22)
    local led_y = y+(large and 31 or 26)
    draw_led(led_x,led_y,ready or running ~= nil,running and {1.0,0.72,0.25} or accent,t)

    local status_font = font.bold(large and 14 or 11) or love.graphics.newFont(12)
    love.graphics.setFont(status_font)
    love.graphics.setColor(running and 1.0 or (ready and 0.42 or 0.70),running and 0.76 or (ready and 0.90 or 0.73),running and 0.31 or (ready and 0.62 or 0.78),1)
    local requires_base = env.id ~= "xfce" and not installed("xfce")
    local status = running and "OPERATION RUNNING" or
        (ready and "INSTALLED" or (requires_base and "REQUIRES XFCE" or "NOT INSTALLED"))
    love.graphics.print(status,x+(large and 22 or 14),y+(large and 126 or 76))

    love.graphics.setFont(font.regular(large and 13 or 10) or love.graphics.newFont(11))
    love.graphics.setColor(0.62,0.70,0.79,1)
    if large then
        love.graphics.printf(env.description,x+22,y+158,w-44, "left")
        love.graphics.setColor(0.45,0.56,0.67,1)
        love.graphics.print(env.style,x+22,y+h-66)
        love.graphics.setColor(accent[1],accent[2],accent[3],0.95)
        love.graphics.print(ready and "A  OPEN ENVIRONMENT DETAILS" or "A  INSTALLATION DETAILS",x+22,y+h-38)
    else
        local short_description = env.id == "icewm"
            and "Fast, minimal and low-memory."
            or "Traditional lightweight desktop."
        love.graphics.printf(short_description,x+14,y+93,w-28, "left")
        love.graphics.setColor(accent[1],accent[2],accent[3],0.95)
        love.graphics.print("A  VIEW DETAILS",x+14,y+h-20)
    end
    if selected then
        love.graphics.setColor(accent[1],accent[2],accent[3],0.85)
        love.graphics.setLineWidth(2)
        love.graphics.line(x+18,y+h-8,x+math.min(w-18,large and 176 or 110),y+h-8)
    end
end

local function draw_status_bar(th,W,H)
    love.graphics.setColor(th.panel_bg[1],th.panel_bg[2],th.panel_bg[3],0.97)
    love.graphics.rectangle("fill",12,H-83,W-24,25,4)
    love.graphics.setColor(0.36,0.45,0.55,0.55)
    love.graphics.rectangle("line",12,H-83,W-24,25,4)
    love.graphics.setFont(font.regular(11) or love.graphics.newFont(11))
    love.graphics.setColor(th.text[1],th.text[2],th.text[3],0.9)
    love.graphics.print("> "..state.status,22,H-77)
    love.graphics.setColor(0.50,0.61,0.72,1)
    love.graphics.print(string.format("DISK %.1f GB  /  RAM %d%%",
        state.disk_free_gb or 0,state.ram_pct or 0),W-190,H-77)
end

local function draw_details(th,W,H,t)
    local env=env_by_id(state.selected)
    local pw,ph=math.min(W-28,580),math.min(H-34,400)
    local x,y=(W-pw)/2,(H-ph)/2
    local accent=env.accent
    local a=state.enter_t
    love.graphics.setColor(0,0,0,0.77*a)
    love.graphics.rectangle("fill",0,0,W,H)
    love.graphics.setColor(0.035,0.052,0.074,0.99)
    love.graphics.rectangle("fill",x,y,pw,ph,12)
    love.graphics.setColor(accent[1],accent[2],accent[3],0.9)
    love.graphics.setLineWidth(2)
    love.graphics.rectangle("line",x,y,pw,ph,12)
    love.graphics.setColor(accent[1],accent[2],accent[3],0.11)
    love.graphics.rectangle("fill",x+2,y+2,pw-4,88,10,10)

    pcall(icon.draw,env.icon,x+22,y+20,54,accent,{alpha=1})
    love.graphics.setFont(font.bold(26) or love.graphics.newFont(26))
    love.graphics.setColor(0.95,0.97,1,1)
    love.graphics.print(env.name,x+91,y+22)
    love.graphics.setFont(font.mono(10) or love.graphics.newFont(10))
    love.graphics.setColor(accent[1],accent[2],accent[3],1)
    love.graphics.print(env.role.."  /  "..env.subtitle,x+93,y+58)

    local ready=installed(env.id)
    local led = ready and {0.36,0.90,0.60} or {0.66,0.70,0.76}
    draw_led(x+pw-30,y+37,ready,led,t)
    love.graphics.setFont(font.bold(11) or love.graphics.newFont(11))
    love.graphics.setColor(led[1],led[2],led[3],1)
    love.graphics.print(ready and "READY" or "NOT INSTALLED",x+pw-140,y+57)

    love.graphics.setFont(font.regular(13) or love.graphics.newFont(13))
    love.graphics.setColor(0.84,0.89,0.94,1)
    love.graphics.printf(env.detail,x+24,y+112,pw-48,"left")
    love.graphics.setColor(0.55,0.66,0.77,1)
    love.graphics.printf(env.why,x+24,y+165,pw-48,"left")
    love.graphics.setColor(accent[1],accent[2],accent[3],1)
    love.graphics.setFont(font.mono(10) or love.graphics.newFont(10))
    love.graphics.print("REQUIREMENTS  /  "..env.requirements,x+24,y+216)

    if state.confirm_uninstall then
        love.graphics.setColor(0.25,0.055,0.065,0.98)
        love.graphics.rectangle("fill",x+20,y+248,pw-40,64,7)
        love.graphics.setColor(1,0.35,0.34,0.9)
        love.graphics.rectangle("line",x+20,y+248,pw-40,64,7)
        love.graphics.setFont(font.bold(12) or love.graphics.newFont(12))
        love.graphics.setColor(1,0.83,0.82,1)
        love.graphics.printf("REMOVE "..env.name.."?",x+30,y+257,pw-60,"center")
        love.graphics.setFont(font.regular(10) or love.graphics.newFont(10))
        love.graphics.printf("XFCE removal also removes IceWM and LXDE from the shared image. Confirm only if you no longer need any of them.",x+30,y+278,pw-60,"center")
        local yes = state.detail_action == 1
        love.graphics.setColor(yes and 1 or 0.55,yes and 0.32 or 0.60,yes and 0.30 or 0.68,1)
        love.graphics.printf(yes and "[ YES, UNINSTALL ]" or "YES, UNINSTALL",x+28,y+325,pw/2-40,"center")
        love.graphics.setColor(not yes and 0.48 or 0.65,not yes and 0.84 or 0.70,not yes and 0.67 or 0.72,1)
        love.graphics.printf(not yes and "[ KEEP IT ]" or "KEEP IT",x+pw/2,y+325,pw/2-28,"center")
    else
        local actions=active_actions(env)
        local gap=8
        local btn_w=(pw-48-gap*(#actions-1))/#actions
        for i,action in ipairs(actions) do
            local bx=x+24+(i-1)*(btn_w+gap)
            local by=y+258
            local selected=i==state.detail_action
            local col=action.color
            love.graphics.setColor(col[1],col[2],col[3],selected and 0.23 or 0.08)
            love.graphics.rectangle("fill",bx,by,btn_w,44,6)
            love.graphics.setColor(col[1],col[2],col[3],selected and 1 or 0.55)
            love.graphics.setLineWidth(selected and 2 or 1)
            love.graphics.rectangle("line",bx,by,btn_w,44,6)
            love.graphics.setFont(font.bold(10) or love.graphics.newFont(10))
            love.graphics.setColor(action.disabled and 0.46 or 0.91,action.disabled and 0.49 or 0.94,action.disabled and 0.54 or 0.98,1)
            love.graphics.printf(action.label,bx+5,by+16,btn_w-10,"center")
        end
    end

    love.graphics.setFont(font.regular(10) or love.graphics.newFont(10))
    love.graphics.setColor(0.54,0.64,0.74,1)
    love.graphics.print("LEFT/RIGHT  SELECT ACTION     A  CONFIRM     B  BACK",x+24,y+ph-27)
end

function scene.enter(args)
    state.selected="xfce"
    state.detail_open=false
    state.detail_action=1
    state.confirm_uninstall=false
    state.status="Desktop environments"
    state.elapsed=0
    state.enter_t=0
    state.busy=false
    input.clear()
    input.on("press",function(action)
        if state.detail_open then
            if state.confirm_uninstall then
                if action=="left" or action=="right" then
                    state.detail_action=state.detail_action==1 and 2 or 1
                elseif action=="a" then
                    if state.detail_action==1 then confirm_uninstall()
                    else state.confirm_uninstall=false end
                elseif action=="b" then
                    state.confirm_uninstall=false
                end
                return
            end
            local actions=active_actions(env_by_id(state.selected))
            if action=="left" then
                state.detail_action=math.max(1,state.detail_action-1)
            elseif action=="right" then
                state.detail_action=math.min(#actions,state.detail_action+1)
            elseif action=="a" then
                run_action(actions[state.detail_action])
            elseif action=="b" then
                state.detail_open=false
            end
            return
        end

        if action=="left" then
            state.selected=state.selected=="xfce" and "lxde" or
                (state.selected=="icewm" and "xfce" or "icewm")
        elseif action=="right" then
            state.selected=state.selected=="xfce" and "icewm" or
                (state.selected=="icewm" and "lxde" or "xfce")
        elseif action=="up" then
            state.selected=state.selected=="lxde" and "icewm" or "xfce"
        elseif action=="down" then
            state.selected=state.selected=="xfce" and "icewm" or "lxde"
        elseif action=="a" then
            open_details(state.selected)
        elseif action=="b" then
            sm.back()
        end
    end)
    refresh(false)
end

function scene.update(dt)
    state.enter_t=math.min(1,state.enter_t+dt*2.5)
    state.elapsed=state.elapsed+dt
    if state.elapsed>5 then
        state.elapsed=0
        refresh(true)
    end
end

function scene.draw()
    local W,H=love.graphics.getDimensions()
    local th=palette()
    love.graphics.clear(th.bg[1],th.bg[2],th.bg[3],1)
    if th.bg_anim then
        pcall(effects.scanlines,W,H,0.025)
    end
    local profile_name=""
    local cfg=require("core.config")
    profile_name=tostring(cfg.get("profile_name","") or "")
    if profile_name~="" then
        love.graphics.setFont(font.regular(10) or love.graphics.newFont(10))
        love.graphics.setColor(0.55,0.67,0.77,1)
        love.graphics.print("WELCOME BACK, "..profile_name:upper(),18,60)
    end

    chrome.draw_header({
        theme=th,title="Void-DESK",subtitle="START SESSION",
        status_icons={"wifi","bluetooth","battery"},
    })

    local top=profile_name~="" and 84 or 72
    local bottom=H-112
    local content_h=bottom-top
    local left_x=14
    local gap=10
    local left_w=math.floor((W-42)*0.57)
    local right_x=left_x+left_w+gap
    local right_w=W-right_x-14
    draw_card(ENV[1],left_x,top,left_w,content_h,
        state.selected=="xfce",true,state.enter_t)
    local small_h=math.floor((content_h-gap)/2)
    draw_card(ENV[2],right_x,top,right_w,small_h,
        state.selected=="icewm",false,state.enter_t)
    draw_card(ENV[3],right_x,top+small_h+gap,right_w,small_h,
        state.selected=="lxde",false,state.enter_t)

    draw_status_bar(th,W,H)
    chrome.draw_footer({
        theme=th,
        hints={
            {icon="dpad",label="Select environment"},
            {icon="btn_a",label="Details"},
            {icon="btn_b",label="Back"},
            {icon="monitor",label="Tablet (M)"},
        },
        right_text=string.format("FREE %.1f GB",state.disk_free_gb or 0),
    })
    if state.detail_open then draw_details(th,W,H,state.elapsed) end
end

return scene
