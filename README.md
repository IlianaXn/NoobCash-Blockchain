# NoobCash-Blockchain

**NoobCash-Blockchain** is a simplified peer-to-peer system through which its users can conduct transactions with security ensured by the use of cryptographic proof and the distributed consensus algorithm **Proof-of-Work**. Its core is based on the [Bitcoin System](https://bitcoin.org/) and specifically Satoshi Nakamoto's original paper [^ref1].
It was developed by three undergraduate students, [George Kallitsis](https://github.com/giorgoskallitsis99), [Nefeli Myropoulou](https://github.com/nefeli-my) and [Iliana Xygkou](https://github.com/IlianaXn) for the course Distributed Systems 2021-2022 [NTUA ECE](https://www.ece.ntua.gr/gr).

## Technology Stack

During the development of this app these technologies are used:
* [Python](https://www.python.org/) as the programming language
* [Flask](https://palletsprojects.com/p/flask/) as the web application framework

## System Setup

In order to setup the **NoobCash-Blockchain** app one must ensure that they have installed Python 3.9.5.
One must also define the characteristics of the system by setting values for some environment variables in a `.env` file inside the `Noobcash_Blockchain` directory.
Variables:
* MINING_DIFFICULTY: the number of preceeding 0's in blocks' hashes.
* CAPACITY: the capacity of a block (how many transactions inside a block).
* N: number of nodes in the network.
* BOOTSTRAP_IP: the IPv4 address of the bootstrap node.
* BOOTSTRAP_PORT: the port on which bootstrap node listens.

Given those, they can execute the following commands inside the `Noobcash_Blockchain` directory:
1. Create a virtual environment:
```
python3 -m venv ./venv 
```
2. Activate the virtual environment: (this command must be repeated each time before starting the app)
 ```
 source venv/bin/activate
 ```
3. Install the required packages:
```
pip3 install -r requirements.txt
```
4. Start the app:
```
python3 app.py [--test][--port PORT][--id ID]
```
Options:
* test: It's used when one wants to test the system using the files provided in the `transactions` directory.
* port (default 5000): It can be set to any other port after making sure no other app listens on it.
* id (default None): It can be set only to 0 to indicate that this node is the bootstrap node.

## Client

The **NoobCash** client is a Command Line Interface providing the commands below:
* ```balance```: Show the balance of the wallet of the node.
* ```view```: Show the transaction contained in the last block of the blockchain.
* ```t [recipient_id] [amount]```: Send to the node with id equal to ___recipient_id___  ___amount___ coins.
* ```help [command]```: Show the available commands, and if ___command___ is specified, show details about this specific command.
* ```bye```: Exit client (we have to be polite even to computers...)

One can activate the client by executing:
```
python3 client.py
```

## Tests

As it was mentioned before, one can execute some predefined tests by adding the ```--test``` option when starting the app.
Moreover, they can modify the environment variables in the `.env` file to check system's scalability regarding the number of nodes (given test files satisfy the versions of 5 or 10 nodes) and its throughput with respect to the mining difficulty (preceeding 0's in blocks' hashes) and blocks' capacity.

We ran the experiments using 5 and 10 nodes, capacity of values 1, 5, and 10 and mining difficulty of values 4 and 5. 
The diagrams describing the system's behavior are shown below and are explained in the ```report.pdf``` (in greek, we're sorry for that).

![Alt text](/results/throughput.png?raw=true "Throughput")

![Alt text](/results/mean_time.png?raw=true "Mean time for mining")



[^ref1]:  Nakamoto, S. (2008) Bitcoin: A Peer-to-Peer Electronic Cash System. https://bitcoin.org/bitcoin.pdf
