#!/usr/bin/env bash
# Cisco Anyconnect CSD wrapper for OpenConnect
# 
# This script is trying to be as honest as possible to mimic the official Cisco Anyconnect client.

function valid_ip()
{
    local  ip=$1
    local  stat=1

    if [[ $ip =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
        OIFS=$IFS
        IFS='.'
        ip=($ip)
        IFS=$OIFS
        [[ ${ip[0]} -le 255 && ${ip[1]} -le 255 \
            && ${ip[2]} -le 255 && ${ip[3]} -le 255 ]]
        stat=$?
    fi
    return $stat
}

if ! command -v xmlstarlet &>/dev/null; then
    echo "************************************************************************" >&2
    echo "WARNING: xmlstarlet not found in path; CSD token extraction may not work" >&2
    echo "************************************************************************" >&2
    unset useXMLStarlet
else
    useXMLStarlet=true
fi

kernelVersion=$(uname -r)
kernelArchitecture=$(uname -i)
hostName=$(hostname -s)

[ -f "$(command -v ss)" -a -x "$(command -v ss)" ] && socketsUtil=$(command -v ss) || socketsUtil=$(command -v netstat)
declare -a tcp4Ports=($(${socketsUtil} -n4tl | awk '/[0-9]/{print $4}' | awk -F: '{print $2}' | sort -n | uniq))
declare -a udp4Ports=($(${socketsUtil} -n4ul | awk '/[0-9]/{print $4}' | awk -F: '{print $2}' | sort -n | uniq))

if valid_ip ${CSD_HOSTNAME}; then
    ipAddress=${CSD_HOSTNAME}
else
    if command -v dig &>/dev/null; then
        ipAddress=$(dig -t A +short ${CSD_HOSTNAME})
    elif command -v nslookup &>/dev/null; then
        ipAddress=$(nslookup -type=A ${CSD_HOSTNAME} | awk '/^Address:/ {A=$2}; END {print A}')
    fi
fi

macAddress=$(cat /sys/class/net/$(ip route get ${ipAddress} | awk '/dev/{print $5}')/address)

if command -v dpkg-query &>/dev/null; then
    iptableVersion=$(dpkg-query -W -f "\${Version}" iptables | awk -F- '{print $1}')
elif command -v rpm &>/dev/null; then
    iptableVersion=$(rpm -qa --queryformat "%{VERSION}" iptables)
else
    iptableVersion="1.6.1"
fi

read -d '' payloadData <<EOF
endpoint.os.version="Linux";
endpoint.os.servicepack="${kernelVersion}";
endpoint.os.architecture="${kernelArchitecture}";
endpoint.device.protection="none";
endpoint.device.protection_version="4.3.05059";
endpoint.device.hostname="${hostName}";
EOF

payloadData+=$'\n'

for port in ${tcp4Ports[@]}; do payloadData+="endpoint.device.port[\"${port}\"]=\"true\";"$'\n'; done
for port in ${tcp4Ports[@]}; do payloadData+="endpoint.device.tcp4port[\"${port}\"]=\"true\";"$'\n'; done
for port in ${udp4Ports[@]}; do payloadData+="endpoint.device.udp4port[\"${port}\"]=\"true\";"$'\n'; done

payloadData+="endpoint.device.MAC[\"${macAddress}\"]=\"true\";
endpoint.device.protection_extension=\"5.1.6.8\";
endpoint.enforce=\"success\";
endpoint.fw[\"IPTablesFW\"]={};
endpoint.fw[\"IPTablesFW\"].exists=\"true\";
endpoint.fw[\"IPTablesFW\"].description=\"IPTables (Linux)\";
endpoint.fw[\"IPTablesFW\"].version=\"${iptableVersion}\";
endpoint.fw[\"IPTablesFW\"].enabled=\"failed\";
"
shift

requestTicket=
requestStub=0

while [ "$1" ]; do
    if [ "$1" == "-ticket" ]; then shift; requestTicket=${1//\"/}; fi
    if [ "$1" == "-stub" ]; then shift; requestStub=${1//\"/}; fi
    shift
done

pinnedPubKey="-s ${CSD_SHA256:+"-k --pinnedpubkey sha256//$CSD_SHA256"}"
requestURI="https://${CSD_HOSTNAME}/+CSCOE+/sdesktop/token.xml?ticket=${requestTicket}&stub=${requestStub}"

if [ -n "${useXMLStarlet}" ]; then
    requestToken=$(curl ${pinnedPubKey} -s "${requestURI}" | xmlstarlet sel -t -v /hostscan/token)
else
    requestToken=$(curl ${pinnedPubKey} -s "${requestURI}" | sed -n '/<token>/s^.*<token>\(.*\)</token>^\1^p' )
fi

cookieHeader="Cookie: sdesktop=${requestToken}"
contentHeader="Content-Type: text/xml"
requestURI="https://${CSD_HOSTNAME}/+CSCOE+/sdesktop/scan.xml?reusebrowser=1"

curl ${pinnedPubKey} -H "${contentHeader}" -H "${cookieHeader}" --data "${payloadData}type=text/xml" "${requestURI}"
exit 0
