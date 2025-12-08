import json
import os
from blockchain import Block

class Storage:
    def __init__(self, node_id):
        self.node_id = node_id
        self.file = f"node_{node_id}_state.json"

    def load_state(self, blockchain, table, seq_num, promised_ballot, accepted_ballot, accepted_val):
        if not os.path.exists(self.file):
            return

        try:
            with open(self.file, "r") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error loading state: {e}")
            return
        
        for key, value in data.get("table", {}).items():
            table[int(key)] = value

        for b in data.get("blockchain", []):
            block = Block(
                sender_id=b["sender_id"],
                receiver_id=b["receiver_id"],
                amount=b["amount"],
                prev_hash=b["prev_hash"],
                nonce=b["nonce"],
                hash=b["hash"],
                tag=b["tag"]
            )
            blockchain.chain.append(block)

        for key, value in data.get("seq_num", {}).items():
            seq_num[int(key)] = value
        
        for key, value in data.get("promised_ballot", {}).items():
            promised_ballot[int(key)] = tuple(value) if value else value
        
        for key, value in data.get("accepted_ballot", {}).items():
            accepted_ballot[int(key)] = tuple(value) if value else value
        
        for key, value in data.get("accepted_val", {}).items():
            accepted_val[int(key)] = value

    def persist(self, blockchain, table, seq_num, promised_ballot, accepted_ballot, accepted_val):
        data = {
            "table": {str(k): v for k, v in table.items()},
            "blockchain": [],
            "seq_num": {str(k): v for k, v in seq_num.items()},
            "promised_ballot": {str(k): list(v) if v else v for k, v in promised_ballot.items()},
            "accepted_ballot": {str(k): list(v) if v else v for k, v in accepted_ballot.items()},
            "accepted_val": {str(k): v for k, v in accepted_val.items()}
        }

        for block in blockchain.chain:
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