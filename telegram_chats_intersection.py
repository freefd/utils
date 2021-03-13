#!/usr/bin/env python3

from telethon import TelegramClient, sync
from telethon.tl.types import ChannelParticipantsSearch, Channel
from telethon.tl.functions.channels import GetParticipantsRequest
from textwrap import wrap
from time import sleep
import os
import logging
import argparse
import itertools
import yaml

class Intersection:
    def __init__(self, arguments):
        self.verbose = arguments.verbose
        self.showusers = arguments.showusers
        self.peers = arguments.peers
        self.client_api_id = arguments.api_id
        self.client_api_hash = arguments.api_hash
        self.client_phone_id = arguments.phone
        self.db = {'chats':{}, 'results':{}}

    def _percentage(self, part, whole):
        # Calculate percentage
        return f'{100 * float(part)/float(whole):.2f}'

    def _create_client(self):
        # Create Telegram client
        if self.verbose: logging.info(f'Creating Telegram Client')
        client = TelegramClient(os.path.basename(__file__),
                                self.client_api_id,
                                self.client_api_hash)
        # Start a client
        client.start(self.client_phone_id)
        # Save our own ID
        self.user_id = client.get_me().id

        return client

    def parse_chats(self):
        # Create Telegram client
        client = self._create_client()

        # Get all available known channels
        channel_list = [dialog.entity for dialog in client.get_dialogs() if isinstance(dialog.entity, Channel)]
        if self.verbose: logging.info(f'Collecting known chats')

        # Check whether the specific peers were passed using arguments
        if self.peers is not None:
            flat_peers_list = [peer for sublist in self.peers for peer in sublist]
            channel_list = [dialog.entity for dialog in client.get_dialogs()
                if isinstance(dialog.entity, Channel) and dialog.entity.id in flat_peers_list]
        # Otherwise get all available channels 
        else:
            channel_list = [dialog.entity for dialog in client.get_dialogs()
                if isinstance(dialog.entity, Channel) and dialog.entity.megagroup]

        if self.verbose: logging.info(f"Collected the list of chats: {'; '.join([channel.title for channel in channel_list])}")

        # Iterate over channels
        for channel in channel_list:

            # Get all participants, max 10k users due to https://github.com/LonamiWebs/Telethon/issues/580
            users = client.get_participants(channel, aggressive=False)
            if self.verbose: logging.info(f'Parsing "{channel.title}" ({channel.id}) with {len(users)} users')

            # Save some necessary stuff
            self.db['chats'][channel.id] = {}
            self.db['chats'][channel.id]['users'] = {}
            self.db['chats'][channel.id]['title'] = channel.title
            self.db['chats'][channel.id]['users_number'] = len(users)

            # Discover and save details about participants in a particular chat
            if self.verbose: logging.info(f'Parsing users from chat "{channel.title}" ({channel.id})')
            for participant in users:
                # Ignore our own ID
                if participant.id != self.user_id:
                    self.db['chats'][channel.id]['users'][participant.id] = dict()
                    self.db['chats'][channel.id]['users'][participant.id]['username'] = participant.username or None
                    self.db['chats'][channel.id]['users'][participant.id]['first_name'] = participant.first_name or None
                    self.db['chats'][channel.id]['users'][participant.id]['last_name'] = participant.last_name or None

            # Sleep for 2 seconds to avoid any requests restriction by Telegram platform
            if self.verbose: logging.info(f'Sleep for 2 seconds')
            sleep(2)

    def find_intersection(self):
        # Get a list of tupleы with two channel each for intersection by participants
        for channels_list in itertools.combinations(self.db['chats'].keys(), 2):

            if self.verbose:
                logging.info(f"Intersection \"{self.db['chats'][channels_list[0]]['title']}\" with \"{self.db['chats'][channels_list[1]]['title']}\"")

            intersection_users = sorted(
                list(
                    set.intersection(
                        set(
                            list(self.db['chats'][channels_list[0]]['users'].keys())
                        ),
                        set(
                            list(self.db['chats'][channels_list[1]]['users'].keys())
                        )
                    )
                )
            )

            # If the intersection participants exist
            if len(intersection_users) > 0:
                # Generate YAML structure
                root_key = '_'.join(['overlapping', str(channels_list[0]), str(channels_list[1])])

                self.db['results'][root_key] = {}
                self.db['results'][root_key][channels_list[0]] = {}
                self.db['results'][root_key][channels_list[1]] = {}

                self.db['results'][root_key][channels_list[0]]['title'] = self.db['chats'][channels_list[0]]['title']
                self.db['results'][root_key][channels_list[1]]['title'] = self.db['chats'][channels_list[1]]['title']
                self.db['results'][root_key][channels_list[0]]['percentage'] = \
                    self._percentage(len(intersection_users),self.db['chats'][channels_list[0]]['users_number'])
                self.db['results'][root_key][channels_list[1]]['percentage'] = \
                    self._percentage(len(intersection_users),self.db['chats'][channels_list[1]]['users_number'])
                self.db['results'][root_key][channels_list[0]]['part'] = \
                    str(len(intersection_users)) + "/" + str(self.db['chats'][channels_list[0]]['users_number'])
                self.db['results'][root_key][channels_list[1]]['part'] = \
                    str(len(intersection_users)) + "/" + str(self.db['chats'][channels_list[1]]['users_number'])

                # Generate YAML for users if such an argument has been passed
                if self.showusers:
                    self.db['results'][root_key]['users'] = {}
                    for user in intersection_users:
                        self.db['results'][root_key]['users'][user] = {}
                        if self.db['chats'][channels_list[0]]['users'][user]['first_name'] is not None:
                            self.db['results'][root_key]['users'][user]['firstname'] = \
                                self.db['chats'][channels_list[0]]['users'][user]['first_name']
                        if self.db['chats'][channels_list[0]]['users'][user]['last_name'] is not None:
                            self.db['results'][root_key]['users'][user]['lastname'] = \
                                self.db['chats'][channels_list[0]]['users'][user]['last_name']
                        if self.db['chats'][channels_list[0]]['users'][user]['username'] is not None:
                            self.db['results'][root_key]['users'][user]['username'] = \
                                self.db['chats'][channels_list[0]]['users'][user]['username']

                # Print result YAML
                print(yaml.dump(self.db['results'], allow_unicode=True))
            else:
                if self.verbose: logging.info(f"Did not find common users")
            print("")

def get_args():
    args_parser = argparse.ArgumentParser(description="Check participants intersection between two Telegram chats")
    args_parser.add_argument('--phone', default=0, type=int, help='Registered phone number. Default: not set', required=True)
    args_parser.add_argument('--api-id', default=0, type=int, help='Telegram API ID. Default: not set', required=True)
    args_parser.add_argument('--api-hash', default=None, type=str, help='Telegram API Hash. Default: not set', required=True)
    args_parser.add_argument('--verbose', default=False, help='Enable verbose mode. Default: false.', required=False, action='store_true')
    args_parser.add_argument('--showusers', default=False, help='Show overlapping users. Default: false.',
        required=False, action='store_true')
    args_parser.add_argument('--peers', default=None, type=int, help='A list of chat peers to compare. Default: not set.',
        required=False, action='append', nargs='+')
    return args_parser.parse_args()


if __name__ == '__main__':

    logging.basicConfig(level=logging.INFO)
    arguments = get_args()

    if arguments.api_id > 0 and arguments.api_hash != '' and arguments.phone > 0:
        intersectionObj = Intersection(arguments)
        intersectionObj.parse_chats()
        intersectionObj.find_intersection()
    else:
        logging.error(f'Please provide the necessary values for the arguments')