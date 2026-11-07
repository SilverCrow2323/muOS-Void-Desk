local loader = {}
local THEMES = {
    cyberpunk = {
        bg         = {0.02, 0.03, 0.05},
        header_bg  = {0.05, 0.08, 0.12},
        footer_bg  = {0.03, 0.04, 0.06},
        panel_bg   = {0.08, 0.10, 0.14},
        accent     = {0.29, 0.81, 0.88},
        accent2    = {0.96, 0.35, 0.83},
        text       = {0.92, 0.94, 0.96},
        dim        = {0.55, 0.60, 0.66},
        shadow     = {0, 0, 0, 0.65},
        orbit_color = {0.29, 0.81, 0.88, 0.35},
        scanlines  = true,
        vignette   = true,
    },
    crimson = {
        bg         = {0.04, 0.02, 0.02},
        header_bg  = {0.08, 0.03, 0.04},
        footer_bg  = {0.03, 0.02, 0.02},
        panel_bg   = {0.10, 0.04, 0.05},
        accent     = {0.91, 0.21, 0.33},
        accent2    = {1.00, 0.69, 0.18},
        text       = {0.94, 0.92, 0.90},
        dim        = {0.58, 0.52, 0.52},
        shadow     = {0, 0, 0, 0.7},
        orbit_color = {0.91, 0.21, 0.33, 0.35},
        scanlines  = false,
        vignette   = true,
    },
    stealth = {
        bg         = {0.03, 0.03, 0.03},
        header_bg  = {0.05, 0.05, 0.05},
        footer_bg  = {0.02, 0.02, 0.02},
        panel_bg   = {0.07, 0.07, 0.08},
        accent     = {0.62, 0.66, 0.68},
        accent2    = {0.45, 0.48, 0.50},
        text       = {0.82, 0.85, 0.86},
        dim        = {0.42, 0.45, 0.46},
        shadow     = {0, 0, 0, 0.8},
        orbit_color = {0.62, 0.66, 0.68, 0.25},
        scanlines  = false,
        vignette   = false,
    },
    green = {
        bg         = {0.01, 0.04, 0.02},
        header_bg  = {0.02, 0.06, 0.03},
        footer_bg  = {0.01, 0.03, 0.02},
        panel_bg   = {0.03, 0.08, 0.04},
        accent     = {0.31, 0.88, 0.38},
        accent2    = {0.24, 0.94, 0.66},
        text       = {0.75, 0.95, 0.78},
        dim        = {0.35, 0.55, 0.38},
        shadow     = {0, 0, 0, 0.6},
        orbit_color = {0.31, 0.88, 0.38, 0.35},
        scanlines  = true,
        vignette   = true,
    },
}
local current = THEMES.cyberpunk

function loader.apply(name)
    current = THEMES[name] or THEMES.cyberpunk
    love.graphics.setBackgroundColor(current.bg[1], current.bg[2], current.bg[3])
end
function loader.get() return current end
function loader.list() return THEMES end

return loader
