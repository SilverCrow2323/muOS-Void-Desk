-- Central layout: dimensions and font sizes for the whole app.
-- All scenes should read from here instead of hardcoding numbers.
local L = {
    -- Chrome
    HEADER_H = 68,
    FOOTER_H = 56,
    STATUS_H = 30,

    -- Menu
    MENU_ROW_H = 46,
    WIDGET_H = 140,

    -- Font sizes
    FONT = {
        title      = 32,   -- header title
        subtitle   = 22,   -- header subtitle
        clock      = 20,   -- header clock
        label      = 18,   -- menu row label
        desc       = 14,   -- menu row description
        value      = 16,   -- menu right-side value
        status     = 15,   -- status panel text
        widget_t   = 18,   -- widget card title
        widget_s   = 14,   -- widget card subtitle
        widget_v   = 16,   -- widget value
        tiny       = 12,
        mono       = 14,
        mono_sm    = 12,
    },

    -- Colors (theme-agnostic defaults)
    PAD = 8,
}

-- Backwards-compat lowercase aliases for scenes that use L.header_h etc.
L.header_h    = L.HEADER_H
L.footer_h    = L.FOOTER_H
L.status_h    = L.STATUS_H
L.strip_h     = L.STATUS_H
L.row_h       = L.MENU_ROW_H
L.widget_h    = L.WIDGET_H
L.scale       = 1
L.font_status = L.FONT.status

return L
