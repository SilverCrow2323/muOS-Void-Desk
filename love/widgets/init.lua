-- Minimal widget system (buttons, lists) — sostituibile con LUIS in Sprint 2
local theme = require("theme.loader")
local W = {}

-- ==== Button ====
function W.button(opts)
    local b = {
        x = opts.x or 0, y = opts.y or 0,
        w = opts.w or 160, h = opts.h or 40,
        text = opts.text or "",
        color = opts.color or theme.get("accent"),
        selected = opts.selected or false,
        on_press = opts.on_press,
    }

    function b:draw(mx, my)
        local t = theme.get()
        local is_sel = self.selected or (mx and my and
            mx >= self.x and mx <= self.x+self.w and
            my >= self.y and my <= self.y+self.h)

        -- glow se selezionato
        if is_sel then
            love.graphics.setColor(self.color[1], self.color[2], self.color[3], 0.25)
            love.graphics.rectangle("fill", self.x-3, self.y-3, self.w+6, self.h+6, 4)
        end

        -- sfondo
        love.graphics.setColor(t.panel_bg[1], t.panel_bg[2], t.panel_bg[3], 0.95)
        love.graphics.rectangle("fill", self.x, self.y, self.w, self.h, 3)

        -- bordo
        love.graphics.setColor(self.color[1], self.color[2], self.color[3], is_sel and 1.0 or 0.6)
        love.graphics.setLineWidth(is_sel and 2 or 1)
        love.graphics.rectangle("line", self.x, self.y, self.w, self.h, 3)

        -- testo
        love.graphics.setColor(t.text[1], t.text[2], t.text[3], 1)
        local font = love.graphics.getFont()
        local tw = font:getWidth(self.text)
        love.graphics.print(self.text,
            self.x + (self.w - tw)/2,
            self.y + (self.h - font:getHeight())/2)
    end

    function b:mousepressed(mx, my, btn)
        if btn == 1 and mx >= self.x and mx <= self.x+self.w and
           my >= self.y and my <= self.y+self.h then
            if self.on_press then self.on_press() end
        end
    end

    return b
end

-- ==== List (vertical scroll) ====
function W.list(opts)
    local l = {
        x = opts.x or 0, y = opts.y or 0,
        w = opts.w or 400, h = opts.h or 300,
        items = opts.items or {},
        selected = opts.selected or 1,
        on_select = opts.on_select,
    }

    function l:draw()
        local t = theme.get()
        love.graphics.setColor(t.panel_bg[1], t.panel_bg[2], t.panel_bg[3], 0.9)
        love.graphics.rectangle("fill", self.x, self.y, self.w, self.h, 3)
        love.graphics.setColor(t.accent[1], t.accent[2], t.accent[3], 0.5)
        love.graphics.rectangle("line", self.x, self.y, self.w, self.h, 3)

        local row_h = 28
        local max_rows = math.floor((self.h - 10) / row_h)
        local offset = math.max(0, self.selected - max_rows)
        for i = 1, math.min(max_rows, #self.items - offset) do
            local idx = i + offset
            local yy = self.y + 5 + (i-1) * row_h
            if idx == self.selected then
                love.graphics.setColor(t.accent[1], t.accent[2], t.accent[3], 0.25)
                love.graphics.rectangle("fill", self.x+3, yy, self.w-6, row_h-2, 2)
            end
            love.graphics.setColor(t.text[1], t.text[2], t.text[3], 1)
            love.graphics.print(tostring(self.items[idx]), self.x + 10, yy + 4)
        end
    end

    function l:move(d)
        self.selected = math.max(1, math.min(#self.items, self.selected + d))
        if self.on_select then self.on_select(self.selected) end
    end

    return l
end

return W
