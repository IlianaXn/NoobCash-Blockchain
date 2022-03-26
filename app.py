import netifaces as ni
import json
import socket
import threading
import jsonpickle
import requests
import os
from flask import Flask, jsonify, request, Response, abort
from flask_cors import CORS
from Node import Node
from dotenv import load_dotenv
from werkzeug.exceptions import HTTPException
import time
from Transaction import Transaction

load_dotenv()
N = int(os.getenv("N"))
bootstrap_ip = os.getenv("BOOTSTRAP_IP")
bootstrap_port = int(os.getenv("BOOTSTRAP_PORT"))
app = Flask(__name__)
CORS(app)


# execute transactions in given file matching our node_id
def read_trans():
    with app.app_context():
        with open(f'transactions/{N}nodes/transactions{my_node.id}.txt') as f, \
                open(f'results/result_{my_node.id}.txt', "w") as test_file:

            trans_id = 0
            while True:
                activated_nodes = 0
                for node_NBCs in my_node.NBCs.values():
                    if len(node_NBCs) != 0:
                        activated_nodes += 1
                if activated_nodes == N:
                    break

            print('So it begins!')
            for line in f:
                trans_id += 1
                receiver, amount = line.split(' ')
                receiver_id = int(receiver[2:])
                amount = int(amount)
                if amount > N * 100:
                    print("Not enough NBCs in the whole world!")
                    test_file.write(f'Trans {trans_id} failed\n')
                    print(f'Trans {trans_id} failed!')
                    continue

                receiver_addr = my_node.ring[receiver_id][2]

                flag = my_node.create_transaction(receiver_addr, amount)
                if flag:
                    test_file.write(f'Trans {trans_id} ok\n')
                    print(f'Trans {trans_id} ok!')
                else:
                    test_file.write(f'Trans {trans_id} failed\n')
                    print(f'Trans {trans_id} failed!')
            test_file.close()


@app.route('/')
def hello():
    return 'Hi, I am alive!'


# return all transactions contained in the last block of blockchain
@app.route('/transactions/get', methods=['GET'])
def get_transactions():
    info = []
    for x in my_node.transactions:
        info.append({
            'sender': find_id(my_node.ring, x.sender_address),
            'receiver': find_id(my_node.ring, x.receiver_address),
            'amount': x.amount,
            'timestamp': x.timestamp
        })
    return jsonify(info=info, length=len(info)), 200


# not used in bootstrap node
# update ring based on info sent by bootstrap node
@app.route('/setRing/', methods=['POST'])
def updateRing():
    ring = jsonpickle.decode(request.json)
    if ring is None:
        abort(404, description="Parameter not found in setRing endpoint")
    my_node.set_ring(ring)
    if test:
        thread = threading.Thread(target=read_trans, name='make transactions')
        thread.start()
    return Response(status=200)


# only for bootstrap node
# insert new node into ring and return its id and blockchain so far
@app.route('/registerNode/', methods=['POST'])
def registerNode():
    info = jsonpickle.decode(request.json)
    if info is None:
        abort(404, description="Parameter not found in registerNode endpoint")

    registered_node_id, my_chain = my_node.register_node_to_ring(info['public_key'],
                                                                 info['ip'], info['port'])
    updated_info = {
        'node_id': registered_node_id,
        'chain': my_chain
    }
    if updated_info['node_id'] == N - 1 and test:
        thread = threading.Thread(target=read_trans, name='make transactions')
        thread.start()
    return jsonify(jsonpickle.encode(updated_info))


# create a transaction sending given amount coins to node with given id
@app.route('/createTransaction/', methods=['POST'])
def create_transaction():
    info = json.loads(request.json)
    if info is None:
        abort(404, description="Parameter not found in createTransaction endpoint")
    elif info['id'] not in range(0, N):
        return Response(status=400)
    else:
        receiver_addr = my_node.ring[info['id']][2]
        flag = my_node.create_transaction(receiver_addr, info['amount'])
        if flag:
            return Response(status=200)
        else:
            return Response(status=400)


# receive (broadcast) transaction executed by someone except for me
@app.route('/addTransaction/', methods=['POST'])
def add_transaction():
    while not my_node.chain:
        pass
    info = jsonpickle.decode(request.json)
    if info is None:
        abort(404, description="Parameter not found in addTransaction endpoint")
    flag = my_node.add_transaction_to_block(info)
    if flag:
        return Response(status=200)
    else:
        return Response(status=400)


# receive (broadcast) block found by someone except for me
@app.route('/addBlock/', methods=['POST'])
def add_block():
    info = jsonpickle.decode(request.json)
    if info is None:
        abort(404, description="Parameter not found in addBlock endpoint")
    flag = my_node.create_new_block(info)
    if flag:
        return Response(status=200)
    else:
        return Response(status=400)


# return the length of my blockchain
@app.route('/chainLength/', methods=['GET'])
def length_of_chain():
    return jsonify(length=len(my_node.chain)), 200


# return my blockchain
@app.route('/getChain/', methods=['GET'])
def get_chain():
    return jsonify(jsonpickle.encode(keys=True, value={'chain': my_node.chain})), 200


# return the balance of my wallet
@app.route('/balance/', methods=['GET'])
def get_balance():
    return jsonify(balance=my_node.wallet.wallet_balance()), 200


# return all transactions contained in the last block of blockchain
@app.route('/viewLast/', methods=['GET'])
def get_last_trans():
    block_trans = my_node.chain[-1].listOfTransactions
    info = []
    for x in block_trans:
        if isinstance(x, Transaction):
            info.append({
                'sender': find_id(my_node.ring, x.sender_address),
                'receiver': find_id(my_node.ring, x.receiver_address),
                'amount': x.amount,
                'timestamp': x.timestamp
            })
        else:
            info.append({
                'sender': find_id(my_node.ring, x['sender_address']),
                'receiver': find_id(my_node.ring, x['receiver_address']),
                'amount': x['amount'],
                'timestamp': x['timestamp']
            })
    return jsonify(info), 200


# return id of node with key as public key
def find_id(ring, key):
    for i in range(len(ring)):
        if ring[i][2] == key:
            return i


# announce myself to bootstrap node
def announce_me():
    with app.app_context():
        info = {
            'public_key': my_node.wallet.public_key,
            'ip': my_node.ip,
            'port': my_node.port
        }
        con = jsonpickle.encode(info)
        res = requests.post(f'http://{bootstrap_ip}:{bootstrap_port}/registerNode/', json=con)
        res_j = jsonpickle.decode(res.json())
        my_node.update(res_j['node_id'], res_j['chain'])


@app.errorhandler(HTTPException)
def handle_exception(e):
    # start with the correct headers and status code from the error
    response = e.get_response()
    # replace the body with JSON
    response.data = json.dumps({
        "code": e.code,
        "name": e.name,
        "description": e.description,
    })
    response.content_type = "application/json"
    return response


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    parser.add_argument('-id', '--id', default=None, type=int, help='id, given for bootstrap')
    parser.add_argument('-test', '--test', action='store_true', help='run tests with given transaction files')

    args = parser.parse_args()

    node_id = args.id
    port = args.port
    test = args.test

    # for localhost
    #host_name = socket.gethostname()
    #host_ip = socket.gethostbyname(host_name)

    host_ip = ni.ifaddresses('eth1')[ni.AF_INET][0]['addr']

    my_node = Node(node_id, host_ip, port)

    if node_id == 0:
        my_node.ring = [(host_ip, port, my_node.wallet.public_key)]
    else:
        timer = threading.Timer(2, announce_me)
        timer.start()

    app.run(host=host_ip, port=port, threaded=True)