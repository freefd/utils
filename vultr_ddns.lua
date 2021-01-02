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

require("os")
require("socket")
require("ltn12")
require("ubus")

json = require("json")
https = require("ssl.https")

apiKey         = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
recordName     = "homerouter"
domainName     = "domain.tld"
domainFound    = false
requestMethod  = "POST"
requestURI     = "https://api.vultr.com/v2/domains/" .. domainName .. "/records"
recordTemplate = {
    name = recordName,
    data = "127.0.0.1",
    type = "A",
    ttl = "300",
    priority = 0
}
requestHeaders = {
    ["Authorization"] = "Bearer " .. apiKey,
    ["Content-Type"] = "application/json",
}

remoteIP       = {}
domainList     = {}
dnsRecords     = {}

function log(msg)
    os.execute("logger -t dyndns '" .. msg .. "'")
end

u = ubus.connect()

if not u then
    log("Ubus connect failed")
    os.exit(1)
end

status = u:call("network.interface.wan", "status", {})
wanIP = status["ipv4-address"][1]["address"]

remoteIPResponse = https.request({
    url = "https://ifconfig.me/all.json",
    sink = ltn12.sink.table(remoteIP),
    method = "GET",
    headers = requestHeaders,
})

if remoteIPResponse then
    local detectedIP = json.decode(remoteIP[1]).ip_addr
    if remoteIP and wanIP ~= detectedIP  then
        log("We are behind NAT: " .. wanIP .. " <-> " .. detectedIP )
        wanIP = detectedIP
    end
end

apiResponse = https.request({
    url = "https://api.vultr.com/v2/domains",
    method = "GET",
    headers = requestHeaders,
    sink = ltn12.sink.table(domainList)
})

if not apiResponse then
    log("Failed to fetch domains list")
    os.exit(1)
end

domainList = json.decode(domainList[1]).domains

for _, key in ipairs(domainList) do
    if key.domain == domainName then
        domainFound = true
        break
    end
end

if not domainFound then
    log("Domain " .. domainName .. " has not been found")
    os.exit(1)
end

apiResponse = https.request({
    url = "https://api.vultr.com/v2/domains/" .. domainName .. "/records" ,
    method = "GET",
    headers = requestHeaders,
    sink = ltn12.sink.table(dnsRecords)
})

if not apiResponse then
    log("Failed to fetch DNS records for " .. domainName .. " domain")
    os.exit(1)
end

dnsRecords = json.decode(dnsRecords[1]).records

for _, record in ipairs(dnsRecords) do
    if record.name == recordName and record.data == wanIP then
        log("Record update is not needed: " .. wanIP )
        os.exit(0)
    elseif record.name == recordName then
        requestMethod = "PATCH"
        requestURI = requestURI .. "/" .. record.id
        recordTemplate["data"] = wanIP
        break
    else
        recordTemplate["data"] = wanIP
    end
end

recordTemplate = json.encode(recordTemplate)
requestHeaders["Content-Length"] = string.len(recordTemplate)

apiResponse = https.request({
    url = requestURI,
    method = requestMethod,
    headers = requestHeaders,
    source = ltn12.source.string(recordTemplate)
})

if not apiResponse then
    log("Failed to update record " .. recordName .. "." .. domainName .. " [" .. wanIP .. "]")
else
    if requestMethod == "POST" then
        log("Record has been created: " .. recordName .. "." .. domainName .. " [" .. wanIP .. "]")
    else
        log("Record has been updated: " .. recordName .. "." .. domainName .. " [" .. wanIP .. "]")
    end
end
