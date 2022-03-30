import time
import os
import uuid
from dotenv import load_dotenv
from Crypto.Hash import SHA256
from Block import Block
from collections import OrderedDict

load_dotenv()
N = int(os.getenv("N"))


class Blockchain:
    def __init__(self, node):
        self.chain = self.build_genesis(node)

    def build_genesis(self, node):
        if node.id == 0:
            times = time.time()
            trans_id = SHA256.new(('0' + node.wallet.to_dict()['public_key'].decode('utf-8')
                                   + str(100 * N) + str(times)).encode()).hexdigest()
            trans = OrderedDict({
                'transaction_id': trans_id,
                'sender_address': 0,
                'receiver_address': node.wallet.to_dict()['public_key'],
                'amount': 100 * N,
                'timestamp': times,
                'transaction_outputs': [OrderedDict({'id': uuid.uuid4(),
                                                     'transaction_id': trans_id,
                                                     'receiver': node.wallet.to_dict()['public_key'],
                                                     'amount': 100 * N})]
            })
            block = Block(index=1, previousHash=1)
            block.add_transaction(trans)
            node.NBCs[node.wallet.to_dict()['public_key']] = [trans['transaction_outputs'][0]]
            node.wallet.balance += 100 * N
            node.block = Block(index=2, previousHash=block.hash)
            return [block]
        else:
            return []

    def __getitem__(self, key):
        return self.chain[key]

    def __len__(self):
        return len(self.chain)

    def add_block(self, block):
        self.chain.append(block)

    def __eq__(self, other):
        if isinstance(other, Blockchain):
            return self.chain == other.chain
        return False