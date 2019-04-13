#!/usr/bin/env bash
# Cisco Anyconnect CSD wrapper for OpenConnect
# 
# Based on https://gitlab.com/openconnect/openconnect/blob/master/trojans/csd-post.sh
# This script is trying to be as honest as possible to mimic the official Cisco Anyconnect client.

if ! xmlstarlet --version > /dev/null 2>&1; then
    echo "************************************************************************" >&2
    echo "WARNING: xmlstarlet not found in path; CSD token extraction may not work" >&2
    echo "************************************************************************" >&2
    unset XMLSTARLET
else
    XMLSTARLET=true
fi

[ -f "$(which ss)" -a -x "$(which ss)" ] && socketsUtil=$(which ss) || socketsUtil=$(which netstat)

declare -a tcp4Ports=($(${socketsUtil} -n4tl | awk '/[0-9]/{print $4}' | awk -F: '{print $2}' | sort -n | uniq))
declare -a udp4Ports=($(${socketsUtil} -n4ul | awk '/[0-9]/{print $4}' | awk -F: '{print $2}' | sort -n | uniq))

kernelVersion=$(uname -r)
hostName=$(hostname -s)
macAddress=$(cat /sys/class/net/$(ip route get $(dig +short ${CSD_HOSTNAME}) | awk '/dev/{print $5}')/address)

read -d '' DATA <<EOF
endpoint.os.version="Linux";
endpoint.os.servicepack="${kernelVersion}";
endpoint.os.architecture="x64";
endpoint.device.protection="none";
endpoint.device.protection_version="4.3.05059";
endpoint.device.hostname="${hostName}";
EOF

DATA+=$'\n'

for port in ${tcp4Ports[@]}; do DATA+="endpoint.device.port[\"${port}\"]=\"true\";"$'\n'; done
for port in ${tcp4Ports[@]}; do DATA+="endpoint.device.tcp4port[\"${port}\"]=\"true\";"$'\n'; done
for port in ${udp4Ports[@]}; do DATA+="endpoint.device.udp4port[\"${port}\"]=\"true\";"$'\n'; done

DATA+="endpoint.device.MAC[\"${macAddress}\"]=\"true\";
endpoint.device.protection_extension=\"3.6.11765.2\";
endpoint.enforce=\"success\";
endpoint.fw[\"IPTablesFW\"]={};
endpoint.fw[\"IPTablesFW\"].exists=\"true\";
endpoint.fw[\"IPTablesFW\"].description=\"IPTables (Linux)\";
endpoint.fw[\"IPTablesFW\"].version=\"1.6.1\";
endpoint.fw[\"IPTablesFW\"].enabled=\"failed\";
"
shift

TICKET=
STUB=0

while [ "$1" ]; do
    if [ "$1" == "-ticket" ]; then shift; TICKET=${1//\"/}; fi
    if [ "$1" == "-stub" ]; then shift; STUB=${1//\"/}; fi
    shift
done

PINNEDPUBKEY="-s ${CSD_SHA256:+"-k --pinnedpubkey sha256//$CSD_SHA256"}"
URL="https://${CSD_HOSTNAME}/+CSCOE+/sdesktop/token.xml?ticket=${TICKET}&stub=${STUB}"
if [ -n "${XMLSTARLET}" ]; then
    TOKEN=$(curl ${PINNEDPUBKEY} -s "${URL}"  | xmlstarlet sel -t -v /hostscan/token)
else
    TOKEN=$(curl ${PINNEDPUBKEY} -s "${URL}" | sed -n '/<token>/s^.*<token>\(.*\)</token>^\1^p' )
fi
COOKIE_HEADER="Cookie: sdesktop=${TOKEN}"
CONTENT_HEADER="Content-Type: text/xml"
URL="https://${CSD_HOSTNAME}/+CSCOE+/sdesktop/scan.xml?reusebrowser=1"
curl ${PINNEDPUBKEY} -H "${CONTENT_HEADER}" -H "${COOKIE_HEADER}" --data "${DATA};type=text/xml" "${URL}"
