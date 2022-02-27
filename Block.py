import time
import hashlib
from collections import OrderedDict


class Block:
    def __init__(self, index, previousHash=1, nonce=0, listOfTransactions=None):
        if listOfTransactions is None:
            listOfTransactions = []
        self.index = index
        self.previousHash = previousHash
        self.listOfTransactions = listOfTransactions
        self.nonce = nonce
        self.timestamp = time.time()
        self.hash = self.myHash()

    def myHash(self):
        # calculate self.hash
        s = (str(self.index) + str(self.previousHash) + str(self.timestamp) + str(self.listOfTransactions) + str(
            self.nonce)).encode()               # convert string to bytes
        return hashlib.sha256(s).hexdigest()    # return hex value of hashed data

    def add_transaction(self, transaction):
        # add a transaction to the block
        self.listOfTransactions.append(transaction)

    def __eq__(self, other):
        if isinstance(other, Block):
            return self.index == other.index and self.previousHash == other.previousHash and \
                   self.listOfTransactions == other.listOfTransactions and self.nonce == other.nonce and \
                   self.timestamp == other.timestamp and self.hash == other.hash
        return False

    def to_dict(self):
        return OrderedDict({
            'index': self.index,
            'previousHash': self.previousHash,
            'listOfTransactions': self.listOfTransactions,
            'nonce': self.nonce,
            'timestamp': self.timestamp,
            'hash': self.hash
        })
