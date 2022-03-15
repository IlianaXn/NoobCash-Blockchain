import jsonpickle
import numpy as np
import requests
import netifaces as ni
from dotenv import load_dotenv
import os
import time

load_dotenv()
N = int(os.getenv("N"))
CAPACITY = int(os.getenv("CAPACITY"))
MINING_DIFFICULTY = int(os.getenv("MINING_DIFFICULTY"))


def do_trans():
    # for localhost
    # addr = socket.gethostbyname(socket.gethostname())

    addr = ni.ifaddresses('eth1')[ni.AF_INET][0]['addr']

    # input('Press ENTER when you are sure mining is all over!')
    init = None
    num_trans = 0
    block_times = []
    initial_time = time.time()
    last_time = 0
    different_chains = False
    ignore = N - 1

    for addr_last in range(1, 6):
        for node_port in range(5000, 5002):
            if N == 5 and node_port == 5001:
                continue
            url = f'http://{addr[:-1]}{addr_last}:{node_port}/getChain/'
            r = requests.get(url)
            info = jsonpickle.decode(r.json(), keys=True)['chain']

            # we will ignore genesis and initial 100s transactions i.e. first 4 or 9 trans
            if addr_last == 1 and node_port == 5000:
                init = info
            if info != init:
                different_chains = True

    for block in init[1:]:
        for trans in block.listOfTransactions:
            if ignore:
                ignore -= 1
            else:
                num_trans += 1
                if trans.timestamp < initial_time:
                    initial_time = trans.timestamp
        if not ignore:
            if block_times:
                temp = block.timestamp - block_times[-1]
                block_times = block_times[:-1]
                block_times.extend([temp, block.timestamp])
            else:
                block_times.append(block.timestamp)
    last_time = init[-1].timestamp
    num_blocks = len(init)

    print('Different chains!' if different_chains else 'Same chains!')
    print('N =', N)
    print('Difficulty =', MINING_DIFFICULTY)
    print('Capacity =', CAPACITY)
    print('Total transactions =', num_trans)
    print('Total time for trans =', last_time - initial_time, 's')
    print('Total number of blocks =', num_blocks)
    print(f'Throughput = {num_trans / (last_time - initial_time)} t/s')
    print('Mean time of mining =', np.mean(block_times[:-1]), 's')


if __name__ == '__main__':
    do_trans()
