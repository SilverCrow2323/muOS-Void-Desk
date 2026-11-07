local dbg = {}

function dbg.dump_joysticks()
    local joys = love.joystick.getJoysticks()
    print(string.format("[input] %d joystick(s) detected", #joys))
    for i, j in ipairs(joys) do
        print(string.format("  #%d  name=%s  buttons=%d  axes=%d  hats=%d  isGamepad=%s",
            i, j:getName(),
            j:getButtonCount(),
            j:getAxisCount(),
            j:getHatCount(),
            tostring(j:isGamepad())))
    end
end

return dbg
