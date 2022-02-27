import socket
import jsonpickle
import numpy as np
import requests


def do_trans():
    addr = socket.gethostbyname(socket.gethostname())

    input('Press ENTER when you are sure mining is all over!')
    init = None
    num_trans = 0
    block_times = []
    initial_time = 0
    last_time = 0
    num_blocks = 0
    for node_port in range(5000, 5005):
        url = f'http://{addr}:{node_port}/getChain/'
        r = requests.get(url)
        info = jsonpickle.decode(r.json(), keys=True)['chain']

        # we will ignore genesis and initial 100s transactions i.e. first 4 or 9 trans
        if node_port == 5000:
            init = info
        num_trans = 0
        block_times = []
        ignore = 4
        first_t_flag = False

        for block in info[1:]:
            for trans in block.listOfTransactions:
                if ignore:
                    ignore -= 1
                elif not first_t_flag:
                    initial_time = trans.timestamp
                    first_t_flag = True
                    num_trans += 1
                else:
                    num_trans += 1
            if first_t_flag:
                if block_times:
                    temp = block.timestamp - block_times[-1]
                    block_times = block_times[:-1]
                    block_times.extend([temp, block.timestamp])
                else:
                    block_times.append(block.timestamp)
        last_time = info[-1].listOfTransactions[-1].timestamp
        if info == init:
            print('Same :)')
        else:
            print('Different :(')
        num_blocks = len(info)

    print('Total transactions =', num_trans)
    print('Total time for trans =', last_time - initial_time, 's')
    print('Total number of blocks =', num_blocks)
    print(f'Throughput = {num_trans / (last_time - initial_time)} t/s')
    print('Mean time of mining =', np.mean(block_times[:-1]), 's')


if __name__ == '__main__':
    do_trans()
