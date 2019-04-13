# A set of differents tools

1. [vultr_ddns.lua](https://github.com/freefd/utils/vultr_ddns.lua)

    The Lua script for Vultr DNS that allows you to use it with OpenWrt or LEDE as dynamic DNS script due to lack of such functionality in native ddns-scripts (https://github.com/openwrt/packages/tree/master/net/ddns-scripts).
1. [csd-post.sh](https://github.com/freefd/utils/csd-post.sh)

    Cisco Secure Desktop wrapper for Openconnect, based on https://gitlab.com/openconnect/openconnect/blob/master/trojans/csd-post.sh. The script just simulates invoking of a trojan and sends predefined data, but it tries to be as honest as possible to avoid any synthentic params while they can be collected from a system such as Linux kernel version, hostname, opened ports, MAC address and so on.
