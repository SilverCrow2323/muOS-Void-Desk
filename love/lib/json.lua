local json = {}

local function esc(c)
    local m = {['"']='\\"',['\\']='\\\\',['\b']='\\b',['\f']='\\f',
               ['\n']='\\n',['\r']='\\r',['\t']='\\t'}
    return m[c] or string.format("\\u%04x", string.byte(c))
end
local function esc_str(s) return '"'..s:gsub('[%z\1-\31\\"]', esc)..'"' end
local function is_arr(t)
    local i = 0; for _ in pairs(t) do i=i+1 end
    return i == #t
end
local function enc(v)
    local t = type(v)
    if t=="nil" then return "null"
    elseif t=="boolean" then return tostring(v)
    elseif t=="number" then return tostring(v)
    elseif t=="string" then return esc_str(v)
    elseif t=="table" then
        if is_arr(v) then
            local p={} ; for _,x in ipairs(v) do p[#p+1]=enc(x) end
            return "["..table.concat(p,",").."]"
        else
            local p={} ; for k,x in pairs(v) do
                p[#p+1]=esc_str(tostring(k))..":"..enc(x)
            end
            return "{"..table.concat(p,",").."}"
        end
    end
    return "null"
end
function json.encode(v) return enc(v) end

local function skip(s,i) while i<=#s and s:sub(i,i):match("%s") do i=i+1 end return i end
local pv
local function pstr(s,i)
    local o={} ; i=i+1
    while i<=#s do
        local c=s:sub(i,i)
        if c=='"' then return table.concat(o), i+1 end
        if c=='\\' then
            local n=s:sub(i+1,i+1)
            local m={['"']='"',['\\']='\\',['/']='/',b='\b',f='\f',n='\n',r='\r',t='\t'}
            o[#o+1]=m[n] or n ; i=i+2
        else o[#o+1]=c ; i=i+1 end
    end
    error("unterminated string")
end
local function pnum(s,i)
    local j=i
    while j<=#s and s:sub(j,j):match("[%-%+0-9eE%.]") do j=j+1 end
    return tonumber(s:sub(i,j-1)), j
end
function pv(s,i)
    i=skip(s,i) ; local c=s:sub(i,i)
    if c=='"' then return pstr(s,i)
    elseif c=='{' then
        local o={} ; i=skip(s,i+1)
        if s:sub(i,i)=='}' then return o,i+1 end
        while true do
            local k,ni=pstr(s,skip(s,i))
            ni=skip(s,ni)
            if s:sub(ni,ni)~=':' then error("expected :") end
            local v,ni2=pv(s,ni+1)
            o[k]=v ; ni2=skip(s,ni2)
            if s:sub(ni2,ni2)=='}' then return o,ni2+1 end
            if s:sub(ni2,ni2)~=',' then error("expected ,") end
            i=ni2+1
        end
    elseif c=='[' then
        local a={} ; i=skip(s,i+1)
        if s:sub(i,i)==']' then return a,i+1 end
        while true do
            local v,ni=pv(s,i)
            a[#a+1]=v ; ni=skip(s,ni)
            if s:sub(ni,ni)==']' then return a,ni+1 end
            if s:sub(ni,ni)~=',' then error("expected ,") end
            i=ni+1
        end
    elseif s:sub(i,i+3)=="true" then return true,i+4
    elseif s:sub(i,i+4)=="false" then return false,i+5
    elseif s:sub(i,i+3)=="null" then return nil,i+4
    else return pnum(s,i) end
end
function json.decode(s) return (pv(s,1)) end
return json
