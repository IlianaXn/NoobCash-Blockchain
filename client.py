#!/usr/bin/python
import cmd
import json
import socket
import time
import requests
import netifaces as ni


class CLI(cmd.Cmd):
    prompt = 'noobcash>>'
    doc_header = 'Available commands:'

    def __init__(self, node_port):
        super(CLI, self).__init__()
        self.port = node_port
        # self.addr = socket.gethostbyname(socket.gethostname())
        self.addr = ni.ifaddresses('eth1')[ni.AF_INET][0]['addr']

    def preloop(self):
        self.do_help('')

    def do_view(self, line):
        """view
        View transactions of last block."""
        info = requests.get(f'http://{self.addr}:{self.port}/viewLast/')
        res_j = info.json()
        for x in res_j:
            print(f'Node {"GOD" if x["sender"] is None else x["sender"]} sent to Node {x["receiver"]} {x["amount"]} '
                  f'coins on {time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime(x["timestamp"]))}.')

    def do_t(self, line):
        """t [recipient_id] [amount]
        Send to recipient with [recipient_id] [amount] coins"""
        receiver_id, amount = map(int, line.split(' '))
        con = json.dumps({
            'id': receiver_id,
            'amount': amount
        })

        info = requests.post(f'http://{self.addr}:{self.port}/createTransaction/', json=con)
        if info.ok:
            print('Done!')
        else:
            print('Failed!')

    def do_balance(self, line):
        """balance
        Show balance of wallet."""
        info = requests.get(f'http://{self.addr}:{self.port}/balance/')
        res_j = info.json()
        print(res_j['balance'])

    def do_bye(self, line):
        """bye
        Exit client."""
        return True


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='Your port.')
    args = parser.parse_args()
    port = args.port
    CLI(port).cmdloop('Noobcash client! You can spend your money now!')