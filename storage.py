import json
import os
from blockchain import Block

class Storage:
    def __init__(self, id):
        self.file = f"node_{id}_state.json"

    def load_state(self, bc, balance):
        if not os.path.exists(self.file):
            return
        
        with open(self.file) as f:
            data = json.load(f)

        for key, value in data["balances"].items():
            balance[int(key)] = value

        for b in data["blockchain"]:
            block = Block(
                sender_id=b["sender_id"],
                receiver_id=b["receiver_id"],
                amount=b["amount"],
                prev_hash=b["prev_hash"],
                nonce=b["nonce"],
                hash=b["hash"],
                tag=b["tag"]
            )
            bc.blockchain.append(block)

    def persist(self, bc, balances):
        data = {
            "balances": balances,
            "blockchain": []
        }

        for block in bc.blockchain:
            data["blockchain"].append({
                "sender_id": block.sender_id,
                "receiver_id": block.receiver_id,
                "amount": block.amount,
                "prev_hash": block.prev_hash,
                "nonce": block.nonce,
                "hash": block.hash,
                "tag": block.tag
            })

        with open(self.file, "w") as f:
            json.dump(data, f, indent=2)