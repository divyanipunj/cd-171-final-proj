import hashlib

class Block:
    def __init__(self, sender_id, reciever_id, prev, amount, nonce, hash):
        self.sender_id = sender_id
        self.reciever_id = reciever_id
        self.amount = amount

        self.nonce = nonce
        self.hash = hash # before we call block, we need to compute the hash

class Blockchain:
    def __init__(self):
        self.blockchain = []

    def compute_hash(self, sender_id, receiver_id, amount, nonce):
        data = f"{sender_id}{receiver_id}{amount}{nonce}"
        encoded_string = data.encode('utf-8') # encode string to bytes
        return hashlib.sha256(encoded_string).hexdigest() # hexidecimal representation of hash
    
    def compute_nonce(self, sender_id, receiver_id, amount):
        # initialize nonce
        while self.compute_hash(sender_id, receiver_id, amount)[-1] not in "01234":
            # update nonce and retry
        return nonce, hash

    def add():
        pass

    def get_prev_hash():
        pass

    def print_blockchain():
        pass