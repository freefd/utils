# A set of different tools

1. [vultr_ddns.lua](https://github.com/freefd/utils/blob/master/vultr_ddns.lua)

    The Lua script for Vultr DNS that allows you to use it with OpenWrt or LEDE as dynamic DNS script due to lack of such functionality in native ddns-scripts (https://github.com/openwrt/packages/tree/master/net/ddns-scripts).
1. [csd-post.sh](https://github.com/freefd/utils/blob/master/csd-post.sh)

    Cisco Secure Desktop wrapper for Openconnect, based on https://gitlab.com/openconnect/openconnect/blob/master/trojans/csd-post.sh. The script just simulates invoking of a trojan and sends predefined data, but it tries to be as honest as possible to avoid any synthentic params while they can be collected from a system such as Linux kernel version, hostname, opened ports, MAC address and so on.
1. [telegram_chatwipe.py](https://github.com/freefd/utils/blob/master/telegram_chatwipe.py)

    Python script to `delete` or `list` your messages from specified Telegram chat until a provided date. The simple example how to run it:
    ```
    ~> ./telegram_chatwipe.py --phone 79123456789 --api-id 123456 --api-hash a622ddd7244a59b9c12be4e762a133df --since 1970-01-01 --mode delete
    0. [All Peers]
    1. chat1 (Peer 1012345678)
    2. chat2 (Peer 1087654321)

    [INPUT] Choose from the list: 1
    [INFO] Chosen: chat1
    [INFO] Getting messages from peer 1012345678 for user Username until the date 1970-01-01 00:00:00...
    [INFO] Received: 100 messages. Offset: 0.
    [WARN] Going to delete among 100500 messages
    [INFO] Deleted 100500 messages
    ```
    The graphic explanation of the arguments `since` and `until`:
    ```mermaid
    timeline
      title History Timeline
      Older posts
      Date A : since
      ...
      Date B : until
      Newer posts
    ```

    You can also specify `peer` argument, please see usage help for more information.
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

    The Lua script for REG.RU DNS that allows you to use it with OpenWrt as dynamic DNS script due to lack of such functionality in native ddns-scripts (https://github.com/openwrt/packages/tree/master/net/ddns-scripts).

1. [regru_ddns.py](https://github.com/freefd/utils/blob/master/regru_ddns.py)

    The Python script for REG.RU DNS that allows you to use it with OpenWrt hotplug.d or Linux NetworkManager-dispatcher. WAN interface must be set in `CONFIG.hook.wan_interface`.

1. [RSSH.ps1](https://github.com/freefd/utils/blob/master/RSSH.ps1)

    Powershell script to run SSH reverse tunneling to export RDP for a special environment purposes.
    Please refer to [Windows RDP over reverse SSH tunneling](https://github.com/freefd/articles/blob/main/9_Windows_RDP_over_reverse_SSH_tunneling/README.md) article.

1. [media_files_sort.sh](https://github.com/freefd/utils/blob/master/media_files_sort.sh)

    Bash script to sort media files based on EXIF information or creation date from the current directory to the target directory in the format `BASEDIR/YYYY/MM/DD/YYYY-MM-DD_HHMMSS_XXHASH.EXTENSION`, where 
    * `BASEDIR` - a static root path to the target directory
    * `YYYY` .. `SS` - corresponding parts of date from file metadata, from the year up to seconds
    * `XXHASH` - the result of producing [xxh32sum](https://xxhash.com/) from the given file to make some entropy suffix
    * `EXTENSION` - preserved extension from the original file

    Prerequisites:
    * bash or dash
    * exiftool
    * jq
    * date
    * xxh32sum
    * rsync

    Non-unique files will have the same names, including the suffix from `xxh32sum` util, and will be overridden in the destination folder after an additional simple comparison.

    Nevertheless, later you could use [fdupes](https://github.com/adrianlopezroche/fdupes), [rmlint](https://rmlint.readthedocs.io/), [rdfind](https://github.com/pauldreik/rdfind) or similar software to find and remove duplicates.

    Script can recursively handle the following media types across the directories from the current: .JPG, .JPEG, .CRW, .THM, .RW2, .ARW, .AVI, .MOV, .MP4, .MPG, .3GP, .MTS, .PNG
    Especially for video media (.MP4, MPG and MOV), the script [will adjust](https://exiftool.org/ExifTool.html#QuickTimeUTC) the filename according to the current timezone.

    The script supports a few arguments:
    ```shell
    ~> bash media_files_sort.sh -h
    usage: media_files_sort.sh options

    OPTIONS:
      -h      Show this message
      -n      Run in Dry run Mode. Default: False
      -b      Based directory for output sorted files. Default: /path/to/media/sorted
      -d      Run in Debug Mode. Default: False
    ```

    There is a dry run mode available, so you can demo the results before doing the real work.
    You can also override the built-in path `/path/to/media/sorted` with the `-b` argument, or by editing the value of `_defaultBaseDirectory` variable inside the script.

    Dry run example:
    ```shell
    /p/t/m/i/directory> bash media_files_sort.sh -n -b /path/to/media/sorted_new
    [2025-04-09 15:30:40] INFO: Running in Dry run mode
    [2025-04-09 15:30:40] NOTICE: Intent to move '/path/to/media/incoming/directory/IMG_20221123_131543.jpg' to '/path/to/media/sorted_new/2022/11/23/2022-11-23_131543_b9be7a0d.jpg'
    [2025-04-09 15:30:40] NOTICE: Intent to move '/path/to/media/incoming/directory/IMG_20211202_194347_451.jpg' to '/path/to/media/sorted_new/2021/12/02/2021-12-02_194346_d7fca074.jpg'
    ... omitted for brevity ...
    [2025-04-09 15:30:45] NOTICE: Intent to move '/path/to/media/incoming/directory/Pictures/Office Lens/2020_10_06 13_53 Office Lens.jpg' to '/path/to/media/sorted_new/2020/10/06/2020-10-06_135342_da9615a0.jpg'
    [2025-04-09 15:30:45] NOTICE: Intent to move '/path/to/media/incoming/directory/Pictures/Office Lens/2020_12_11 21_30 Office Lens.jpg' to '/path/to/media/sorted_new/2020/12/11/2020-12-11_213026_00d0f2ac.jpg'
    ... omitted for brevity ...
    [2025-04-09 15:30:48] NOTICE: Intent to move '/path/to/media/incoming/directory/Videos/2_5454291518808396024.mp4' to '/path/to/media/sorted_new/2021/07/14/2021-07-14_160035_ca195681.mp4'
    [2025-04-09 15:30:48] NOTICE: Intent to move '/path/to/media/incoming/directory/Videos/2_5278634035076139354.MOV' to '/path/to/media/sorted_new/2020/11/08/2020-11-08_231816_65e8a444.MOV'
    ...
    ```