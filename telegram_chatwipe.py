#!/usr/bin/env python3

import time
import argparse
import datetime
from typing import Any, List, Iterable, Dict, Union
from telethon import TelegramClient, sync, types, functions
from telethon.tl.functions.channels import DeleteMessagesRequest
from telethon.tl.functions.messages import SearchRequest, GetDialogsRequest
from telethon.tl.types import InputMessagesFilterEmpty, InputPeerChannel, InputPeerEmpty, InputUserSelf, Channel

def get_args() -> Dict:
    args_parser = argparse.ArgumentParser(description="Telegram's Chat History Remover")
    args_parser.add_argument('--user', type=str, default=None, help='Telegram user name. Default: not set', required=True)
    args_parser.add_argument('--phone', type=str, default=None, help='Registered phone number. Default: not set', required=True)
    args_parser.add_argument('--api-id', type=int, default=0, help='Telegram API ID. Default: not set', required=True)
    args_parser.add_argument('--api-hash', type=str, default=None, help='Telegram API Hash. Default: not set', required=True)
    args_parser.add_argument('--until', type=valid_date_type, default=None, help='Datetime in format "YYYY-MM-DD". Default: not set', required=True)
    args_parser.add_argument('--mode', type=str, choices=['list', 'delete'], default='list', help='Operating mode. Default: list.', required=True)
    args_parser.add_argument('--peer', type=int, default=0, help='Peer name. Default: not set')
    return args_parser.parse_args()

def valid_date_type(arg_date_str: str) -> datetime:
    try:
        return datetime.datetime.strptime(arg_date_str, "%Y-%m-%d")
    except ValueError:
        msg = "[ERROR] Given Date ({0}) not valid. Expected format, YYYY-MM-DD".format(arg_date_str)
        raise argparse.ArgumentTypeError(msg)

def message_chunks(l: List[Any], n: int) -> Iterable[Any]:
    for i in range(0, len(l), n):
        yield l[i:i + n]

def choose_peer(client, peer_id) -> List[int]:
    peer = 0
    prompt: str = ''
    dialogs = client.get_dialogs(limit=30)

    entities = [dialog.entity for dialog in dialogs if isinstance(dialog.entity, Channel)]
    entities = [entity for entity in entities if entity.megagroup]
    peer_exists = [entity.id for entity in entities if entity.id == peer_id]

    if isinstance(peer_id, int) and len(peer_exists)>0:
        for entity in entities:
            if entity.id == peer_id:
                peer = entity
                print('[INFO] Chosen: '+entity.title)
    else:
        for i, entity in enumerate(entities):
            prompt += '{}. {} (Peer {})\n'.format(i+1, entity.title, entity.id)

        print(prompt)

        num = input('[INPUT] Choose chat: ')
        print('[INFO] Chosen: '+entities[int(num)-1].title)
        peer = entities[int(num)-1]
    
    return peer

def get_messages(client, peer_id: Union[Channel], peer_hash: str,
                 delete_up_to_date, username: str, limit: int = 100,
                 offset_id: int = 0, max_id: int = 0, min_id: int = 0) -> List[int]:

    print('[INFO] Getting messages from peer {} for user {} until the date {}...'.format(peer_id, username, delete_up_to_date))

    add_offset = 0
    messages: List[int] = []

    while True:
        time.sleep(0.1)

        search_result = client(SearchRequest(
            peer=InputPeerChannel(peer_id, peer_hash),
            q='',
            filter=InputMessagesFilterEmpty(),
            min_date=None,
            max_date=None,
            offset_id=offset_id,
            add_offset=add_offset,
            limit=limit,
            max_id=max_id,
            min_id=min_id,
            from_id=InputUserSelf(),
            hash=0
        ))

        if search_result.messages:
            print('[INFO] Received: {0} messages. Offset: {1}.'.format(len(search_result.messages), add_offset))
            for post in search_result.messages:
                if post.date.replace(tzinfo=None) > delete_up_to_date:
                    messages.extend([post])
                    add_offset += 1
                else:
                    return messages

        else:
            print("[INFO] It's stopped because met end of chat.")
            return messages

def main(args) -> None:
    if args.user != '' and args.api_id != 0 and args.api_hash != '' and args.phone != '':
        client = TelegramClient(args.user, args.api_id, args.api_hash)
        client.start(str('+')+args.phone)
        
        peer = choose_peer(client, args.peer)
        messages_found = get_messages(client, peer.id, peer.access_hash, args.until, args.user)

        if args.mode == 'delete' and len(messages_found) > 0:
            print("[WARN] Going to delete among {} messages".format(len(messages_found)))

        for chunk in message_chunks(messages_found, 100):
            if args.mode == 'delete':
                affected_messages = client.delete_messages(InputPeerChannel(peer.id, peer.access_hash), chunk)
                print("[INFO] Deleted {} messages".format(affected_messages[0].pts_count))
            elif args.mode == 'list':
                for post in chunk:
                    print("[INFO] ({}) [ID:{}]: {}".format(str(post.date.strftime(
                        "%b %d %Y %H:%M:%S UTC")), str(post.id), str(post.message)))

    else:
        print('[ERROR] Please provide the necessary values for the params')

if __name__ == '__main__':
    main(get_args())
