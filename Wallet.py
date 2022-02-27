from collections import OrderedDict
from Crypto.PublicKey import RSA


class Wallet:

    def __init__(self):
        self.public_key, self.private_key = self.generateKeyPair()
        self.balance = 0

    def wallet_balance(self):
        return self.balance

    def generateKeyPair(self):
        private_key_rsa = RSA.generate(2048)
        private_key = private_key_rsa.export_key('PEM')
        public_key_rsa = private_key_rsa.public_key()
        public_key = public_key_rsa.export_key('PEM')
        return public_key, private_key

    def to_dict(self):
        return OrderedDict({
            'public_key': self.public_key,
            'private_key': self.private_key
        })