function love.conf(t)
    -- Detect device: the muOS launcher sets VOIDDESK_FULLSCREEN=1
    local fs = (os.getenv("VOIDDESK_FULLSCREEN") == "1")
    -- Fallback: if love binary lives in ./lib/ we are on device
    if not fs then
        local f = io.open("lib/love", "r")
        if f then f:close(); fs = true end
    end

    t.identity = "voiddesk"
    t.version  = "11.5"
    t.console  = (os.getenv("VOIDDESK_CONSOLE") == "1")

    t.window.title       = "VoidDesk"
    t.window.width       = 640
    t.window.height      = 480
    t.window.fullscreen  = fs       -- windowed on PC, fullscreen on device
    t.window.borderless  = fs
    t.window.vsync       = 1
    t.window.msaa        = 0
    t.window.resizable   = not fs
    t.window.highdpi = true
    t.window.x           = 100
    t.window.y           = 100

    t.modules.joystick   = true
    t.modules.keyboard   = true
    t.modules.mouse      = true
    t.modules.audio      = true
    t.modules.physics    = false
    t.modules.video      = false
    t.modules.touch      = false
end
