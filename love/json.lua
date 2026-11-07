-- Minimal JSON encoder/decoder for LÖVE (no external deps)
local json = {}

local function escape_char(c)
    local map = { ['"'] = '\\"', ['\\'] = '\\\\', ['\b'] = '\\b',
                  ['\f'] = '\\f', ['\n'] = '\\n', ['\r'] = '\\r',
                  ['\t'] = '\\t' }
    return map[c] or string.format("\\u%04x", string.byte(c))
end

local function escape_str(s)
    return '"' .. s:gsub('[%z\1-\31\\"]', escape_char) .. '"'
end

local function is_array(t)
    local i = 0
    for _ in pairs(t) do i = i + 1 end
    return i == #t
end

local function encode_value(v)
    local t = type(v)
    if t == "nil" then return "null"
    elseif t == "boolean" then return tostring(v)
    elseif t == "number" then return tostring(v)
    elseif t == "string" then return escape_str(v)
    elseif t == "table" then
        if is_array(v) then
            local parts = {}
            for _, item in ipairs(v) do parts[#parts+1] = encode_value(item) end
            return "[" .. table.concat(parts, ",") .. "]"
        else
            local parts = {}
            for k, val in pairs(v) do
                parts[#parts+1] = escape_str(tostring(k)) .. ":" .. encode_value(val)
            end
            return "{" .. table.concat(parts, ",") .. "}"
        end
    end
    return "null"
end

function json.encode(v) return encode_value(v) end

-- minimal decoder
local function skip_ws(s, i)
    while i <= #s and s:sub(i,i):match("%s") do i = i + 1 end
    return i
end

local parse_value

local function parse_string(s, i)
    local out = {}
    i = i + 1
    while i <= #s do
        local c = s:sub(i,i)
        if c == '"' then return table.concat(out), i + 1 end
        if c == '\\' then
            local n = s:sub(i+1,i+1)
            local map = { ['"']='"', ['\\']='\\', ['/']='/', b='\b',
                          f='\f', n='\n', r='\r', t='\t' }
            out[#out+1] = map[n] or n
            i = i + 2
        else
            out[#out+1] = c
            i = i + 1
        end
    end
    error("unterminated string")
end

local function parse_number(s, i)
    local j = i
    while j <= #s and s:sub(j,j):match("[%-%+0-9eE%.]") do j = j + 1 end
    return tonumber(s:sub(i, j - 1)), j
end

function parse_value(s, i)
    i = skip_ws(s, i)
    local c = s:sub(i,i)
    if c == '"' then return parse_string(s, i)
    elseif c == '{' then
        local obj = {}
        i = skip_ws(s, i + 1)
        if s:sub(i,i) == '}' then return obj, i + 1 end
        while true do
            local k, ni = parse_string(s, skip_ws(s, i))
            ni = skip_ws(s, ni)
            if s:sub(ni,ni) ~= ':' then error("expected :") end
            local v, ni2 = parse_value(s, ni + 1)
            obj[k] = v
            ni2 = skip_ws(s, ni2)
            if s:sub(ni2,ni2) == '}' then return obj, ni2 + 1 end
            if s:sub(ni2,ni2) ~= ',' then error("expected ,") end
            i = ni2 + 1
        end
    elseif c == '[' then
        local arr = {}
        i = skip_ws(s, i + 1)
        if s:sub(i,i) == ']' then return arr, i + 1 end
        while true do
            local v, ni = parse_value(s, i)
            arr[#arr+1] = v
            ni = skip_ws(s, ni)
            if s:sub(ni,ni) == ']' then return arr, ni + 1 end
            if s:sub(ni,ni) ~= ',' then error("expected ,") end
            i = ni + 1
        end
    elseif s:sub(i,i+3) == "true" then return true, i + 4
    elseif s:sub(i,i+4) == "false" then return false, i + 5
    elseif s:sub(i,i+3) == "null" then return nil, i + 4
    else return parse_number(s, i)
    end
end

function json.decode(s)
    local v = parse_value(s, 1)
    return v
end

return json
