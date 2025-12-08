import hashlib
import uuid

class Block:
    def __init__(self, sender_id, receiver_id, amount, prev_hash, nonce, hash, tag):
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.amount = amount
        self.prev_hash = prev_hash
        self.nonce = nonce
        self.hash = hash
        self.tag = tag

class Blockchain:
    def __init__(self):
        self.chain = []

    def compute_hash_pointer(self, sender_id, receiver_id, amount, nonce, prev_hash):
        data = f"{sender_id}{receiver_id}{amount}{nonce}{prev_hash}"
        encoded_string = data.encode('utf-8') # encode string to bytes
        return hashlib.sha256(encoded_string).hexdigest() # hexidecimal ver of hash
    
    def compute_nonce_hash(self, sender_id, receiver_id, amount, nonce):
        data = f"{sender_id}{receiver_id}{amount}{nonce}"
        encoded_string = data.encode('utf-8') # encode string to bytes
        return hashlib.sha256(encoded_string).hexdigest() # hexidecimal ver of hash
    
    def compute_nonce(self, sender_id, receiver_id, amount):
        while True:
            nonce = str(uuid.uuid4().hex)
            new_hash = self.compute_nonce_hash(sender_id, receiver_id, amount, nonce)
            if new_hash[-1] in "01234":
                return nonce, new_hash

    def add(self, block):
        self.chain.append(block)
        return block

    def print_blockchain(self):
        for i, block in enumerate(self.chain):
            print(f"[{i}] {block.sender_id} -> {block.receiver_id} \namount = {block.amount} \nnonce = {block.nonce} \nhash = {block.hash} \nprev_hash = {block.prev_hash} \nstatus = {block.tag}")
            print("------------------")