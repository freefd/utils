# A set of differents tools

1. [vultr_ddns.lua](https://github.com/freefd/utils/blob/master/vultr_ddns.lua)

    The Lua script for Vultr DNS that allows you to use it with OpenWrt or LEDE as dynamic DNS script due to lack of such functionality in native ddns-scripts (https://github.com/openwrt/packages/tree/master/net/ddns-scripts).
1. [csd-post.sh](https://github.com/freefd/utils/blob/master/csd-post.sh)

    Cisco Secure Desktop wrapper for Openconnect, based on https://gitlab.com/openconnect/openconnect/blob/master/trojans/csd-post.sh. The script just simulates invoking of a trojan and sends predefined data, but it tries to be as honest as possible to avoid any synthentic params while they can be collected from a system such as Linux kernel version, hostname, opened ports, MAC address and so on.
1. [telegram_chatwipe.py](https://github.com/freefd/utils/blob/master/telegram_chatwipe.py)

    Telegram script to `delete` or `list` your messages from specified chat until a provided date. The simple example how to run:
    ```
    ~> ./telegram_chatwipe.py --phone 79123456789 --api-id 123456 --api-hash a622ddd7244a59b9c12be4e762a133df --until 1970-01-01 --mode delete
    1. chat1 (1012345678)
    2. chat2 (1087654321)

    [INPUT] Choose chat: 1
    [INFO] Chosen: chat1
    [INFO] Getting messages from peer 1012345678 for user Username until the date 1970-01-01 00:00:00...
    [INFO] Received: 100 messages. Offset: 0.
    [WARN] Going to delete among 3600 messages
    [INFO] Deleted 3600 messages
    ```
    You could also specify a `peer` argument, please see usage help for more infomation.
    Don't forget to install [telethon](https://docs.telethon.dev/en/latest/) module for python 3 and create your own [credentials](https://core.telegram.org/api/obtaining_api_id) before you start.
