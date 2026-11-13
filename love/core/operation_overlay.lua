local jobs = require("core.jobs")
local font = require("core.font")
local overlay = { log_cache = {}, log_time = {} }

local function log_for(job)
    local now = love.timer.getTime()
    local id = tostring(job.id)
    if overlay.log_cache[id] and now-(overlay.log_time[id] or 0)<0.9 then
        return overlay.log_cache[id]
    end
    jobs.get_log(job.id,function(resp)
        if resp.ok then
            overlay.log_cache[id]=resp.lines or {}
            overlay.log_time[id]=love.timer.getTime()
        end
    end)
    return overlay.log_cache[id] or {}
end

local function draw_spinner(cx,cy,r,color,t,mode)
    if mode=="extract" then
        for i=0,7 do
            local a=t*1.7+i*math.pi/4
            local s=0.2+0.8*(0.5+0.5*math.sin(t*4+i))
            love.graphics.setColor(color[1],color[2],color[3],s)
            love.graphics.rectangle("fill",cx+math.cos(a)*r-3,cy+math.sin(a)*r-3,6,6,1)
        end
    elseif mode=="download" then
        love.graphics.setColor(color[1],color[2],color[3],0.24)
        love.graphics.circle("line",cx,cy,r)
        local a=(t*2.8)%(math.pi*2)
        love.graphics.setColor(color[1],color[2],color[3],1)
        love.graphics.circle("fill",cx+math.cos(a)*r,cy+math.sin(a)*r,4)
    elseif mode=="verify" then
        local pulse=0.45+0.55*(0.5+0.5*math.sin(t*3))
        love.graphics.setColor(color[1],color[2],color[3],pulse)
        love.graphics.circle("line",cx,cy,r*pulse)
        love.graphics.setLineWidth(2)
        love.graphics.line(cx-r*0.35,cy,cx-r*0.05,cy+r*0.28,cx+r*0.48,cy-r*0.38)
    else
        for i=0,11 do
            local a=t*3+i*math.pi/6
            local alpha=0.18+0.82*(1-i/12)
            love.graphics.setColor(color[1],color[2],color[3],alpha)
            love.graphics.circle("fill",cx+math.cos(a)*r,cy+math.sin(a)*r,2.1)
        end
    end
end

function overlay.handle_action(action)
    if not jobs.overlay_open then return false end
    if action=="b" or action=="menu" or action=="select" then
        -- Backgrounding only dismisses the modal; the supervised job continues.
        jobs.hide_overlay()
        return true
    elseif action=="up" or action=="down" then
        return true
    end
    return true
end

function overlay.draw()
    if not jobs.overlay_open then return end
    local job=jobs.focused()
    if not job then jobs.overlay_open=false; return end
    local W,H=love.graphics.getDimensions()
    local color=job.color or {0.32,0.76,0.95}
    local px,py,pw,ph=20,34,W-40,H-68
    local t=love.timer.getTime()
    local pct=math.max(0,math.min(100,tonumber(job.progress) or 0))
    local status=tostring(job.status or "running")
    local phase=tostring(job.phase or (status=="running" and "Preparing" or status))
    local mode=tostring(job.animation or job.progress_mode or "loading")
    local title=tostring(job.name or "Operation")
    local description=tostring(job.description or "Void Desk is performing this operation.")
    local reason=tostring(job.reason or "This step is required to complete the selected action.")
    local message=tostring(job.message or "")
    local error_state=status=="error" or job.severity=="error"

    love.graphics.setColor(0,0,0,0.78)
    love.graphics.rectangle("fill",0,0,W,H)
    love.graphics.setColor(0.045,0.058,0.080,0.99)
    love.graphics.rectangle("fill",px,py,pw,ph,10)
    love.graphics.setColor(color[1],color[2],color[3],0.85)
    love.graphics.setLineWidth(2)
    love.graphics.rectangle("line",px,py,pw,ph,10)
    love.graphics.setColor(color[1],color[2],color[3],0.12)
    love.graphics.rectangle("fill",px+2,py+2,pw-4,58,8,8)

    local f_title=font.bold(19) or love.graphics.newFont(18)
    love.graphics.setFont(f_title)
    love.graphics.setColor(0.93,0.96,1,1)
    love.graphics.print(title,px+22,py+15)
    local f_meta=font.regular(10) or love.graphics.newFont(10)
    love.graphics.setFont(f_meta)
    love.graphics.setColor(color[1],color[2],color[3],1)
    love.graphics.print(string.upper(tostring(job.hub or "SYSTEM")).."  /  OPERATION #"..tostring(job.id),px+23,py+40)

    local spinner_x=px+pw-62
    draw_spinner(spinner_x,py+34,18,error_state and {1,0.32,0.30} or color,t,mode)

    love.graphics.setFont(font.regular(12) or love.graphics.newFont(12))
    love.graphics.setColor(0.74,0.81,0.88,1)
    love.graphics.printf(description,px+22,py+82,pw-44,"left")
    love.graphics.setColor(0.53,0.63,0.73,1)
    love.graphics.printf("WHY  /  "..reason,px+22,py+118,pw-44,"left")

    local phase_y=py+167
    love.graphics.setFont(font.bold(13) or love.graphics.newFont(13))
    love.graphics.setColor(error_state and 1 or color[1],error_state and 0.38 or color[2],error_state and 0.35 or color[3],1)
    love.graphics.print(string.upper(phase),px+22,phase_y)
    love.graphics.setFont(font.regular(11) or love.graphics.newFont(11))
    love.graphics.setColor(0.65,0.73,0.81,1)
    love.graphics.print(message~="" and message or (status=="running" and "Working..." or status),px+22,phase_y+22)

    local bx,by,bw,bh=px+22,py+218,pw-44,18
    love.graphics.setColor(0.09,0.12,0.16,1)
    love.graphics.rectangle("fill",bx,by,bw,bh,5)
    if job.indeterminate==true or pct<=0 and status=="running" then
        local segment=bw*0.22
        local offset=(t*130)%(bw+segment)-segment
        love.graphics.setColor(color[1],color[2],color[3],0.95)
        love.graphics.rectangle("fill",bx+offset,by,segment,bh,5)
    elseif pct>0 then
        love.graphics.setColor(color[1],color[2],color[3],0.95)
        love.graphics.rectangle("fill",bx,by,bw*pct/100,bh,5)
    end
    love.graphics.setColor(color[1],color[2],color[3],0.45)
    love.graphics.rectangle("line",bx,by,bw,bh,5)
    love.graphics.setFont(font.bold(13) or love.graphics.newFont(13))
    love.graphics.setColor(0.92,0.95,0.98,1)
    love.graphics.printf(job.indeterminate==true and "WORKING" or string.format("%d%%",pct),
        bx,by+27,bw,"right")

    local log_y=by+52
    local log_h=math.max(32,ph-(log_y-py)-58)
    love.graphics.setColor(0.018,0.027,0.041,1)
    love.graphics.rectangle("fill",px+22,log_y,pw-44,log_h,5)
    love.graphics.setColor(0.20,0.29,0.38,0.9)
    love.graphics.rectangle("line",px+22,log_y,pw-44,log_h,5)
    local lines=log_for(job)
    local f_log=font.mono(10) or love.graphics.newFont(10)
    love.graphics.setFont(f_log)
    local line_h=f_log:getHeight()+3
    local visible=math.max(1,math.floor((log_h-12)/line_h))
    local first=math.max(1,#lines-visible+1)
    for i=first,#lines do
        local line=tostring(lines[i])
        local low=line:lower()
        local lc={0.69,0.78,0.86}
        if low:find("fatal",1,true) or low:find("error",1,true) or low:find("failed",1,true) then
            lc={1,0.42,0.38}
        elseif low:find("completed",1,true) or low:find("success",1,true) or low:find("installed",1,true) then
            lc={0.42,0.88,0.63}
        end
        love.graphics.setColor(lc[1],lc[2],lc[3],1)
        love.graphics.print(line:sub(1,math.max(20,math.floor((pw-58)/f_log:getWidth("M")))),
            px+30,log_y+7+(i-first)*line_h)
    end
    if #lines==0 then
        love.graphics.setColor(0.42,0.52,0.62,1)
        love.graphics.print("Detailed output will appear here as the operation progresses.",
            px+30,log_y+10)
    end

    local footer=job.can_background==false and "B  CLOSE DETAILS" or "B  CONTINUE IN BACKGROUND"
    love.graphics.setFont(font.regular(10) or love.graphics.newFont(10))
    love.graphics.setColor(0.63,0.72,0.81,1)
    love.graphics.print(footer,px+22,py+ph-27)
    love.graphics.setColor(0.40,0.51,0.61,1)
    love.graphics.print("PROCESS REMAINS SUPERVISED  ·  SELECT/M TO REOPEN",
        px+pw-260,py+ph-27)
    love.graphics.setColor(1,1,1,1)
end

return overlay
