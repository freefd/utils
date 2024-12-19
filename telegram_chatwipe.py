#!/usr/bin/env python3
''' Telegram Chat History Remover '''

import argparse
import datetime
import logging
import sys
import time
from typing import Any, List, Iterable, Dict, Union
from telethon import TelegramClient, sync
from telethon.tl.functions.messages import SearchRequest
from telethon.tl.types import InputMessagesFilterEmpty, InputPeerChannel, \
                        InputUserSelf, Channel, MessageEmpty, MessageService

def get_args() -> Dict:
    ''' Parse CLI arguments '''
    args_parser = argparse.ArgumentParser(
            description="Telegram Chat History Remover")
    args_parser.add_argument('--phone',
            type=int, default=0,
            help='Registered phone number. Default: not set',
            required=True)
    args_parser.add_argument('--api-id',
            type=int, default=0,
            help='Telegram API ID. Default: not set',
            required=True)
    args_parser.add_argument('--api-hash',
            type=str, default=None,
            help='Telegram API Hash. Default: not set',
            required=True)
    args_parser.add_argument('--until',
            type=valid_date_type,
            default=datetime.datetime.now().strftime("%Y-%m-%d"),
            help='Datetime in format "YYYY-MM-DD". Default: not set',
            required=False)
    args_parser.add_argument('--since',
            type=valid_date_type, default=None,
            help='Datetime in format "YYYY-MM-DD". Default: not set',
            required=True)
    args_parser.add_argument('--mode',
            type=str, choices=['list', 'delete'],
            default='list', help='Operating mode. Default: list.',
            required=True)
    args_parser.add_argument('--peer',
            type=int, default=0,
            help='Peer name. Default: not set')

    args_parser.add_argument(
        '--verbose', '-v', help='Enable verbose output. Default: 0.\n\n',
        required=False, default=0, action='count'
    )

    args_parsed = args_parser.parse_args()
    args_parsed.verbose = 30 - (10 * int(args_parsed.verbose)) if int(
        args_parsed.verbose) > 0 else 20

    return args_parsed

def valid_date_type(arg_date_str: str) -> datetime:
    ''' Validate datetime format '''

    try:
        return datetime.datetime.strptime(arg_date_str, "%Y-%m-%d")
    except ValueError as exc:
        msg = f'Given Date ({arg_date_str}) is not valid:\n\t{exc}. ' \
            'Expected format, YYYY-MM-DD'
        raise argparse.ArgumentTypeError(msg)

def message_chunks(l: List[Any], n: int) -> Iterable[Any]:
    ''' Split list into chunks '''

    for i in range(0, len(l), n):
        yield l[i:i + n]

def choose_peer(client, peer_id) -> List[int]:
    ''' Select a peer '''

    peers: List[Channel] = []
    prompt: str = ''
    dialogs = client.get_dialogs(limit=100)
    entities = [dialog.entity for dialog in dialogs \
                            if isinstance(dialog.entity, Channel)]
    entities = [entity for entity in entities if entity.megagroup]

    if len(entities) == 0:
        logging.warning('Cannot find user %s (%s) participation in any group',
                        client.get_me().username or client.get_me().first_name,
                        client.get_me().id)
        sys.exit(1)

    peer_exists = [entity.id for entity in entities if entity.id == peer_id]

    if isinstance(peer_id, int) and len(peer_exists) > 0:
        for entity in entities:
            if entity.id == peer_id:
                peers = [entity]
                logging.info('Chosen: %s', entity.title)
    else:
        prompt += '0. [All Peers]\n'

        for i, entity in enumerate(entities):
            prompt += f'{i+1}. {entity.title} (Peer {entity.id})\n'

        print(prompt)

        num = input('[INPUT] Choose from the list: ')

        if num == '':
            logging.warning('Chosen: None')
            sys.exit(1)
        elif num == '0':
            logging.info('Chosen: All Peers')
            peers = entities
        else:
            logging.info('Chosen: %s', entities[int(num)-1].title)
            peers = [entities[int(num)-1]]

    return peers

def get_messages(client: TelegramClient, peer_id: Union[Channel],
                peer_hash: str, since_date: datetime,
                until_date: datetime) -> List[int]:
    ''' Collect messages for the peer and time range '''

    logging.info('Getting messages from peer %s for %s: %s - %s',
            peer_id,
            client.get_me().username or client.get_me().first_name,
            str(since_date), str(until_date))

    add_offset: int = 0
    messages: List[int] = []

    while True:
        time.sleep(0.1)

        search_result = client(SearchRequest(
            peer=InputPeerChannel(peer_id, peer_hash),
            q='',
            filter=InputMessagesFilterEmpty(),
            min_date=since_date,
            max_date=until_date,
            offset_id=0,
            add_offset=add_offset,
            limit=100,
            max_id=0,
            min_id=0,
            from_id=InputUserSelf(),
            hash=0
        ))

        if search_result.messages:
            for post in search_result.messages:
                if not isinstance(post, MessageEmpty):
                    logging.info('Received: %s messages. Offset: %s',
                                    len(search_result.messages), add_offset)
                    if post.date.replace(tzinfo=None) >= since_date:
                        messages.extend([post])
                        add_offset += 1
                    else:
                        return messages
                else:
                    add_offset += 1

        else:
            logging.info("It's stopped because met end of chat")
            return messages

if __name__ == '__main__':

    args = get_args()

    logging.basicConfig(
        format = '[%(asctime)s] %(levelname)s %(module)s: %(message)s',
        level = args.verbose
    )

    if args.api_id > 0 and args.api_hash != '' and args.phone > 0:
        client_telegram = TelegramClient(
                        f'chatwipe{args.phone}', args.api_id, args.api_hash)
        client_telegram.start(f'+{args.phone}')

        for peer in choose_peer(client_telegram, args.peer):
            logging.info('Peer: %s', peer.title)
            messages_found = get_messages(
                    client = client_telegram,
                    peer_id = peer.id,
                    peer_hash = peer.access_hash,
                    since_date = args.since,
                    until_date = args.until.replace(hour = 23, minute = 59, second = 59)
                )

            if args.mode == 'delete' and len(messages_found) > 0:
                logging.warning('Going to delete among %s messages',
                                        len(messages_found))

            for chunk in message_chunks(messages_found, 100):
                if args.mode == 'delete':
                    affected_messages = client_telegram.delete_messages(
                        InputPeerChannel(peer.id, peer.access_hash), chunk)

                    logging.info('Deleted %s messages',
                            affected_messages[0].pts_count)
                elif args.mode == 'list':
                    for message in chunk:
                        if isinstance(message, MessageService):
                            logging.info('(%s) %s',
                                str(message.date.strftime("%b %d %Y %H:%M:%S UTC")),
                                message.action)
                        else:
                            logging.info('(%s) [ID:%s]: %s',
                                str(message.date.strftime("%b %d %Y %H:%M:%S UTC")),
                                message.id, message.message)
    else:
        logging.fatal('Please provide correct arguments')
