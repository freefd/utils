# A set of differents tools

1. [vultr_ddns.lua](https://github.com/freefd/utils/blob/master/vultr_ddns.lua)

    The Lua script for Vultr DNS that allows you to use it with OpenWrt or LEDE as dynamic DNS script due to lack of such functionality in native ddns-scripts (https://github.com/openwrt/packages/tree/master/net/ddns-scripts).
1. [csd-post.sh](https://github.com/freefd/utils/blob/master/csd-post.sh)

    Cisco Secure Desktop wrapper for Openconnect, based on https://gitlab.com/openconnect/openconnect/blob/master/trojans/csd-post.sh. The script just simulates invoking of a trojan and sends predefined data, but it tries to be as honest as possible to avoid any synthentic params while they can be collected from a system such as Linux kernel version, hostname, opened ports, MAC address and so on.
1. [telegram_chatwipe.py](https://github.com/freefd/utils/blob/master/telegram_chatwipe.py)

    Python script to `delete` or `list` your messages from specified Telegram chat until a provided date. The simple example how to run it:
    ```
    ~> ./telegram_chatwipe.py --phone 79123456789 --api-id 123456 --api-hash a622ddd7244a59b9c12be4e762a133df --until 1970-01-01 --mode delete
    0. [All Peers]
    1. chat1 (Peer 1012345678)
    2. chat2 (Peer 1087654321)

    [INPUT] Choose chat: 1
    [INFO] Chosen: chat1
    [INFO] Getting messages from peer 1012345678 for user Username until the date 1970-01-01 00:00:00...
    [INFO] Received: 100 messages. Offset: 0.
    [WARN] Going to delete among 3600 messages
    [INFO] Deleted 3600 messages
    ```
    You could also specify `peer` argument, please see usage help for more information.
    Do not forget to install [telethon](https://docs.telethon.dev/en/latest/) module for Python 3 and create your own [credentials](https://core.telegram.org/api/obtaining_api_id) before you start.

1. [telegram_graph.py](https://github.com/freefd/utils/blob/master/telegram_graph.py)

    Python script to generate Plantuml graph from chats, channels and their common contacts in which you participate. Please read [article](https://ntwrk.today/2020/04/09/building-telegram-graph.html) for more information.

1. [telegram_chats_intersection.py](https://github.com/freefd/utils/blob/master/telegram_chats_intersection.py)
    
    Python script to get the intersection between pairs of Telegram chats you participate or pass by `peers` argument. The simple example how to run it:
    ```
    ~> ./telegram_chats_intersection.py --phone 79123456789 --api-id 123456 --api-hash a622ddd7244a59b9c12be4e762a133df --verbose --showusers --peers 1012345678 1087654321
    INFO:root:Creating Telegram Client
    INFO:telethon.network.mtprotosender:Connecting to 123.234.123.234:443/TcpFull...
    INFO:telethon.network.mtprotosender:Connection to 123.234.123.234:443/TcpFull complete!
    INFO:root:Collecting known chats
    INFO:root:Collected the list of chats: Chat Title 1; Chat Title 2
    INFO:root:Parsing "Chat Title 1" (1012345678) with 320 users
    INFO:root:Parsing users from chat "Chat Title 1" (1012345678)
    INFO:root:Sleep for 2 seconds
    INFO:root:Parsing "Chat Title 2" (1087654321) with 2500 users
    INFO:root:Parsing users from chat "Chat Title 2" (1087654321)
    INFO:root:Sleep for 2 seconds
    INFO:root:Intersection "Chat Title 1" with "Chat Title 2"
    overlapping_1012345678_1087654321:
      1012345678:
        part: 3/320
        percentage: '0.94'
        title: Chat Title 1
      1087654321:
        part: 3/2500
        percentage: '0.27'
        title: Chat Title 2
      users:
        23012345:
          firstname: First Name 1
          lastname: Last Name 1
          username: UserName1
        327654321:
          firstname: First Name 2
          username: UserName2
        661345678:
          username: UserName3
    ```
    You could also do not specify `peers` argument, it will perform intersection across of available possible pair combinations for your chats. Please see usage help for more information.
    Do not forget to install [telethon](https://docs.telethon.dev/en/latest/) module for Python 3 and create your own [credentials](https://core.telegram.org/api/obtaining_api_id) before you start.

1. [telegram_chatlog2graylog.py](https://github.com/freefd/utils/blob/master/telegram_chatlog2graylog.py)

    Please refer to [Telegram to Graylog forwarder](https://github.com/freefd/articles/blob/main/6_telegram_chatlog/README.md) article.

1. [regru_ddns.lua](https://github.com/freefd/utils/blob/master/regru_ddns.lua)

    The Lua script for REG.RU DNS that allows you to use it with OpenWrt or LEDE as dynamic DNS script due to lack of such functionality in native ddns-scripts (https://github.com/openwrt/packages/tree/master/net/ddns-scripts).
