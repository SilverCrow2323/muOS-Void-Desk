local sm = require("core.scene_manager")
local bridge = require("core.bridge")
local input = require("core.input")
local theme = require("theme.loader")
local chrome = require("core.chrome")
local font = require("core.font")
local nodes = require("core.nodes")

local scene = {}
local state = {
    mode = "list", files = {}, selected = 1, first = 1,
    name = "", lines = {""}, cursor_line = 1, cursor_col = 1,
    preferred_col = 1, first_line = 1,
    osk = false, osk_index = 1, lower = false,
    loading = false, dirty = false, confirm_delete = false,
    status = "Local workspace · files stay inside data/Texts",
}
local ROW_H = 40
local MAX_BYTES = 128 * 1024
local KEY_ROWS = {
    {"Q","W","E","R","T","Y","U","I"},
    {"O","P","A","S","D","F","G","H"},
    {"J","K","L","Z","X","C","V","B"},
    {"N","M","1","2","3","4","5","6"},
    {"7","8","9","0",".",",","!","?"},
    {"-","_",":",";","(",")","/","@"},
    {"SPACE","NEWLINE","BACK","DONE"},
}
local font_cache = {}

local function cached_font(size)
    if not font_cache[size] then font_cache[size] = love.graphics.newFont(size) end
    return font_cache[size]
end

local function selected_file()
    local item = state.files[state.selected]
    return item and item.name or nil
end

local function text_size()
    local size = 0
    for i, line in ipairs(state.lines) do
        size = size + #line
        if i < #state.lines then size = size + 1 end
    end
    return size
end

local function line_text()
    return table.concat(state.lines, "\n")
end

local function utf8_next(value, index)
    if index > #value then return #value + 1 end
    local byte = value:byte(index)
    local width = (byte < 0x80 and 1)
        or (byte < 0xE0 and 2)
        or (byte < 0xF0 and 3) or 4
    return math.min(#value + 1, index + width)
end

local function utf8_prev(value, index)
    local pos = math.max(1, index - 1)
    while pos > 1 do
        local byte = value:byte(pos)
        if not byte or byte < 0x80 or byte >= 0xC0 then break end
        pos = pos - 1
    end
    return pos
end

local function utf8_count(value)
    local count, pos = 0, 1
    while pos <= #value do
        pos = utf8_next(value, pos)
        count = count + 1
    end
    return count
end

local function byte_after_chars(value, count)
    local pos = 1
    for _ = 1, count do
        if pos > #value then return #value + 1 end
        pos = utf8_next(value, pos)
    end
    return pos
end

local function cursor_column()
    return utf8_count(state.lines[state.cursor_line]:sub(1, state.cursor_col - 1)) + 1
end

local function clamp_cursor()
    state.cursor_line = math.max(1, math.min(#state.lines, state.cursor_line))
    state.cursor_col = math.max(1, math.min(#state.lines[state.cursor_line] + 1,
        state.cursor_col))
    state.preferred_col = cursor_column()
end

local function ensure_cursor_visible()
    local visible = 12
    if state.cursor_line < state.first_line then
        state.first_line = state.cursor_line
    elseif state.cursor_line >= state.first_line + visible then
        state.first_line = state.cursor_line - visible + 1
    end
    state.first_line = math.max(1, math.min(state.first_line,
        math.max(1, #state.lines - visible + 1)))
end

local function refresh_list()
    if state.loading then return end
    state.loading = true
    bridge.call("text_list", {}, function(resp)
        state.loading = false
        if resp.ok then
            state.files = resp.files or {}
            state.selected = math.max(1, math.min(state.selected,
                math.max(1, #state.files)))
            state.status = string.format("%d text files · data/Texts", #state.files)
        else
            state.status = "File list unavailable: " .. tostring(resp.error or "unknown error")
        end
    end)
end

local function set_content(value)
    state.lines = {}
    value = tostring(value or "")
    for line in (value .. "\n"):gmatch("(.-)\n") do
        state.lines[#state.lines + 1] = line
    end
    if #state.lines == 0 then state.lines = {""} end
    state.cursor_line = #state.lines
    state.cursor_col = #state.lines[state.cursor_line] + 1
    clamp_cursor()
    state.first_line = math.max(1, #state.lines - 11)
end

local function save_file(return_to_list)
    if state.loading then return end
    if state.name == "" then
        state.status = "Enter a filename before saving."
        return
    end
    local content = line_text()
    if #content > MAX_BYTES then
        state.status = "Document exceeds the 128 KB editor limit."
        return
    end
    state.loading = true
    bridge.call("text_save", {name=state.name,content=content}, function(resp)
        state.loading = false
        if resp.ok then
            state.name = resp.name
            state.dirty = false
            state.status = "Saved " .. resp.name
            if return_to_list then
                state.mode = "list"
                state.osk = false
                love.keyboard.setTextInput(false)
                refresh_list()
            end
        else
            state.status = "Save failed: " .. tostring(resp.error or "unknown error")
        end
    end)
end

local function open_file()
    local name = selected_file()
    if not name or state.loading then return end
    state.loading = true
    bridge.call("text_read", {name=name}, function(resp)
        state.loading = false
        if resp.ok then
            state.mode = "edit"
            state.name = resp.name
            set_content(resp.content or "")
            state.dirty = false
            state.osk = false
            state.status = "Editing " .. resp.name
            love.keyboard.setTextInput(true)
        else
            state.status = "Open failed: " .. tostring(resp.error or "unknown error")
        end
    end)
end

local function new_file()
    local stamp = os.date("%Y%m%d-%H%M%S")
    local suffix = math.floor((os.clock() * 1000) % 1000)
    state.name = string.format("Untitled-%s-%03d.txt", stamp, suffix)
    state.lines = {""}
    state.cursor_line, state.cursor_col, state.preferred_col = 1, 1, 1
    state.first_line = 1
    state.mode = "edit"
    state.dirty = true
    state.osk = false
    state.status = "New text file · save with START or B"
    love.keyboard.setTextInput(true)
end

local function delete_file()
    local name = selected_file()
    if not name or state.loading then return end
    state.loading = true
    bridge.call("text_delete", {name=name}, function(resp)
        state.loading = false
        state.confirm_delete = false
        if resp.ok then
            state.selected = math.max(1, state.selected - 1)
            state.status = "Deleted " .. name
            refresh_list()
        else
            state.status = "Delete failed: " .. tostring(resp.error or "unknown error")
        end
    end)
end

local function insert_text(value)
    if #line_text() + #value > MAX_BYTES then
        state.status = "Document limit reached (128 KB)"
        return
    end
    local parts = {}
    for part in (value .. "\n"):gmatch("(.-)\n") do
        parts[#parts + 1] = part
    end
    local line = state.lines[state.cursor_line]
    local before = line:sub(1, state.cursor_col - 1)
    local after = line:sub(state.cursor_col)
    if #parts == 1 then
        state.lines[state.cursor_line] = before .. value .. after
        state.cursor_col = state.cursor_col + #value
    else
        state.lines[state.cursor_line] = before .. parts[1]
        for i = 2, #parts - 1 do
            table.insert(state.lines, state.cursor_line + i - 1, parts[i])
        end
        table.insert(state.lines, state.cursor_line + #parts - 1,
            parts[#parts] .. after)
        state.cursor_line = state.cursor_line + #parts - 1
        state.cursor_col = #parts[#parts] + 1
    end
    state.dirty = true
    clamp_cursor()
    ensure_cursor_visible()
end

local function backspace()
    local line = state.lines[state.cursor_line]
    if state.cursor_col > 1 then
        local previous = utf8_prev(line, state.cursor_col)
        state.lines[state.cursor_line] =
            line:sub(1, previous - 1) .. line:sub(state.cursor_col)
        state.cursor_col = previous
    elseif state.cursor_line > 1 then
        local previous_line = state.lines[state.cursor_line - 1]
        state.cursor_col = #previous_line + 1
        state.lines[state.cursor_line - 1] = previous_line .. line
        table.remove(state.lines, state.cursor_line)
        state.cursor_line = state.cursor_line - 1
    else
        return
    end
    state.dirty = true
    clamp_cursor()
    ensure_cursor_visible()
end

local function move_horizontal(direction)
    local line = state.lines[state.cursor_line]
    if direction < 0 then
        if state.cursor_col > 1 then
            state.cursor_col = utf8_prev(line, state.cursor_col)
        elseif state.cursor_line > 1 then
            state.cursor_line = state.cursor_line - 1
            state.cursor_col = #state.lines[state.cursor_line] + 1
        end
    else
        if state.cursor_col <= #line then
            state.cursor_col = utf8_next(line, state.cursor_col)
        elseif state.cursor_line < #state.lines then
            state.cursor_line = state.cursor_line + 1
            state.cursor_col = 1
        end
    end
    clamp_cursor()
    ensure_cursor_visible()
end

local function move_vertical(direction)
    local target = state.cursor_line + direction
    if target < 1 or target > #state.lines then return end
    local preferred = state.preferred_col
    state.cursor_line = target
    state.cursor_col = byte_after_chars(state.lines[target],
        math.max(0, preferred - 1))
    clamp_cursor()
    state.preferred_col = preferred
    ensure_cursor_visible()
end

local function insert_key(key)
    if key == "SPACE" then
        insert_text(" ")
    elseif key == "NEWLINE" then
        insert_text("\n")
    elseif key == "BACK" then
        backspace()
    elseif key == "DONE" then
        state.osk = false
        return
    else
        insert_text(state.lower and key:lower() or key)
    end
end

local function handle_osk(action)
    local row, col = 1, 1
    local index = 0
    for r, keys in ipairs(KEY_ROWS) do
        for c = 1, #keys do
            index = index + 1
            if index == state.osk_index then row, col = r, c end
        end
    end
    if action == "left" then col = math.max(1, col - 1)
    elseif action == "right" then col = math.min(#KEY_ROWS[row], col + 1)
    elseif action == "up" then row = math.max(1, row - 1); col = math.min(col, #KEY_ROWS[row])
    elseif action == "down" then row = math.min(#KEY_ROWS, row + 1); col = math.min(col, #KEY_ROWS[row])
    elseif action == "a" then
        local key = KEY_ROWS[row][col]
        if key then insert_key(key) end
    elseif action == "l1" then
        state.lower = not state.lower
    elseif action == "b" then
        state.osk = false
        return
    end
    local next_index = col
    for r = 1, row - 1 do next_index = next_index + #KEY_ROWS[r] end
    state.osk_index = next_index
end

local function handle_edit(action)
    if state.osk then
        handle_osk(action)
        return
    end
    if action == "left" then
        move_horizontal(-1)
    elseif action == "right" then
        move_horizontal(1)
    elseif action == "up" then
        move_vertical(-1)
    elseif action == "down" then
        move_vertical(1)
    elseif action == "a" then
        insert_text("\n")
    elseif action == "x" then
        backspace()
    elseif action == "r1" then
        state.osk = true
    elseif action == "start" then
        save_file(false)
    elseif action == "b" then
        save_file(true)
    end
end

function scene.textinput(value)
    if state.mode == "edit" and not state.osk then
        insert_text(value)
    end
end

function scene.enter()
    state.mode = "list"
    state.selected = 1
    state.first = 1
    state.loading = false
    state.confirm_delete = false
    state.osk = false
    state.status = "Local workspace · files stay inside data/Texts"
    love.keyboard.setTextInput(false)
    input.clear()
    input.on("press", function(action)
        if state.mode == "edit" then
            handle_edit(action)
            return
        end
        if state.confirm_delete then
            if action == "a" then delete_file()
            elseif action == "b" then state.confirm_delete = false end
            return
        end
        if action == "up" then
            state.selected = math.max(1, state.selected - 1)
        elseif action == "down" then
            state.selected = math.min(#state.files, state.selected + 1)
        elseif action == "a" then
            open_file()
        elseif action == "y" then
            new_file()
        elseif action == "x" and selected_file() then
            state.confirm_delete = true
        elseif action == "r1" then
            refresh_list()
        elseif action == "b" or action == "menu" then
            sm.back()
        end
    end)
    refresh_list()
end

function scene.leave()
    love.keyboard.setTextInput(false)
end

function scene.draw()
    local W, H = love.graphics.getDimensions()
    local th = theme.get()
    local accent = nodes.color_for(4)
    love.graphics.clear(th.bg[1], th.bg[2], th.bg[3], 1)
    chrome.draw_header({theme=th,title="Void-DESK",subtitle="VOID EDIT",status_icons={"file-text","battery"}})

    local x, y, w, h = 12, 76, W - 24, H - 148
    love.graphics.setColor(0.045,0.060,0.082,0.98)
    love.graphics.rectangle("fill",x,y,w,h,8)
    love.graphics.setColor(accent[1],accent[2],accent[3],0.48)
    love.graphics.rectangle("line",x,y,w,h,8)

    if state.mode == "list" then
        love.graphics.setFont(cached_font(15))
        love.graphics.setColor(0.92,0.96,1,1)
        love.graphics.print("TEXT WORKSPACE",x+16,y+12)
        love.graphics.setFont(cached_font(9))
        love.graphics.setColor(0.53,0.66,0.78,1)
        love.graphics.print("PRIVATE FILES  /  data/Texts  /  ALLOWLISTED TEXT TYPES",x+17,y+36)
        local top, row_h = y+58, ROW_H
        local visible = math.max(1,math.floor((h-90)/row_h))
        state.first = math.max(1,math.min(state.selected-visible+1,
            math.max(1,#state.files-visible+1)))
        for i=state.first,math.min(#state.files,state.first+visible-1) do
            local item = state.files[i]
            local ry = top+(i-state.first)*row_h
            local selected = i == state.selected
            love.graphics.setColor(selected and 0.12 or 0.065,
                selected and 0.16 or 0.085,selected and 0.21 or 0.12,1)
            love.graphics.rectangle("fill",x+12,ry,w-24,row_h-4,5)
            love.graphics.setColor(selected and accent[1] or 0.25,
                selected and accent[2] or 0.36,selected and accent[3] or 0.47,
                selected and 0.95 or 0.52)
            love.graphics.rectangle("line",x+12,ry,w-24,row_h-4,5)
            love.graphics.setFont(cached_font(11))
            love.graphics.setColor(0.91,0.95,1,1)
            love.graphics.print(tostring(item.name),x+22,ry+6)
            love.graphics.setFont(cached_font(8))
            love.graphics.setColor(0.56,0.68,0.79,1)
            love.graphics.print(string.format("%d bytes",tonumber(item.size) or 0),x+22,ry+24)
        end
        if #state.files == 0 then
            love.graphics.setFont(cached_font(12))
            love.graphics.setColor(0.62,0.72,0.82,1)
            love.graphics.printf("No text files yet.\nPress Y to create your first document.",x+24,y+145,w-48,"center")
        end
        if state.confirm_delete then
            love.graphics.setColor(0.22,0.045,0.06,0.98)
            love.graphics.rectangle("fill",x+24,H-119,w-48,36,6)
            love.graphics.setColor(1,0.4,0.38,1)
            love.graphics.rectangle("line",x+24,H-119,w-48,36,6)
            love.graphics.setFont(cached_font(10))
            love.graphics.setColor(1,0.86,0.85,1)
            love.graphics.printf("DELETE "..tostring(selected_file() or "FILE").."?  A CONFIRM  /  B CANCEL",x+32,H-107,w-64,"center")
        end
    else
        love.graphics.setFont(cached_font(13))
        love.graphics.setColor(0.93,0.96,1,1)
        love.graphics.print(state.name,x+16,y+9)
        love.graphics.setFont(cached_font(8))
        love.graphics.setColor(state.dirty and 1 or 0.53,state.dirty and 0.68 or 0.66,state.dirty and 0.31 or 0.78,1)
        love.graphics.print((state.dirty and "UNSAVED" or "SAVED").."  ·  "..#line_text().." / 131072 BYTES",x+17,y+31)

        local editor_y = y+50
        local editor_bottom = state.osk and H-176 or H-91
        local editor_h = math.max(42,editor_bottom-editor_y)
        love.graphics.setColor(0.018,0.028,0.043,1)
        love.graphics.rectangle("fill",x+12,editor_y,w-24,editor_h,4)
        love.graphics.setScissor(x+18,editor_y+6,w-36,editor_h-12)
        local f = cached_font(10)
        love.graphics.setFont(f)
        local line_h = f:getHeight()+4
        local visible = math.max(1,math.floor((editor_h-12)/line_h))
        local first = math.max(1,math.min(state.cursor_line-visible+1,
            math.max(1,#state.lines-visible+1)))
        state.first_line = first
        for i=first,math.min(#state.lines,first+visible-1) do
            local yy = editor_y+7+(i-first)*line_h
            love.graphics.setFont(cached_font(8))
            love.graphics.setColor(i==state.cursor_line and accent[1] or 0.35,
                i==state.cursor_line and accent[2] or 0.43,
                i==state.cursor_line and accent[3] or 0.52,1)
            love.graphics.print(string.format("%03d",i),x+21,yy+1)
            love.graphics.setFont(f)
            love.graphics.setColor(0.88,0.93,0.98,1)
            local line = state.lines[i]
            love.graphics.print(line,x+50,yy)
            if i == state.cursor_line and not state.osk and
                math.floor(love.timer.getTime()*2)%2 == 0 then
                local prefix = line:sub(1,state.cursor_col-1)
                local cx = x+50+f:getWidth(prefix)
                love.graphics.setColor(accent[1],accent[2],accent[3],0.95)
                love.graphics.rectangle("fill",cx,yy,2,line_h-2)
            end
        end
        love.graphics.setScissor()
        if state.osk then
            local kb_y = H-168
            love.graphics.setColor(0.03,0.045,0.065,0.99)
            love.graphics.rectangle("fill",12,kb_y,W-24,132,7)
            local cell_w = (W-52)/8
            local selected_index = 0
            for _, keys in ipairs(KEY_ROWS) do selected_index = selected_index+#keys end
            for row, keys in ipairs(KEY_ROWS) do
                for col, key in ipairs(keys) do
                    local index = col
                    for r=1,row-1 do index=index+#KEY_ROWS[r] end
                    local bx, by = 22+(col-1)*cell_w, kb_y+7+(row-1)*17
                    local selected = index == state.osk_index
                    love.graphics.setColor(selected and accent[1]*0.34 or 0.08,
                        selected and accent[2]*0.34 or 0.10,
                        selected and accent[3]*0.34 or 0.14,1)
                    love.graphics.rectangle("fill",bx,by,cell_w-3,15,3)
                    love.graphics.setColor(selected and accent[1] or 0.29,
                        selected and accent[2] or 0.39,selected and accent[3] or 0.50,1)
                    love.graphics.rectangle("line",bx,by,cell_w-3,15,3)
                    love.graphics.setFont(cached_font(7))
                    love.graphics.setColor(0.91,0.95,1,1)
                    love.graphics.printf(key,bx+1,by+4,cell_w-5,"center")
                end
            end
        end
    end

    if not state.osk then
        love.graphics.setFont(cached_font(9))
        love.graphics.setColor(0.56,0.67,0.77,1)
        love.graphics.printf(state.status,x+14,H-103,w-28,"left")
    end
    chrome.draw_footer({theme=th,hints=state.mode=="list" and {
        {icon="dpad",label="Select"},{icon="btn_a",label="Open"},
        {icon="btn_y",label="New"},{icon="btn_x",label="Delete"},{icon="btn_b",label="Back"},
    } or {
        {icon="r1",label="Keyboard"},{icon="l1",label="Case"},
        {icon="dpad",label="Move"},{icon="btn_a",label="Newline"},
        {icon="btn_x",label="Backspace"},{icon="btn_start",label="Save"},
    },right_text="128 KB MAX"})
end

return scene
