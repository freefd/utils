#!/usr/bin/env python3

from telethon import TelegramClient, sync
from telethon.tl.types import Channel
from telethon.tl.functions.channels import GetFullChannelRequest
from textwrap import wrap

import re, os
import networkx as nx

# Main configuration
config = {
    'telegram': {
        'api_id': '123456', # Client's API ID 
        'api_hash': 'bdaf62f128aeaa9a65b67a479d9ff413', # Client's API hash
        'phone_id': '+31201234567' # Client's phone
    },
    'graph': {
        'channels_ignore': [], # Channels to ignore
        'color': { # Colors for nodes (https://plantuml.com/en/color for more information)
            'client': 'gold',
            'channel': 'technology',
            'user': 'lavender'
        },
        'title': 'Telegram channels relationships', # Graph title
        'wordwrap_length': 15
    }
}

if __name__ == '__main__':

    # Create Client object and sign in
    client = TelegramClient(os.path.basename(__file__),
                            config['telegram']['api_id'],
                            config['telegram']['api_hash'])
    # Create Graph object
    graph = nx.Graph()

    client.start(config['telegram']['phone_id'])
    client_name = client.get_me().first_name

    # Add Client as root node
    graph.add_node(client_name, color=config['graph']['color']['client'])

    # For each not ignored channel in list of dialogs
    for channel in [dialog.entity for dialog in client.get_dialogs()
                        if isinstance(dialog.entity, Channel) and 
                           dialog.entity.id not in config['graph']['channels_ignore']]:

        # Get full information for a channel and word wrap its name
        channel_full_info = client(GetFullChannelRequest(channel=channel))
        channel_name = '\\n'.join(wrap(channel.title, config['graph']['wordwrap_length']))

        # Add channel ID as node with attributes 'title' and 'color', link it to the root node
        graph.add_node(channel.id, title=channel_name, color=config['graph']['color']['channel'])
        graph.add_edge(client_name, channel.id)

        # For each contact in full information 
        for contact_name in re.findall("@([A-z0-9_]{1,100})", channel_full_info.full_chat.about):

            # Add contact as node with attribute and link to the channel node
            graph.add_node(contact_name, color=config['graph']['color']['user'])
            graph.add_edge(contact_name, channel.id) 

    # Create Planutml file object
    plantumlFile = open("{}_telegram_graph.plantuml".format(client_name), 'w')

    # Write Plantuml header with graph title
    plantumlFile.write("@startuml\ntitle {}\nleft to right direction\n".format(config['graph']['title']))

    # For each node in graph
    for node in graph.nodes(data=True):

        # The node is channel if it has 'title' attribute
        if 'title' in node[1]:
            plantumlFile.write('frame {} as "{}" #{}\n'.format(node[0], node[1]['title'], node[1]['color']))

        # Otherwise, the node is contact
        else:
            plantumlFile.write('usecase {0} as "@{0}" #{1}\n'.format(node[0], node[1]['color']))

    # Link the nodes with each other by edges
    for edge in graph.edges():
        plantumlFile.write('{} 0--# {}\n'.format(edge[0], edge[1]))
    
    # Write Plantuml footer and close the file
    plantumlFile.write("@enduml")
    plantumlFile.close()