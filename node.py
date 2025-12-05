from blockchain import Block, Blockchain

class Node:
    def __init__(self, id):
        self.id = id
        self.table = {i: 100 for i in range(1,6)}
        self.blockchain = Blockchain()

    def moneyTransfer(self, receiver_id, amount):
        pass

    def failProcess(self):
        pass

    def fixProcess(self):
        pass

    def printBlockchain(self):
        self.blockchain.print_blockchain()

    def printBalance(self):
        print(self.table)
