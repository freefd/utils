#!/usr/bin/lua

-- For use with OpenWrt/LEDE since them support LUA.
-- DynDNS implementation for REG.RU DNS service via API
-- The original idea was taken from https://github.com/nileshgr/utilities/blob/master/general/updateip.lua
-- You can put this script in interface hotplug or crontab.
-- Prerequisites:
-- luasec
-- luasocket
-- libubus-lua

require("os")
require("socket")
require("ltn12")
require("ubus")

cjson = require "luci.jsonc"
https = require("ssl.https")

apiUsername     = "username@maildomain.tld"
apiPassword     = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
recordName      = "homerouter"
domainName      = "domain.tld"
domainFound     = false
remoteIP        = {}
domainList      = {}
dnsRecords      = {}
addDnsRecord    = {}
removeDnsRecord = {}

function log(msg)
    os.execute("logger -t dyndns '" .. msg .. "'")
end

u = ubus.connect()

if not u then
    log("Ubus connect failed")
    os.exit(1)
end

status = u:call("network.interface.wan", "status", {})
wanIP = status["ipv4-address"][1].address

remoteIPResponse = https.request({
    url = "https://ident.me/",
    sink = ltn12.sink.table(remoteIP),
    method = "GET",
})

remoteIP = table.concat(remoteIP)

if remoteIPResponse then
    local detectedIP = remoteIP
    if remoteIP and wanIP ~= detectedIP then
        log("We are behind NAT: " .. wanIP .. " <-> " .. detectedIP)
        wanIP = detectedIP
    end
end

apiRequestPayload = 'input_data={"domains":[{"dname":"' .. domainName .. '"}]}&input_format=json&username=' .. apiUsername .. '&password=' .. apiPassword
apiResponse = https.request {
    url = "https://api.reg.ru/api/regru2/zone/nop",
    method = "POST",
    sink = ltn12.sink.table(domainList),
    source = ltn12.source.string(apiRequestPayload),
    headers = {
        ["content-length"] = #apiRequestPayload,
        ["content-type"] = "application/x-www-form-urlencoded",
    }
}

domainList = table.concat(domainList)

if not apiResponse then
    log("Failed to fetch domains list")
    os.exit(1)
end

for _, key in pairs(cjson.parse(domainList).answer.domains) do
    if key.dname == domainName then
        domainFound = true
        break
    end
end

if not domainFound then
    log("Domain " .. domainName .. " has not been found")
    os.exit(1)
end

apiResponse = https.request({
    url = "https://api.reg.ru/api/regru2/zone/get_resource_records",
    method = "POST",
    sink = ltn12.sink.table(dnsRecords),
    source = ltn12.source.string(apiRequestPayload),
    headers = {
        ["content-length"] = #apiRequestPayload,
        ["content-type"] = "application/x-www-form-urlencoded",
    }
})

if not apiResponse then
    log("Failed to fetch DNS records for " .. domainName .. " domain")
    os.exit(1)
end

dnsRecords = table.concat(dnsRecords)

for _, record in ipairs(cjson.parse(dnsRecords).answer.domains[1].rrs) do
    if record.subname == recordName and record.content == wanIP then
        log("Record update is not needed: " .. wanIP)
        os.exit(0)
    elseif record.subname == recordName then
        log("Record is required to be updated: " .. wanIP)
        apiRequestPayload = 'input_data={"domains":[{"dname":"' .. domainName .. '"}],"subdomain":"' ..
                            recordName .. '","record_type":"A"}&input_format=json&username=' ..
                            apiUsername .. '&password=' .. apiPassword
        apiResponse = https.request({
            url = "https://api.reg.ru/api/regru2/zone/remove_record",
            method = "POST",
            sink = ltn12.sink.table(removeDnsRecord),
            source = ltn12.source.string(apiRequestPayload),
            headers = {
                ["content-length"] = #apiRequestPayload,
                ["content-type"] = "application/x-www-form-urlencoded",
            }
        })

        local removeDnsRecord = table.concat(removeDnsRecord)

        if cjson.parse(removeDnsRecord).result == "success" then
            log("Obsolete record has been deleted: " .. recordName .. "." .. domainName)
        end
    end
end

apiRequestPayload = 'input_data={"domains":[{"dname":"' .. domainName .. '"}],"subdomain":"' ..
                    recordName .. '","ipaddr":"' .. wanIP .. '"}&input_format=json&username=' ..
                    apiUsername .. '&password=' .. apiPassword
apiResponse = https.request({
    url = "https://api.reg.ru/api/regru2/zone/add_alias",
    method = "POST",
    sink = ltn12.sink.table(addDnsRecord),
    source = ltn12.source.string(apiRequestPayload),
    headers = {
        ["content-length"] = #apiRequestPayload,
        ["content-type"] = "application/x-www-form-urlencoded",
    }
})

addDnsRecord = table.concat(addDnsRecord)

if cjson.parse(addDnsRecord).result == "success" then
    log("Record has been created: " .. recordName .. "." .. domainName .. " [" .. wanIP .. "]")
else
    log("Failed to create record " .. recordName .. "." .. domainName .. " [" .. wanIP .. "]")
end
