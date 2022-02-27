import time
import uuid
from collections import OrderedDict
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15


class Transaction:

    def __init__(self, sender_address, sender_private_key, receiver_address, value, UTXOs):
        self.sender_address = sender_address
        self.receiver_address = receiver_address
        self.amount = value
        self.timestamp = time.time()
        self.transaction_id = SHA256.new((sender_address.decode('utf-8') + receiver_address.decode('utf-8') +
                                          str(value) + str(self.timestamp)).encode())
        self.transaction_inputs = UTXOs
        self.transaction_outputs = self.create_transaction_outputs()
        self.signature = self.sign_transaction(sender_private_key)

    def create_transaction_outputs(self):
        outputs = []
        rest = sum([x['amount'] for x in self.transaction_inputs]) - self.amount
        if rest > 0:
            outputs.append(OrderedDict({
                'id': uuid.uuid4(),
                'trans_id': self.transaction_id.hexdigest(),
                'receiver': self.sender_address,
                'amount': rest,
            }))
        outputs.append(OrderedDict({
            'id': uuid.uuid4(),
            'trans_id': self.transaction_id.hexdigest(),
            'receiver': self.receiver_address,
            'amount': self.amount,
        }))
        return outputs

    def sign_transaction(self, p_k):
        private_key = RSA.importKey(p_k)
        cipher = pkcs1_15.new(private_key)
        signature = cipher.sign(self.transaction_id)
        self.transaction_id = self.transaction_id.hexdigest()
        return signature

    def __eq__(self, other):
        if isinstance(other, Transaction):
            return self.transaction_id == other.transaction_id and self.sender_address == other.sender_address and \
                   self.receiver_address == other.receiver_address and self.amount == other.amount and \
                   self.timestamp == other.timestamp and self.transaction_inputs == other.transaction_inputs and \
                   self.transaction_outputs == other.transaction_outputs and self.signature == other.signature
        return False

    def to_dict(self):
        return OrderedDict({
            'transaction_id': self.transaction_id,
            'sender_address': self.sender_address,
            'receiver_address': self.receiver_address,
            'amount': self.amount,
            'timestamp': self.timestamp,
            'transaction_inputs': self.transaction_inputs,
            'transaction_outputs': self.transaction_outputs,
            'signature': self.signature
        })

    def __str__(self):
        return str(self.to_dict())

    def __repr__(self):
        return repr(str(self.to_dict()))
