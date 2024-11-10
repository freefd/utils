#!/usr/bin/env python3
''' Dynamic DNS for REG.RU provider '''

import json
import fcntl
import logging
import socket
import struct
import os
import sys
import argparse

from urllib.parse import quote, urlencode, urlparse

import requests

CONFIG = {
    'api': {
        'url': 'https://api.reg.ru',
        'path': '/api/regru2/zone',
        'username': 'username@maildomain.tld',
        'password': 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
    },
    'host': {
        'domain': 'domain.tld',
        'record': 'homerouter'
    },
    'remote_ip_check': {
        'url': 'https://ident.me',
        'path': '/json'
    },
    'hook': {
        'action': ['ifupdate', 'ifup', 'up', 'reload', 'dhcp4-change'],
        'wan_interface': 'eth0'
    }
}

def get_local_ip_address(**kwargs: str) -> str:
    ''' Get local IP address from interface '''

    logging.warning('Environment variable DHCP4_IP_ADDRESS was not found')

    interface = kwargs['interface']
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    packed_iface = struct.pack('256s', interface.encode('utf_8'))
    packed_addr = fcntl.ioctl(sock.fileno(), 0x8915, packed_iface)[20:24]
    logging.info(
        'Collected Local IP address: %s [%s]',
        socket.inet_ntoa(packed_addr), interface
    )
    return socket.inet_ntoa(packed_addr)

def get_remote_ip_address(**kwargs: str) -> str:
    ''' Detect remote IP address '''

    remote_ip_request = rest_request(
        method = 'GET',
        url = build_api_url(
            url = kwargs['url'],
            path = kwargs['path']
        )
    )
    if remote_ip_request.headers['content-type'].lower() == 'application/json':
        return remote_ip_request.json().get('ip')
    return remote_ip_request.text

def build_api_url(url: str = None, **kwargs: str) -> str:
    ''' Build API URL string '''

    url = urlparse(url)

    if ('username' in kwargs and 'password' in kwargs
        and kwargs['username'] and kwargs['password']):
        netloc = url.netloc.split('@')[-1]
        url = url._replace(
            netloc = \
            f"{quote(kwargs['username'])}:{quote(kwargs['password'])}@{netloc}"
        )

    if 'path' in kwargs and kwargs['path']:
        url = url._replace(path=kwargs['path'])

    if 'query' in kwargs and kwargs['query']:
        url = url._replace(query = urlencode(kwargs['query']))

    return url.geturl()

def rest_request(method: str=None, url: str=None, data: dict=None,
                    datatype: str=None) -> dict:
    ''' Request endpoint using REST '''

    logging.debug('Method: %s\nURL: %s\nParams: %s\nData type: %s',
                    method, url, data, datatype)

    session_object = requests.Session()
    try:
        if datatype == 'PARAMS':
            response = session_object.request(
                method,
                url,
                params = data,
                timeout = 60
            )
        else:
            response = session_object.request(
                method,
                url,
                data = data,
                timeout = 60
            )
        return response

    except requests.exceptions.HTTPError as errh:
        logging.critical(
            'Failed to get response from %s. HTTP error %s', url, errh)
        # sysexits.h: EX_DATAERR
        sys.exit(65)
    except requests.exceptions.ConnectionError as errc:
        logging.critical(
            'Failed to get response from %s. Connection error %s',
            url, errc)
        # sysexits.h: EX_UNAVAILABLE
        sys.exit(69)
    except requests.exceptions.Timeout as errt:
        logging.critical(
            'Failed to get response from %s. Timeout error %s', url, errt)
        # sysexits.h: EX_UNAVAILABLE
        sys.exit(69)
    except requests.exceptions.RequestException as errg:
        logging.critical(
            'Failed to get response from %s. Error %s', url, errg)
        # sysexits.h: EX_OSERR
        sys.exit(71)

    return None

def domain_exists(**kwargs: str) -> bool:
    ''' Check that domain exists '''

    domain_list_request = rest_request(
        method = 'POST',
        url = build_api_url(
            url = kwargs['url'],
            path = f"{kwargs['path']}/nop"
        ),
        data = {
            'input_data': json.dumps({
                'domains': [ { 'dname': kwargs['domain'] } ]
            }),
            'io_encoding': 'utf8',
            'input_format': 'json',
            'output_format': "json",
            'username': kwargs['username'],
            'password': kwargs['password']
        }
        )

    domain_list_response = domain_list_request.json()

    if 'answer' in domain_list_response:
        for domain in domain_list_response.get('answer', None).get('domains', None):
            if domain.get('dname') == kwargs['domain']:
                return True
    return False

def record_exists(**kwargs: str) -> tuple[bool, bool]:
    ''' Check that A record exists in zone '''

    record_list_request = rest_request(
        method = 'POST',
        url = build_api_url(
            url = kwargs['url'],
            path = f"{kwargs['path']}/get_resource_records"
        ),
        data = {
            'input_data': json.dumps({
                'domains': [ { 'dname': kwargs['domain'] } ],
                'output_content_type': 'plain'
            }),
            'username': kwargs['username'],
            'password': kwargs['password'],
            'input_format': 'json',
        }
    )

    record_list_response = record_list_request.json()

    if 'answer' in record_list_response:
        for domain in record_list_response.get('answer').get('domains'):
            if domain.get('dname') == kwargs['domain']:
                logging.info('Domain has been found: %s',
                    kwargs['domain'])
                logging.info('Looking for the record: %s [%s]',
                        kwargs['record'], kwargs['wan_ip'])
                for record in domain.get('rrs'):
                    if (kwargs['record'] == record['subname']
                        and kwargs['wan_ip'] == record['content']):
                        logging.info('Record has been found: %s [%s]',
                            record['subname'], record['content'])
                        return (True, True)
                    elif kwargs['record'] == record['subname']:
                        logging.info('Found record %s: %s',
                            record['subname'], record['content'])
                        return (True, False)

    return (False, False)

def record_delete(**kwargs: str) -> bool:
    ''' Delete A record in zone '''

    record_delete_request = rest_request(
        method = 'POST',
        url = build_api_url(
            url = kwargs['url'],
            path = f"{kwargs['path']}/remove_record"
        ),
        data = {
            'input_data': json.dumps({
                'username': kwargs['username'],
                'password': kwargs['password'],
                'domains': [ { 'dname': kwargs['domain'] } ],
                'subdomain': kwargs['record'],
                'record_type': 'A',
                'output_content_type': 'plain'
            }),
            'input_format': 'json',
        }
    )

    if record_delete_request.json().get('result') == 'success':
        return True

    return False

def record_create(**kwargs: str) -> bool:
    ''' Create A record in zone '''

    record_create_request = rest_request(
        method = 'POST',
        url = build_api_url(
            url = kwargs['url'],
            path = f"{kwargs['path']}/add_alias"
        ),
        data = {
            'input_data': json.dumps({
                'domains': [ { 'dname': kwargs['domain'] } ],
                'subdomain': kwargs['record'],
                'ipaddr': kwargs['wan_ip'],
                'output_content_type': 'plain'
            }),
            'username': kwargs['username'],
            'password': kwargs['password'],
            'input_format': 'json',
        }
    )

    if record_create_request.json().get('result') == 'success':
        return True

    return False

if __name__ == '__main__':

    args = argparse.ArgumentParser(
        description='Dynamic DNS for REG.RU provider',
    )

    args.add_argument(
        '--verbose', '-v', help='Enable verbose output. Default: 0.\n\n',
        required=False, default=0, action='count'
    )

    args.add_argument(
        'interface', type=str, help='Affected interface'
    )

    args.add_argument(
        'action', type=str, help='Action applied to an interface'
    )


    # Adjust log level
    args = args.parse_args()
    args.verbose = 30 - (10 * int(args.verbose)) if int(
        args.verbose) > 0 else 20

    logging.basicConfig(
        format = '[%(asctime)s] %(levelname)s %(module)s: [DDNS] %(message)s',
        level = args.verbose
    )

    if (args.interface == CONFIG['hook']['wan_interface']
        and args.action in CONFIG['hook']['action']):

        CONFIG['wan_ip'] = os.environ.get(
                            'DHCP4_IP_ADDRESS',
                            get_local_ip_address(
                                interface = CONFIG['hook']['wan_interface']
                            )
        )

        logging.info('WAN IP is set to: %s', CONFIG['wan_ip'])

        REMOTE_WAN_IP = get_remote_ip_address(
            url = CONFIG['remote_ip_check']['url'],
            path = CONFIG['remote_ip_check']['path']
        )

        if CONFIG['wan_ip'] != REMOTE_WAN_IP:
            logging.info('NAT is detected: %s <-> %s',
                            CONFIG['wan_ip'], REMOTE_WAN_IP)

            CONFIG['wan_ip'] = REMOTE_WAN_IP
            logging.info('WAN IP is updated to: %s', CONFIG['wan_ip'])

        if not domain_exists(
            url = CONFIG['api']['url'],
            path = CONFIG['api']['path'],
            username = CONFIG['api']['username'],
            password = CONFIG['api']['password'],
            domain = CONFIG['host']['domain']
        ):
            logging.critical('Domain has not been found: %s',
                                CONFIG['host']['domain'])
            # sysexits.h: EX_UNAVAILABLE
            sys.exit(69)

        RECORD_EXISTS, RECORD_UPTODATE = record_exists(
            url = CONFIG['api']['url'],
            path = CONFIG['api']['path'],
            username = CONFIG['api']['username'],
            password = CONFIG['api']['password'],
            domain = CONFIG['host']['domain'],
            record = CONFIG['host']['record'],
            wan_ip = CONFIG['wan_ip']
        )

        if RECORD_EXISTS and RECORD_UPTODATE:
            logging.info('Record update is not required: %s [%s]',
                CONFIG['host']['record'], CONFIG['wan_ip']
            )

        elif RECORD_EXISTS and not RECORD_UPTODATE:
            logging.info('Record update is required: %s [%s]',
                    CONFIG['host']['record'], CONFIG['wan_ip']
            )

            if record_delete(
                url = CONFIG['api']['url'],
                path = CONFIG['api']['path'],
                username = CONFIG['api']['username'],
                password = CONFIG['api']['password'],
                domain = CONFIG['host']['domain'],
                record = CONFIG['host']['record'],
            ):
                logging.info('Outdated record was deleted: %s',
                    CONFIG['host']['record']
                )
            else:
                logging.info('Failed to delete outdated record: %s',
                    CONFIG['host']['record']
                )
                # sysexits.h: EX_CONFIG
                sys.exit(78)

            if record_create(
                url = CONFIG['api']['url'],
                path = CONFIG['api']['path'],
                username = CONFIG['api']['username'],
                password = CONFIG['api']['password'],
                domain = CONFIG['host']['domain'],
                record = CONFIG['host']['record'],
                wan_ip = CONFIG['wan_ip']
            ):
                logging.info('Record has been created: %s [%s]',
                    CONFIG['host']['record'], CONFIG['wan_ip']
                )
            else:
                logging.info('Failed to create record: %s [%s]',
                    CONFIG['host']['record'], CONFIG['wan_ip']
                )
                # sysexits.h: EX_CONFIG
                sys.exit(78)

        else:
            logging.info('Record does not exist for: %s [%s]',
                    CONFIG['host']['record'], CONFIG['wan_ip'])

            if record_create(
                url = CONFIG['api']['url'],
                path = CONFIG['api']['path'],
                username = CONFIG['api']['username'],
                password = CONFIG['api']['password'],
                domain = CONFIG['host']['domain'],
                record = CONFIG['host']['record'],
                wan_ip = CONFIG['wan_ip']
            ):
                logging.info('Record has been created: %s [%s]',
                    CONFIG['host']['record'], CONFIG['wan_ip']
                )
            else:
                logging.info('Failed to create record: %s [%s]',
                    CONFIG['host']['record'], CONFIG['wan_ip']
                )
                # sysexits.h: EX_CONFIG
                sys.exit(78)
    else:
        logging.critical(
            'Existing due to foreign interface or action: %s [%s]',
            args.interface, args.action
        )
