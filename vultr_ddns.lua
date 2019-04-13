#!/usr/bin/lua

-- For use with OpenWrt/LEDE since them support LUA.
-- DynDNS implementation for Vultr DNS service via API
-- The original idea was taken from https://github.com/nileshgr/utilities/blob/master/general/updateip.lua
-- You can put this script in interface hotplug or crontab.

-- Prerequisites:
-- luasec
-- luasocket
-- libubus-lua
-- json4lua


recordName   = "homerouter"
recordID     = 0
domainName   = "domain.tld"
domainList   = {}
dnsRecords   = {}
httpResponse = {}
domainFound  = false                                                       
recordAction = "create_record"

requestHeaders = {                                                         
        ["API-Key"] = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX", 
        ["Content-Type"] = "application/json",                             
} 

function log(msg)
    os.execute("logger -t dyndns '" .. msg .. "'")
end

require ("os")
require ("socket")
require ("ltn12")                                                                                              
require ("ubus")

json = require ("json")
https = require ("ssl.https")

u = ubus.connect()                                                                                             
                                                                                                               
if not u then                                                                                                  
    log('Ubus connect failed')                                                                                 
    os.exit(1)                                                                                                 
end                                                                                                            

status = u:call("network.interface.wan", "status", {})                                                         
wanIP = status["ipv4-address"][1]["address"]  

success = https.request({
    url = "https://api.vultr.com/v1/dns/list",
    sink = ltn12.sink.table(domainList),
    method = "GET",
    headers = requestHeaders,
})

if not success then
    log('Failed to fetch domains list')
    os.exit(1)	
end

domainList = json.decode(domainList[1])

for _, key in ipairs(domainList) do
    if key.domain == domainName then
        domainFound = true
        break
    end
end

if not domainFound then       
    log('Domain ' .. domainName .. ' has not been found')
    os.exit(1)                   
end

success = https.request({
    url = "https://api.vultr.com/v1/dns/records?domain=" .. domainName,
    sink = ltn12.sink.table(dnsRecords),
    method = "GET",
    headers = requestHeaders
})

if not success then
    log('Failed to fetch DNS records for ' .. domainName .. ' domain')
    os.exit(1)
end

dnsRecords = json.decode(dnsRecords[1])

for _, record in ipairs(dnsRecords) do
    if record.name == recordName and record.data == wanIP then
        log('Record update is not needed')                                                                           
        os.exit(0)                                                                                             
    elseif record.name == recordName then
        recordAction = "update_record"
        recordID = record.RECORDID
        break
    end
end

if recordID > 0 then
    recordRequest = 'domain=' .. domainName .. '&name=' .. recordName .. '&data=' .. wanIP .. '&RECORDID=' .. recordID .. '&type=A'
else
    recordRequest = 'domain=' .. domainName .. '&name=' .. recordName .. '&data=' .. wanIP .. '&type=A'
end

requestHeaders["Content-Length"] = string.len(recordRequest)
requestHeaders["Content-Type"]   = "application/x-www-form-urlencoded"
status = https.request({
    url = "https://api.vultr.com/v1/dns/" .. recordAction,
    method = "POST",
    headers = requestHeaders,
    sink = ltn12.sink.table(httpResponse),
    source = ltn12.source.string(recordRequest)
})

if not status then
    log('Failed to update record ' .. recordName .. '.' .. domainName .. ' [' .. wanIP .. ']')
else
    if recordAction == 'create_record' then
        log('Created record ' .. recordName .. '.' .. domainName .. ' [' .. wanIP .. ']')
    else
        log('Updated record ' .. recordName .. '.' .. domainName .. ' [' .. wanIP .. ']')
    end
end
