import hashlib
import secrets
import time
import os
import flask
import jsonpickle
import threading
import requests
from flask import current_app
from Crypto.Signature import pkcs1_15
from Crypto.PublicKey import RSA
from requests import RequestException
from Block import Block
from Wallet import Wallet
from Transaction import Transaction
from Crypto.Hash import SHA256
from dotenv import load_dotenv
from Blockchain import Blockchain

# retrieve from .env file
load_dotenv()
N = int(os.getenv("N"))
CAPACITY = int(os.getenv("CAPACITY"))
MINING_DIFFICULTY = int(os.getenv("MINING_DIFFICULTY"))


class Node:
    """
        A class used to represent a node in NoobCash blockchain network

        Attributes
        ----------
        id : int
            an integer which uniquely identifies the node and it is assigned by the bootstrap node
            once it is inserted in the network
        ip : str
            the IPv4 address of the node
        port : int
            the port on which the application NoobCash listens
        NBCs : dict[Bytes, list[dict[]]]
            a dict which contains the unspent transaction outputs for every node in the network
            key = public_key and value = list of UTXOs (default {})
        wallet : Wallet
            the wallet of the node
        ring : list[(str, int, bytes)]
            a list which contains tuples of (ip, port, public_key) and index of list corresponds
            to id of each node in the network (default [])
        transactions : list[Transaction]
            a list which contains the transactions collected by the node but not yet added to the
            blockchain (default [])
        self.block : Block
            current block to be filled with collected transactions (default None)
        self.chain : Blockchain
            the blockchain of NoobCash network
        mining_flag : bool
            a flag that indicates whether node is currently mining or not (default False)
        self.lock : threading.Lock
            a lock used to ensure isolation between procedures which change same objects
        self.mining_lock : threading.Lock
            a lock used to assure isolation of mining procedure
        self.resolve_lock : threading.Lock
            a lock used to assure isolation of resolving conflicts procedure

        Methods
        -------
        create_wallet()
            Returns the wallet of the node
        register_node_to_ring(public_key, ip, port)
            Registers node to the NoobCash network and returns its id and bootstrap's current blockchain
        update(node_id, chain)
            Sets node's id to node_id and its chain to given chain (provided by bootstrap node)
        set_ring(ring)
            Sets node's ring to given ring (provided by bootstrap node)
        broadcast_ring(app)
            Sends network ring to all nodes in the network (executed only by bootstrap node)
        broadcast_transaction(transaction)
            Sends transaction to all nodes in the network
        broadcast_block(block)
            Sends mined block to all nodes in the network
        create_transaction(receiver, amount)
            Crafts new transaction with amount coins sent to receiver if node has enough coins
        validate_transaction(transaction)
            Checks validity of transactions based on signature, id, inputs, and outputs
        update_NBCs(transaction)
            Updates NBCs of sender and receiver, and if node is either of them, adjusts wallet's balance
        add_transaction_to_block(transaction, app=None)
            Adds a new transaction to current block if it's valid, and initiates mining in case of
            full block
        add_transactions_to_block()
            Adds pending transactions to current block in bulk
        create_new_block(block)
            Adds block to blockchain if it's valid, and modifies NBCs according to contained transactions
            within it
        validate_block(block)
            Checks validity of block based on its hash, satisfaction of mining difficulty, hash of previous block
            in chain, and valid transactions within it.
        mine_block(block, app)
            Mines block and if it succeeds, broadcasts block, updates blockchain and processes pending transactions
        proof_of_work(block)
            Finds nonce s.t. hash of block satisfies mining difficulty
        validate_chain(chain)
            Checks validity of chain based on contained transactions within it, and updates NBCs of nodes
        recalculate_NBCs(chain)
            Replaces blockchain with chain and recalculates NBCs of nodes and pending transactions according to
            included transactions
        resolve_conflicts(app)
            Finds chain of greatest length across the network and replaces node's chain with it
        """

    def __init__(self, node_id, ip, port):
        """
        Parameters
        ----------
        node_id : int
            The id of the node
        ip : str
            The IPv4 address of the node
        port : int
            The port on which NoobCash application listens on
        """
        self.id = node_id
        self.ip = ip
        self.port = port
        self.NBCs = {}  # key = public_key, value = [UTXOs]
        self.wallet = self.create_wallet()
        self.ring = []  # (ip, port, public_key)
        self.transactions = []
        self.block = None
        self.chain = Blockchain(self)
        self.mining_flag = False
        self.lock = threading.Lock()
        self.mining_lock = threading.Lock()
        self.resolve_lock = threading.Lock()

    def create_wallet(self) -> Wallet:
        """Creates the wallet of the node.

        Returns
        ------
        Wallet
            the created wallet of the node.
        """

        return Wallet()

    def register_node_to_ring(self, public_key: bytes, ip: str, port: int) -> (int, Blockchain):
        """Appends new node to ring and broadcasts the updated ring to all nodes if all nodes
        have joined (executed only by the bootstrap node).

        Parameters
        ----------
        public_key : bytes
            The public_key of the incoming node.
        ip : str
            The IPv4 address of the incoming node.
        port : int
            The port on which the NoobCash application of the incoming node listens.

        Returns
        -------
        int
            the incoming node's assigned id
        Blockchain
            the bootstrap's current chain
        """

        node_id = len(self.ring)
        self.ring.append((ip, port, public_key))
        self.NBCs[public_key] = []
        if node_id == N - 1:
            app = current_app._get_current_object()
            thread = threading.Thread(target=self.broadcast_ring,
                                      name='broadcasting info and giving money',
                                      args=[app])
            thread.start()
        return node_id, self.chain

    def update(self, node_id: int, chain: Blockchain) -> None:
        """Sets id and chain to given node_id and chain by bootstrap node, respectively.

        Parameters
        ----------
        node_id : int
            The assigned id by the bootstrap node.
        chain : Blockchain
            The bootstrap's current chain.
        """

        with self.lock:
            self.id = node_id
            self.chain = chain
            if self.chain:
                self.block = Block(index=self.chain[-1].index + 1,
                                   previousHash=self.chain[-1].hash)

    def set_ring(self, ring: list[(str, int, bytes)]) -> None:
        """Replaces node's ring with the given ring by bootstrap node and expands
        NBCs dictionary accordingly for all nodes in the ring.

        Parameters
        ----------
        ring : list[(str, int, bytes)]
            The network ring provided by the bootstrap node.
        """

        with self.lock:
            self.ring = ring
            for x in self.ring:
                try:
                    self.NBCs[x[2]]
                except KeyError:
                    self.NBCs[x[2]] = []
            self.chain = self.chain if self.validate_chain(self.chain) else []

    def broadcast_ring(self, app: flask.app.Flask) -> None:
        """Broadcasts the network ring to all other nodes in the network (executed only
        by the bootstrap node).

        Parameters
        ----------
        app : flask.app.Flask
            The Flask environment in order to be able to create http requests.
        """

        with app.app_context():
            con = jsonpickle.encode(self.ring)
            for x in self.ring[1:]:
                addr = f'http://{x[0]}:{x[1]}/setRing/'
                try:
                    threading.Thread(target=requests.post,
                                     kwargs={'url': addr, 'json': con}, ).start()
                except RequestException as e:
                    print(f'Exception {e} occurred while '
                          f'broadcasting ring to node {x[0]}:{x[1]}')
            for x in self.ring[1:]:
                self.create_transaction(x[2], 100)

    def broadcast_transaction(self, transaction: Transaction) -> None:
        """Broadcasts a new transaction to all other nodes in the network.

        Parameters
        ----------
        transaction : Transaction
            The newly crafted transaction to be broadcast to the network.
        """

        con = jsonpickle.encode(transaction)
        for x in self.ring:
            if x[2] == self.ring[self.id][2]:
                continue
            addr = f'http://{x[0]}:{x[1]}/addTransaction/'
            try:
                threading.Thread(target=requests.post,
                                 kwargs={'url': addr, 'json': con}, ).start()
            except RequestException as e:
                print(f'Exception {e} occurred while broadcasting transaction '
                      f'to node {x[0]}:{x[1]}')

    def broadcast_block(self, block: Block) -> None:
        """Broadcasts a mined block to all other nodes in the network.

        Parameters
        ----------
        block : Block
            The newly mined block to be broadcast to the network.
        """
        con = jsonpickle.encode(block)
        for x in self.ring:
            if x[2] == self.ring[self.id][2]:
                continue
            addr = f'http://{x[0]}:{x[1]}/addBlock/'
            try:
                threading.Thread(target=requests.post,
                                 kwargs={'url': addr, 'json': con},
                                 ).start()
            except RequestException as e:
                print(f'Exception {e} occurred while broadcasting '
                      f'block to node {x[0]}:{x[1]}')

    def create_transaction(self, receiver: bytes, amount: int) -> bool:
        """Crafts a new transaction from the current node to receiver with amount coins
        if the current node has enough coins.

        Parameters
        ----------
        receiver : bytes
            The public_key of the receiver of the coins.
        amount : int
            The amount of coins to be transferred.

        Returns
        -------
        bool
            whether the transaction could be or not be crafted due to sufficiency of available
            coins.
        """
        with self.lock:
            count = 0
            trans_in = []
            for x in self.NBCs[self.wallet.public_key]:
                count += x['amount']
                trans_in.append(x)
                if count >= amount:
                    break
            if count < amount or receiver not in set(self.NBCs.keys()):
                return False
            trans = Transaction(self.wallet.public_key,
                                self.wallet.private_key,
                                receiver, amount, trans_in)
        self.broadcast_transaction(trans)
        self.add_transaction_to_block(trans)
        return True

    def validate_transaction(self, transaction: Transaction) -> bool:
        """Checks validity of a transactions based on validity of its signature, not duplicate id
        validity of inputs (not double spent), and correct outputs according to transferred amount and
        inputs.

        Parameters
        ----------
        transaction : Transaction
            The transaction to be checked for validity.

        Returns
        -------
        bool
            whether the transaction was valid or not. It wouldn't be valid in each of the following cases:
            - Invalid signature (transaction_id doesn't equal decrypted signature based on public key of sender)
            - Duplicate id, i.e. transaction was received in the past
            - Invalid inputs (sender has already spent or never had the inputs to conclude the transaction)
            - Invalid outputs (output to receiver doesn't equal transferred amount or output to sender doesn't
            equal the change)
        """
        public_key = RSA.importKey(transaction.sender_address)
        cipher = pkcs1_15.new(public_key)  # binary form
        trans_id = SHA256.new((transaction.sender_address.decode('utf-8') +
                               transaction.receiver_address.decode('utf-8') +
                               str(transaction.amount) +
                               str(transaction.timestamp))
                              .encode())
        try:
            cipher.verify(trans_id, transaction.signature)
        except ValueError:
            print('Transaction not validated because of a wrong signature')
            return False
        for x in self.chain[1:]:
            for t in x.listOfTransactions:
                if transaction.transaction_id == t.transaction_id:
                    print('Transaction not validated because it is a duplicate')
                    return False
        count = 0
        trans_in = transaction.transaction_inputs
        trans_out = transaction.transaction_outputs
        sender = transaction.sender_address
        for x in trans_in:
            if x not in self.NBCs[sender]:
                print('Not enough NBCs to implement transaction')
                return False
            else:
                count += x['amount']
        # check outputs
        if transaction.amount != trans_out[-1]['amount']:
            return False
        elif len(trans_out) != 1 and (count - transaction.amount) != trans_out[0]['amount']:
            return False
        return True

    def update_NBCs(self, transaction: Transaction) -> None:
        """Based on the transactions modifies the NBCs of the sender and receiver, and in case
        the current node is either of them, updates its wallet's balance.

        Parameters
        ----------
        transaction : Transaction
            The transaction whose outputs are to be processed.
        """
        sender = transaction.sender_address
        receiver = transaction.receiver_address
        t_out = transaction.transaction_outputs
        t_in = transaction.transaction_inputs
        if len(t_out) != 1:
            self.NBCs[sender].append(t_out[0])
        set_out = set([x['id'] for x in t_in])
        self.NBCs[sender] = list(filter(lambda x: x['id'] not in set_out,
                                        self.NBCs[sender]))
        self.NBCs[receiver].append(t_out[- 1])
        if sender == self.wallet.public_key:
            self.wallet.balance -= transaction.amount
        if receiver == self.wallet.public_key:
            self.wallet.balance += transaction.amount

    def add_transaction_to_block(self, transaction: Transaction, app: flask.app.Flask = None) -> bool:
        """Adds a transactions to the current block if it's valid, and in case of a full block, initiates
        mining.

        Parameters
        ----------
        transaction : Transaction
            The candidate transaction to be added to the current block.
        app: flask.app.Flask
            The Flask environment in order to be able to create http requests.

        Returns
        -------
        bool
            whether the transaction was added to the block. It wouldn't be in case it was invalid.
        """
        if not app:
            app = current_app._get_current_object()
        with app.app_context():
            with self.lock:
                curr_block_size = len(self.block.listOfTransactions)
                if self.validate_transaction(transaction):
                    self.transactions.append(transaction)
                    self.update_NBCs(transaction)
                    if curr_block_size != CAPACITY:
                        self.block.add_transaction(transaction)
                elif transaction in self.transactions and transaction not in self.block.listOfTransactions and \
                        curr_block_size != CAPACITY:
                    self.block.add_transaction(transaction)
                else:
                    return False
                print('Transaction added in current block')
            if len(self.block.listOfTransactions) == CAPACITY and not self.mining_flag:
                thread = threading.Thread(target=self.mine_block, name='mining', args=[self.block, app])
                thread.start()
            return True

    def add_transactions_to_block(self) -> None:
        """Adds a bunch of pending transactions to the (newly created) current block.
        """
        for t in self.transactions:
            curr_block_size = len(self.block.listOfTransactions)
            if curr_block_size != CAPACITY - 1:
                self.block.add_transaction(t)
            elif curr_block_size == CAPACITY - 1:
                app = current_app._get_current_object()
                threading.Thread(target=self.add_transaction_to_block,
                                 args=[t, app], ).start()
                break

    def create_new_block(self, block: Block) -> bool:
        """Adds a new block to the chain if it's valid, updates the NBCs according to first-time seen
        transactions within the block, updates pending transactions, and creates and fills a new current
        block.

        Parameters
        ----------
        block : Block
            The candidate block to be added to the chain.

        Returns
        -------
        bool
            whether the block was added to the chain. It wouldn't be in case it was invalid.
        """
        with self.lock:
            if self.validate_block(block):
                self.chain.add_block(block)
                print('New block added to chain')
                block_transactions = block.listOfTransactions
                for t in block_transactions:
                    if t not in self.transactions:
                        self.update_NBCs(t)
                self.transactions = [x for x in self.transactions if x not in block_transactions]
                self.block = Block(index=self.chain[-1].index + 1,
                                   previousHash=self.chain[-1].hash)
                self.add_transactions_to_block()
                return True
            return False

    def validate_block(self, block: Block) -> bool:
        """Checks validity of block based on its hash, satisfaction of mining difficulty, hash of previous block
        in chain, and valid transactions within it. In case of inconsistent hash of previous block, calls for resolution
        of conflict.

        Parameters
        ----------
        block : Block
            The block to be checked for validity.

        Returns
        -------
        bool
            whether the block was valid or not. It wouldn't be valid in each of the following cases:
            - Invalid hash (hash doesn't occur from block's attributes)
            - Unsatisfactory hash (hash doesn't start with MINING_DIFFICULTY in number zeros)
            - Inconsistent previous hash (previous hash doesn't belong to previous block in the chain)
            - Invalid transactions within it
        """
        s = (str(block.index) + str(block.previousHash) + str(block.timestamp) +
             str(block.listOfTransactions) + str(block.nonce)).encode()
        computed_hash = hashlib.sha256(s).hexdigest()
        if computed_hash != block.hash:
            print('Invalid block hash')
            return False
        if not (block.hash.startswith('0' * MINING_DIFFICULTY)):
            print('Mining difficulty not reached')
            return False
        if block.previousHash != self.chain[-1].hash:
            print('Different previous hashes, must resolve conflicts')
            app = current_app._get_current_object()
            threading.Thread(target=self.resolve_conflicts, args=[app]).start()
            return False
        for t in block.listOfTransactions:
            if (t not in self.transactions) and not self.validate_transaction(t):
                print('Invalid transaction contained in block')
                return False
        return True

    def mine_block(self, block: Block, app: flask.app.Flask) -> None:
        """Mines the block and if it succeeds, broadcasts the block,
        updates blockchain and processes pending transactions.

        Parameters
        ----------
        block : Block
            The candidate block to be added to the chain.
        app: flask.app.Flask
            The Flask environment in order to be able to create http requests.
        """
        with self.mining_lock:
            if str(block.myHash()).startswith('0' * MINING_DIFFICULTY):
                return
            print('Proof of work begins')
            with app.app_context():
                self.mining_flag = True
                mined = self.proof_of_work(block)
                if mined:
                    print('Proof of work completed')
                    with self.lock:
                        if self.chain[-1].index + 1 == mined.index:
                            print('I am the winner!')
                            self.chain.add_block(mined)
                            self.broadcast_block(mined)
                            block_transactions = mined.listOfTransactions
                            self.transactions = [x for x in self.transactions if x not in block_transactions]
                            self.block = Block(index=self.chain[-1].index + 1,
                                               previousHash=self.chain[-1].hash)
                            self.add_transactions_to_block()
                        else:
                            print('Was very close to winning')
                else:
                    print('Lost!')
                self.mining_flag = False

    def proof_of_work(self, block: Block) -> Block:
        """Tries random values of block's nonce until block's hash starts with MINING_DIFFICULTY in number
        zeros. If anytime index of last block in the chain is different from block's index, someone found
        a new block and mining was unsuccessful.

        Parameters
        ----------
        block : Block
            The block whose nonce has to be modified until its hash is the desired one.

        Returns
        -------
        Block
            The mined block in case mining was successful or None in case mining was interrupted.
        """
        block.nonce = secrets.token_bytes(4)
        block.timestamp = time.time()
        while self.chain[-1].index + 1 == block.index:
            if not str(block.myHash()).startswith('0' * MINING_DIFFICULTY):
                block.nonce = secrets.token_bytes(4)
                block.timestamp = time.time()
            else:
                block.hash = block.myHash()
                return block
        return None

    def validate_chain(self, chain: Blockchain) -> bool:  # called when incoming to network for first time
        """Checks validity of chain based on validity of included transactions and updates NBCs of nodes
         according to them.

        Parameters
        ----------
        chain : Blockchain
            The chain to be checked for validity.

        Returns
        -------
        bool
            whether the chain was valid or not. It wouldn't be valid in case an included transaction was
            invalid.
        """
        gen = chain[0]
        trans = gen.listOfTransactions[0]
        self.NBCs[trans['receiver_address']] = [trans['transaction_outputs'][0]]
        for x in chain[1:]:
            for t in x.listOfTransactions:
                if self.validate_transaction(t):
                    self.update_NBCs(t)
                else:
                    print('Invalid chain due to invalid transaction in it.')
                    return False
        return True

    # given a new chain recalculate node's NBCs
    def recalculate_NBCs(self, chain: Blockchain) -> None:
        """Replaces blockchain with chain and recalculates NBCs of nodes and pending transactions according to
        included transactions.

        Parameters
        ----------
        chain : Blockchain
            The chain whose transactions are to be processed.
        """
        back_trans = self.transactions
        for k in self.NBCs:
            self.NBCs[k] = []
        self.chain = chain
        self.block = Block(index=self.chain[-1].index + 1,
                           previousHash=self.chain[-1].hash)
        list_out = []
        gen = chain[0]
        trans = gen.listOfTransactions[0]
        self.NBCs[trans['receiver_address']] = [trans['transaction_outputs'][0]]
        for block in self.chain[1:]:
            for t in block.listOfTransactions:
                self.update_NBCs(t)
                if t in back_trans:
                    list_out.append(t)
        test_transactions = list(filter(lambda x: x not in list_out, back_trans))
        self.transactions = []
        for transaction in test_transactions:
            if self.validate_transaction(transaction):
                self.transactions.append(transaction)
                self.update_NBCs(transaction)
        self.add_transactions_to_block()

    def resolve_conflicts(self, app: flask.app.Flask) -> None:
        """Finds chain of greatest length across the network. If this chain, is longer than current
        node's chain, replaces node's chain with it and recalculate NBCs and pending transactions.

        Parameters
        ----------
        app: flask.app.Flask
            The Flask environment in order to be able to create http requests.
        """
        with app.app_context():
            with self.resolve_lock:
                my_length = len(self.chain)
                dominant = None
                chain = None
                for x in self.ring:
                    if x[2] == self.ring[self.id][2]:
                        continue
                    addr = f'http://{x[0]}:{x[1]}/getChain/'
                    try:
                        r = requests.get(addr)
                    except RequestException as e:
                        print(f'Exception {e} occurred while trying to get '
                              f'chain of node {x[0]}:{x[1]}')
                    info = jsonpickle.decode(r.json(), keys=True)['chain']
                    if len(info) > my_length:
                        dominant = x
                        chain = info
                if dominant:
                    with self.lock:
                        # based upon dominant chain recalculate node's NBCs
                        self.recalculate_NBCs(chain)
                        print('I replaced my chain')