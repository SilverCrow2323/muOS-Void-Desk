local sm = require("core.scene_manager")
local bridge = require("core.bridge")
local input = require("core.input")
local theme = require("theme.loader")
local chrome = require("core.chrome")
local font = require("core.font")
local nodes = require("core.nodes")

local scene = {}
local state = {
    notes = {},
    selected = 1,
    mode = "list",
    name = "",
    content = "",
    osk = false,
    osk_index = 1,
    loading = false,
    confirm_delete = false,
    status = "Your notes stay in Void Desk's local data folder.",
    scroll = 0,
}

local KEYS = {
    "A","B","C","D","E","F","G","H",
    "I","J","K","L","M","N","O","P",
    "Q","R","S","T","U","V","W","X",
    "Y","Z","0","1","2","3","4","5",
    "6","7","8","9","-","_",".",",",
    "SPACE","NEWLINE","BACK","DONE",
}
local COLS = 8
local font_cache = {}
local function cached_font(size)
    if not font_cache[size] then font_cache[size] = love.graphics.newFont(size) end
    return font_cache[size]
end

local function current_name()
    local item = state.notes[state.selected]
    return item and item.name or nil
end

local function refresh()
    state.loading = true
    bridge.call("notes_list", {}, function(resp)
        state.loading = false
        if resp.ok then
            state.notes = resp.notes or {}
            state.selected = math.max(1, math.min(state.selected, math.max(1,#state.notes)))
            state.status = string.format("%d notes stored locally", #state.notes)
        else
            state.status = "Notes unavailable: " .. tostring(resp.error or "unknown error")
        end
    end)
end

local function save_note(return_to_list)
    if state.loading then return end
    state.loading = true
    bridge.call("notes_save", {name=state.name,content=state.content}, function(resp)
        state.loading = false
        if resp.ok then
            state.name = resp.name
            state.status = "Saved " .. resp.name
            if return_to_list then
                state.mode = "list"
                state.osk = false
                love.keyboard.setTextInput(false)
                refresh()
            end
        else
            state.status = "Save failed: " .. tostring(resp.error or "unknown error")
        end
    end)
end

local function new_note()
    local stamp = os.date("%Y%m%d-%H%M%S")
    state.name = string.format("Note-%s-%03d.txt", stamp, math.floor((os.clock()*1000)%1000))
    state.content = ""
    state.mode = "edit"
    state.osk = false
    state.scroll = 0
    state.status = "New note · type with a keyboard or press R1 for the on-screen keyboard"
    love.keyboard.setTextInput(true)
end

local function open_note()
    local name = current_name()
    if not name or state.loading then return end
    state.loading = true
    bridge.call("notes_read", {name=name}, function(resp)
        state.loading = false
        if resp.ok then
            state.name = resp.name
            state.content = resp.content or ""
            state.mode = "edit"
            state.osk = false
            state.scroll = 0
            state.status = "Editing " .. resp.name
            love.keyboard.setTextInput(true)
        else
            state.status = "Open failed: " .. tostring(resp.error or "unknown error")
        end
    end)
end

local function delete_note()
    local name = current_name()
    if not name or state.loading then return end
    state.loading = true
    bridge.call("notes_delete", {name=name}, function(resp)
        state.loading = false
        state.confirm_delete = false
        if resp.ok then
            state.status = "Deleted " .. name
            state.selected = math.max(1,state.selected-1)
            refresh()
        else
            state.status = "Delete failed: " .. tostring(resp.error or "unknown error")
        end
    end)
end

local function add_key(key)
    if key == "SPACE" then
        state.content = state.content .. " "
    elseif key == "NEWLINE" then
        state.content = state.content .. "\n"
    elseif key == "BACK" then
        if utf8 and utf8.offset then
            local position = utf8.offset(state.content, -1)
            if position then state.content = state.content:sub(1, position-1) end
        else
            state.content = state.content:sub(1,-2)
        end
    elseif key == "DONE" then
        state.osk = false
        return
    else
        state.content = state.content .. key:lower()
    end
    if #state.content > 32768 then
        state.content = state.content:sub(1,32768)
        state.status = "Note limit reached (32 KB)"
    end
end

function scene.textinput(text)
    if state.mode ~= "edit" or state.osk then return end
    if #state.content + #text <= 32768 then
        state.content = state.content .. text
    else
        state.status = "Note limit reached (32 KB)"
    end
end

local function handle_edit(action)
    if state.osk then
        local row = math.floor((state.osk_index-1)/COLS)
        local col = (state.osk_index-1)%COLS
        if action=="left" then col=(col-1)%COLS
        elseif action=="right" then col=(col+1)%COLS
        elseif action=="up" then row=math.max(0,row-1)
        elseif action=="down" then row=math.min(math.ceil(#KEYS/COLS)-1,row+1)
        elseif action=="a" then
            local key=KEYS[state.osk_index]
            if key then add_key(key) end
        elseif action=="b" then
            state.osk=false
            return
        end
        state.osk_index=math.max(1,math.min(#KEYS,row*COLS+col+1))
        return
    end

    if action=="r1" then
        state.osk=true
    elseif action=="a" then
        state.content=state.content.."\n"
    elseif action=="x" then
        state.content=state.content:sub(1,-2)
    elseif action=="start" then
        save_note(true)
    elseif action=="b" then
        save_note(true)
    end
end

function scene.enter(args)
    state.mode="list"
    state.selected=1
    state.confirm_delete=false
    state.loading=false
    state.osk=false
    state.status="Your notes stay in Void Desk's local data folder."
    input.clear()
    input.on("press",function(action)
        if state.mode=="edit" then
            handle_edit(action)
            return
        end
        if state.confirm_delete then
            if action=="a" then delete_note()
            elseif action=="b" then state.confirm_delete=false end
            return
        end
        if action=="up" then
            state.selected=math.max(1,state.selected-1)
        elseif action=="down" then
            state.selected=math.min(math.max(1,#state.notes),state.selected+1)
        elseif action=="a" then
            open_note()
        elseif action=="y" then
            new_note()
        elseif action=="x" and current_name() then
            state.confirm_delete=true
        elseif action=="r1" then
            refresh()
        elseif action=="b" then
            sm.back()
        end
    end)
    refresh()
end

function scene.leave()
    love.keyboard.setTextInput(false)
end

function scene.draw()
    local W,H=love.graphics.getDimensions()
    local th=theme.get()
    local accent=nodes.color_for(4)
    love.graphics.clear(th.bg[1],th.bg[2],th.bg[3],1)
    chrome.draw_header({theme=th,title="Void-DESK",subtitle="NOTES",status_icons={"file-text","battery"}})

    local x,y,w,h=12,76,W-24,H-148
    love.graphics.setColor(0.045,0.060,0.082,0.98)
    love.graphics.rectangle("fill",x,y,w,h,8)
    love.graphics.setColor(accent[1],accent[2],accent[3],0.48)
    love.graphics.rectangle("line",x,y,w,h,8)

    if state.mode=="list" then
        love.graphics.setFont(font.bold(17) or cached_font(17))
        love.graphics.setColor(0.92,0.96,1,1)
        love.graphics.print("LOCAL NOTEBOOK",x+16,y+12)
        love.graphics.setFont(font.regular(10) or cached_font(10))
        love.graphics.setColor(0.51,0.64,0.76,1)
        love.graphics.print("PRIVATE BY DEFAULT  /  STORED IN data/notes",x+17,y+37)

        local row_y=y+62
        local row_h=48
        local visible=math.max(1,math.floor((h-116)/row_h))
        local first=math.max(1,math.min(state.selected-visible+1,math.max(1,#state.notes-visible+1)))
        for i=first,math.min(#state.notes,first+visible-1) do
            local row=state.notes[i]
            local yy=row_y+(i-first)*row_h
            local selected=i==state.selected
            love.graphics.setColor(selected and 0.12 or 0.07,selected and 0.16 or 0.09,selected and 0.21 or 0.13,1)
            love.graphics.rectangle("fill",x+12,yy,w-24,row_h-4,5)
            love.graphics.setColor(selected and accent[1] or 0.25,selected and accent[2] or 0.36,selected and accent[3] or 0.46,selected and 0.95 or 0.55)
            love.graphics.rectangle("line",x+12,yy,w-24,row_h-4,5)
            love.graphics.setFont(font.bold(12) or cached_font(12))
            love.graphics.setColor(0.91,0.95,1,1)
            love.graphics.print(tostring(row.name or "Untitled"),x+22,yy+6)
            love.graphics.setFont(font.regular(9) or cached_font(9))
            love.graphics.setColor(0.57,0.67,0.77,1)
            love.graphics.print(tostring(row.preview or ""):sub(1,80),x+22,yy+26)
        end
        if #state.notes==0 then
            love.graphics.setFont(font.regular(13) or cached_font(13))
            love.graphics.setColor(0.59,0.69,0.79,1)
            love.graphics.printf("Your notebook is empty.\nCreate a note with Y.",x+24,y+150,w-48,"center")
        end
        if state.confirm_delete then
            love.graphics.setColor(0.22,0.045,0.06,0.98)
            love.graphics.rectangle("fill",x+36,H-120,w-72,42,6)
            love.graphics.setColor(1,0.4,0.38,1)
            love.graphics.rectangle("line",x+36,H-120,w-72,42,6)
            love.graphics.setFont(font.bold(11) or cached_font(11))
            love.graphics.setColor(1,0.85,0.84,1)
            love.graphics.printf("DELETE "..tostring(current_name() or "NOTE").."?  A CONFIRM  /  B CANCEL",x+44,H-107,w-88,"center")
        end
    else
        love.graphics.setFont(font.bold(15) or cached_font(15))
        love.graphics.setColor(0.92,0.96,1,1)
        love.graphics.print(state.name,x+16,y+10)
        love.graphics.setFont(font.regular(10) or cached_font(10))
        love.graphics.setColor(0.54,0.66,0.77,1)
        love.graphics.print(string.format("%d / 32768 BYTES",#state.content),x+17,y+34)

        local editor_y=y+56
        local editor_h=h-72
        love.graphics.setColor(0.018,0.028,0.043,1)
        love.graphics.rectangle("fill",x+12,editor_y,w-24,editor_h,4)
        love.graphics.setScissor(x+18,editor_y+8,w-36,editor_h-16)
        love.graphics.setFont(font.mono(11) or cached_font(11))
        love.graphics.setColor(0.85,0.91,0.97,1)
        local max_lines=math.max(1,math.floor((editor_h-20)/15))
        local lines={}
        for line in (state.content.."\n"):gmatch("(.-)\n") do lines[#lines+1]=line end
        local start=math.max(1,#lines-max_lines+1)
        for i=start,#lines do
            love.graphics.print(lines[i],x+20,editor_y+8+(i-start)*15)
        end
        love.graphics.setScissor()
        if state.osk then
            local kb_y=H-190
            love.graphics.setColor(0.035,0.047,0.065,0.98)
            love.graphics.rectangle("fill",12,kb_y,W-24,132,7)
            local cell_w=(W-52)/COLS
            for i,key in ipairs(KEYS) do
                local row=math.floor((i-1)/COLS)
                local col=(i-1)%COLS
                local bx=22+col*cell_w
                local by=kb_y+8+row*21
                local selected=i==state.osk_index
                love.graphics.setColor(selected and accent[1]*0.32 or 0.08,selected and accent[2]*0.32 or 0.10,selected and accent[3]*0.32 or 0.14,1)
                love.graphics.rectangle("fill",bx,by,cell_w-3,18,3)
                love.graphics.setColor(selected and accent[1] or 0.29,selected and accent[2] or 0.39,selected and accent[3] or 0.50,1)
                love.graphics.rectangle("line",bx,by,cell_w-3,18,3)
                love.graphics.setFont(font.bold(8) or cached_font(8))
                love.graphics.setColor(0.91,0.95,1,1)
                love.graphics.printf(key,bx+1,by+5,cell_w-5,"center")
            end
        end
    end

    if not state.osk then
        love.graphics.setFont(font.regular(10) or cached_font(10))
        love.graphics.setColor(0.54,0.65,0.75,1)
        love.graphics.printf(state.status,x+14,H-103,w-28,"left")
    end
    chrome.draw_footer({
        theme=th,
        hints=state.mode=="list" and {
            {icon="dpad",label="Select"},
            {icon="btn_a",label="Open"},
            {icon="btn_y",label="New"},
            {icon="btn_x",label="Delete"},
            {icon="btn_b",label="Back"},
        } or {
            {icon="r1",label="Keyboard"},
            {icon="dpad",label="Select key"},
            {icon="btn_a",label="Newline / Type"},
            {icon="btn_x",label="Backspace"},
            {icon="btn_start",label="Save"},
        },
        right_text="32 KB MAX",
    })
end

return scene
