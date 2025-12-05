import hashlib

class Block:
    def __init__(self, sender_id, reciever_id, prev, amount, nonce, hash):
        self.sender_id = sender_id
        self.reciever_id = reciever_id
        self.amount = amount

        self.nonce = nonce
        self.hash = hash #before we call block, we need to compute the hash
        

class Node:
    def __init__(self, id):
        self.id = id
        self.table = {i: 100 for i in range(1,6)}
        self.blockchain = []

