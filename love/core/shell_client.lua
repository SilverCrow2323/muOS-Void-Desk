local bridge = require("core.bridge")

local client = {}
client.output = ""
client.ready = false
client.poll_timer = 0
client.POLL_INTERVAL = 0.15

function client.start(cb)
    bridge.call("shell_start", {}, function(resp)
        if resp.ok then client.ready = true end
        if cb then cb(resp) end
    end)
end

function client.poll(dt)
    if not client.ready then return end
    client.poll_timer = client.poll_timer + dt
    if client.poll_timer < client.POLL_INTERVAL then return end
    client.poll_timer = 0
    bridge.call("shell_poll", {}, function(resp)
        if resp.ok and resp.output and #resp.output > 0 then
            client.output = client.output .. resp.output
            if #client.output > 60000 then
                client.output = client.output:sub(-60000)
            end
        end
    end)
end

function client.send(text, cb)
    bridge.call("shell_send", { text = text }, cb)
end

function client.stop()
    bridge.call("shell_kill", {}, function() end)
    client.ready = false
    client.output = ""
end

function client.exec(cmd)
    client.send(cmd .. "\n")
end

return client
