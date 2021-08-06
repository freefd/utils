#!/usr/bin/env python3

import argparse
import datetime
import json
import logging
import os
import socket
import time
import tempfile

from argparse import RawTextHelpFormatter
from telethon import TelegramClient, events, sync, types
from telethon.events.newmessage import NewMessage
from telethon.tl.functions.messages import SearchRequest, GetDialogsRequest
from telethon.tl.types import DataJSON, InputMessagesFilterEmpty, InputPeerChannel, \
                                PeerChannel, Channel, User, Message

def get_args(show_usage: bool=False) -> dict:
    """
    Define arguments are allowed to be passed to the script
    """
    args_parser = argparse.ArgumentParser(
        description="Forward messages from Telegram Channels to Graylog over UDP GELF",
        formatter_class=RawTextHelpFormatter)
    args_parser.add_argument('--phone', '-ph', type=int, required=False,
                             default=os.environ.get(
                                 'CHATLOG2GRAYLOG_PHONE') or 0,
                             help='Registered phone number. CHATLOG2GRAYLOG_PHONE '\
                                  'environment variable will also work. '\
                                  'Default: 0.\n\n')
    args_parser.add_argument('--api-id', '-id', type=int, required=False,
                             default=os.environ.get(
                                 'CHATLOG2GRAYLOG_API_ID') or 0,
                             help='Telegram API ID. CHATLOG2GRAYLOG_API_ID '\
                                  'environment variable will also work. '\
                                  'Default: 0.\n\n')
    args_parser.add_argument('--api-hash', '-hash', type=str, required=False,
                             default=os.environ.get(
                                 'CHATLOG2GRAYLOG_API_HASH') or None,
                             help='Telegram API Hash. CHATLOG2GRAYLOG_API_HASH '\
                                  'environment variable will also work. '\
                                  'Default: not set.\n\n')
    args_parser.add_argument('--until', '-u', type=valid_date_type, required=False,
                             default=os.environ.get(
                                 'CHATLOG2GRAYLOG_UNTIL') or None,
                             help='Datetime in format "YYYY-MM-DD". '\
                                  'CHATLOG2GRAYLOG_UNTIL environment variable will '\
                                  'also work. Default: not set.\n\n')
    args_parser.add_argument('--verbose', '-v', action='count', required=False,
                             default=os.environ.get(
                                 'CHATLOG2GRAYLOG_LOG_LEVEL') or 0,
                             help='Enable verbose output. CHATLOG2GRAYLOG_LOG_LEVEL '\
                                  'environment variable will also work. '\
                                  'Default: 0.\n\n')
    args_parser.add_argument('--mode', '-m', type=str, required=False,
                             choices=['realtime', 'history'],
                             default=os.environ.get(
                                 'CHATLOG2GRAYLOG_MODE') or 'realtime',
                             help='Operating mode. CHATLOG2GRAYLOG_MODE '\
                                  'environment variable will also work. '\
                                  'Default: realtime.\n\n')
    args_parser.add_argument('--graylog-host', '-gh', type=str, required=False,
                             default=os.environ.get(
                                 'CHATLOG2GRAYLOG_GRAYLOG_HOST') or None,
                             help='Graylog host to forward messages. CHATLOG2GRAYLOG_HOST '\
                                  'environment variable will also work. '\
                                  'Default: not set.\n\n')
    args_parser.add_argument('--graylog-port', '-gp', type=int, required=False,
                             default=os.environ.get(
                                 'CHATLOG2GRAYLOG_GRAYLOG_PORT') or 12201,
                             help='Graylog GELF input port. CHATLOG2GRAYLOG_GRAYLOG_PORT '\
                                  'environment variable will also work. Default: 12201\n\n')

    # Convert a whitespace separated string with peers to list
    peerlist = os.environ.get('CHATLOG2GRAYLOG_PEERS').split(
        ' ') if os.environ.get('CHATLOG2GRAYLOG_PEERS') else None

    args_parser.add_argument('--peers', '-p', type=str, required=False, nargs='+',
                             default=peerlist or None,
                             help='List of chat peer IDs for '\
                                  'realtime mode. CHATLOG2GRAYLOG_PEERS '\
                                  'environment variable will also work. '\
                                  'Default: not set.')

    # Special switcher to show usage
    if show_usage:
        args_parser.print_help()
        exit()

    # Adjust log level
    args_parsed = args_parser.parse_args()
    args_parsed.verbose = 30 - (10*int(args_parsed.verbose)) if int(
                                        args_parsed.verbose) > 0 else 50

    return args_parsed

def valid_date_type(arg_date_str: str) -> datetime:
    """
    Datetime validation type helper for argparse
    """
    try:
        return datetime.datetime.strptime(arg_date_str, "%Y-%m-%d")
    except ValueError:
        msg = f'[ERROR] Given Date ({arg_date_str}) '\
              f'is not valid. Expected format: YYYY-MM-DD'
        raise argparse.ArgumentTypeError(msg)


class Telegram2Graylog:

    def __init__(self, arguments: dict) -> None:
        """
        Initializing and starting Telegram Client
        """
        self.arguments = arguments
        self.telegram_client = TelegramClient(tempfile.gettempdir() +
                                    '/telegram_chatlog2graylog.session',
                                    self.arguments.api_id, self.arguments.api_hash)
        self.telegram_client.start(str('+')+str(self.arguments.phone))
        self.host = socket.gethostbyname(socket.gethostname())

    def choose_peer(self) -> object:
        """
        Filtering out channels and selecting chat peer(s) to work with
        """
        peers = []
        prompt: str = ''
        dialogs = self.telegram_client.get_dialogs(limit=100)

        entities = [dialog.entity for dialog in dialogs if isinstance(
            dialog.entity, Channel)]
        entities = [entity for entity in entities if entity.megagroup]

        if len(entities) == 0:
            logging.error(f'Cannot find chats the account is participating')
            exit()

        prompt += f'0. [All Peers]\n'

        for i, entity in enumerate(entities):
            prompt += f'{i+1}. Chat: {entity.title} (Peer {entity.id})\n'

        print(prompt)

        num = input('[INPUT] Choose chat: ')
        if num == '':
            logging.warn('Chosen: None')
            exit()
        elif num == '0':
            logging.info('Chosen: All Peers')
            peers = entities
        elif 0 <= int(num) < len(entities)+1:
            logging.info(f'Chosen: {entities[int(num)-1].title}')
            peers = [entities[int(num)-1]]
        else:
            logging.error(f'Provided item is not in the list')

        return peers

    def gelf_builder(self, object: dict, sender=None, channel=None) -> dict:
        """
        Converting telegram's message or event to GELF format
        """
        gelf = {}
        if isinstance(object, Message):
            # Process user's message from chat with defined message text
            if object.from_id is not None and object.message and object.message != '':
                user = self.telegram_client.get_entity(object.from_id)
                channel = self.telegram_client.get_entity(object.peer_id)

                if isinstance(user, User) and isinstance(channel, Channel):
                    gelf = {}
                    gelf['version'] = '1.1'
                    gelf['channel_title'] = channel.title
                    gelf['channel_id'] = int('-100' + str(channel.id))

                    gelf['sender_id'] = user.id
                    gelf['sender_username'] = user.username
                    gelf['sender_firstname'] = user.first_name
                    gelf['sender_lastname'] = user.last_name

                    gelf['timestamp'] = int(object.date.timestamp())
                    gelf['message_id'] = object.id
                    gelf['full_message'] = object.message
                    gelf['short_message'] = object.message[:60] + \
                        (object.message[60:] and '..')
                    gelf['host'] = self.host

        else:

            # Process non-service user's message from chat with defined message text
            if (isinstance(sender, User) and isinstance(channel, Channel) and
                    object.from_id is not None and 
                    object.raw_text and object.raw_text != ''):

                gelf['version'] = '1.1'
                gelf['channel_title'] = channel.title
                gelf['channel_id'] = object.chat_id
                gelf['sender_id'] = object.sender_id

                gelf['sender_username'] = sender.username
                gelf['sender_firstname'] = sender.first_name
                gelf['sender_lastname'] = sender.last_name

                gelf['timestamp'] = int(object.date.timestamp())
                gelf['message_id'] = object.id
                gelf['full_message'] = object.raw_text
                gelf['short_message'] = object.raw_text[:60] + \
                    (object.raw_text[60:] and '..')
                gelf['host'] = self.host

        return gelf if len(gelf) > 0 else None

    def gelf_sender(self, message):
        """
        Sending UDP GELF message towards Graylog GELF input
        """
        logging.debug(f'Sending parsed message: {message} to '
                      f'{self.arguments.graylog_host}:{self.arguments.graylog_port}')
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(json.dumps(message).encode(),
                    (self.arguments.graylog_host, self.arguments.graylog_port))

    def get_messages(self, peer_id: int, peer_hash: str,
                     up_to_date, limit: int = 100, offset_id: int = 0,
                     max_id: int = 0, min_id: int = 0) -> object:
        """
        Collecting messages from defined chat peer(s) until provided date
        """

        logging.info(f'Getting messages from peer {peer_id} '
                     f'until the date {up_to_date}...')

        add_offset = 0
        messages = list()

        while True:
            time.sleep(0.1)

            search_result = self.telegram_client(SearchRequest(
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
                from_id=None,
                hash=0
            ))

            if search_result.messages:
                logging.info(
                    f'Received: {len(search_result.messages)} messages. Offset: {add_offset}.')
                for post in search_result.messages:
                    if post.date.replace(tzinfo=None) > up_to_date:
                        messages.extend([post])
                        add_offset += 1
                    else:
                        return messages

            else:
                logging.info("It's stopped because met end of chat")
                return messages


if __name__ == '__main__':

    args = get_args()

    logging.basicConfig(
        format='[%(asctime)s] %(levelname)s: %(message)s',
        level=args.verbose)

    # All necessary arguments should be defined
    if (args.api_id > 0 and args.api_hash != '' and args.phone > 0
            and args.mode != '' and args.graylog_host is not None):

        logging.debug(f'Running Mode: {args.mode}')

        if args.mode == 'history':

            if not args.until:
                get_args(True)
                exit(1)

            telegram_to_graylog = Telegram2Graylog(args)
            peers = telegram_to_graylog.choose_peer()

            for peer in peers:
                logging.info(f'Peer: {peer.title}')
                messages_found = telegram_to_graylog.get_messages(
                    peer.id, peer.access_hash, args.until)

                logging.info(
                    f'Send messages one by one: {args.graylog_host} via {args.graylog_port}/UDP')

                for message in messages_found:
                    logging.debug(f'New raw message: {message}')

                    gelf_message = telegram_to_graylog.gelf_builder(message)
                    if gelf_message is not None:
                        telegram_to_graylog.gelf_sender(gelf_message)

        elif args.mode == 'realtime':

            telegram_to_graylog = Telegram2Graylog(args)
            chatlist = [PeerChannel(int(peer))
                        for peer in args.peers] if args.peers else None

            # Subscribing to messages from provided list of chat(s) as peers
            # otherwise subscribing to all chats the user participate
            @telegram_to_graylog.telegram_client.on(events.NewMessage(chats=chatlist))
            async def telegram_event_handler(event):

                logging.debug(f'New raw event: {event}')

                sender = await event.get_sender()
                channel = await event.get_chat()

                gelf_message = telegram_to_graylog.gelf_builder(
                    event, sender, channel)
                if gelf_message is not None:
                    telegram_to_graylog.gelf_sender(gelf_message)

            telegram_to_graylog.telegram_client.run_until_disconnected()
    else:
        get_args(True)
