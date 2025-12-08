import argparse
import threading
from paxos import Paxos
from blockchain import Block, Blockchain
from storage import Storage

parser = argparse.ArgumentParser()
parser.add_argument('-port', type=int, required=True)
parser.add_argument('-node', type=int, required=True)
args = parser.parse_args()

MY_PORT = args.port
NODE_ID = args.node
PORTS = [8001, 8002, 8003, 8004, 8005]

# should we catch edge case where node tries to send to invalid receiver_id?

class Node:
    def __init__(self, node_id, port, ports):
        self.node_id = node_id
        self.table = {i: 100 for i in range(1,6)}
        self.blockchain = Blockchain()
        self.storage = Storage(node_id)
        self.paxos = Paxos(node_id, port, ports)
        self.storage.load_state(
            self.blockchain,
            self.table,
            self.paxos.seq_num,
            self.paxos.promised_ballot,
            self.paxos.accepted_ballot,
            self.paxos.accepted_val
        )
        self.failed = False
        threading.Thread(target=self.paxos.listener, daemon=True).start()

    def moneyTransfer(self, sender_id, receiver_id, amount):
        if sender_id != self.node_id:
            print("You can only send from your node.")
            return

        if self.table[sender_id] < amount:
            print("Insufficient funds.")
            return

        depth = len(self.blockchain.chain)
        ballot, promises = self.paxos.prepare(depth)

        if not promises:
            print("Not elected.")
            return
        
        print("Elected.")
        # nonce, new_hash = self.blockchain.compute_nonce(sender_id, receiver_id, amount)
        # # if blockchain is empty, prev_hash is set to 0
        # prev_hash = self.blockchain.chain[-1].hash if self.blockchain.chain else 0

        proposal = {
            "sender_id": sender_id,
            "receiver_id": receiver_id,
            "amount": amount
        }

        find = self.paxos.find_value(proposal, promises)
        if find:
            nonce, new_hash = self.blockchain.compute_nonce(sender_id, receiver_id, amount)
            # if blockchain is empty, prev_hash is set to 0
            prev_hash = self.blockchain.chain[-1].hash if self.blockchain.chain else 0

        accepted = self.paxos.accept(ballot, nonce)

        block = Block(
            sender_id=accepted["sender_id"],
            receiver_id=accepted["receiver_id"],
            amount=accepted["amount"],
            prev_hash=accepted["prev"],
            nonce=accepted["nonce"],
            hash=accepted["hash"],
            tag="COMMITTED"
        )

        self.blockchain.add(block)
        self.table[block.sender_id] -= block.amount
        self.table[block.receiver_id] += block.amount

        self.storage.persist(
            self.blockchain,
            self.table,
            self.paxos.seq_num,
            self.paxos.promised_ballot,
            self.paxos.accepted_ballot,
            self.paxos.accepted_val
        )        
        print("Money transferred.")

    def failProcess(self):
        print("Process failed.")
        self.storage.persist(
            self.blockchain,
            self.table,
            self.paxos.seq_num,
            self.paxos.promised_ballot,
            self.paxos.accepted_ballot,
            self.paxos.accepted_val
        )        
        self.blockchain.chain.clear()
        self.table.clear()
        self.paxos.seq_num.clear()
        self.paxos.promised_ballot.clear()
        self.paxos.accepted_ballot.clear()
        self.paxos.accepted_val.clear()
        self.failed = True

    def fixProcess(self):
        self.storage.load_state(
            self.blockchain,
            self.table,
            self.paxos.seq_num,
            self.paxos.promised_ballot,
            self.paxos.accepted_ballot,
            self.paxos.accepted_val
        )
        self.failed = False
        print("Process fixed.")

    def printBlockchain(self):
        self.blockchain.print_blockchain()

    def printBalance(self):
        print(self.table)

node = Node(NODE_ID, MY_PORT, PORTS)

while True:
    cmd = input().strip()

    if cmd.startswith("moneyTransfer"):
        _, debit_node, credit_node, amount = cmd.split()
        node.moneyTransfer(int(debit_node), int(credit_node), int(amount))
    elif cmd == "failProcess":
        node.failProcess()
    elif cmd == "fixProcess":
        node.fixProcess()
    elif cmd == "printBlockchain":
        node.printBlockchain()
    elif cmd == "printBalance":
        node.printBalance()