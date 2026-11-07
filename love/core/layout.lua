-- Central layout: dimensions and font sizes for the whole app.
-- All scenes should read from here instead of hardcoding numbers.
local L = {
    -- Chrome
    HEADER_H = 68,
    FOOTER_H = 56,
    STATUS_H = 30,

    -- Menu
    MENU_ROW_H = 54,
    WIDGET_H = 180,

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

return L
