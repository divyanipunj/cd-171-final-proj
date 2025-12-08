import socket
import json
import threading
import time
from storage import Storage

DEST_HOST = "localhost"

class Paxos:
    def __init__(self, node_id, my_port, ports):
        self.node_id = node_id
        self.my_port = my_port
        self.other_ports = [port for port in ports if port != my_port]

        self.promised_ballot = {}
        self.accepted_ballot = {}
        self.accepted_val = {}
        self.seq_num = {}
        self.storage = Storage(self.node_id)

    def send_message(self, port, message):
        try:
            print(f"[{self.my_port}] Sending {message['type']} to port {port} with ballot {message.get('ballot')}")
            time.sleep(3) # 3 second delay
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                s.connect((DEST_HOST, port))
                s.sendall(json.dumps(message).encode())
                data = s.recv(4096)
                if data:
                    return json.loads(data.decode())
                else:
                    return None
        except Exception as e:
            return None

    def listener(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((DEST_HOST, self.my_port))
            s.listen()
            print(f"[{self.node_id} listening on port {self.my_port}")

            while True:
                conn, _ = s.accept()
                threading.Thread(target=self.handle_all_connections, args=(conn,), daemon=True).start()

    def handle_all_connections(self, conn):
        with conn:
            data = conn.recv(4096)
            if not data:
                return
            
            message = json.loads(data.decode())
            response = None

            if message["type"] == "PREPARE":
                response = self.handle_prepare(message)
            elif message["type"] == "ACCEPT":
                response = self.handle_accept(message)
            elif message["type"] == "DECISION":
                response = self.handle_decision(message)
            if response:
                conn.sendall(json.dumps(response).encode())

    def prepare(self, depth):
        if depth not in self.seq_num:
            self.seq_num[depth] = 0
        else:
            self.seq_num[depth] += 1

        ballot = (self.seq_num[depth], self.node_id, depth)
        prepare = {"type": "PREPARE", "ballot": ballot}

        promises = []
        for port in self.other_ports:
            response = self.send_message(port, prepare)
            if response:
                promises.append(response)

        if len(promises) < 2:
            print(f"[{self.my_port}] Not enough promises.")
            return None, None
        
        return ballot, promises

        # now leader has been elected, can calculate nonce
    
    def find_value(self, proposal, promises):
        chosen_val = proposal.copy() # ? 
        highest_ballot_accepted = None
        accept_ballot_count = 0
        for response in promises:
            if response["type"] == "PROMISE" and response["accepted_num"] is not None: # CASE WHERE PREV VALUE ACCEPTED
                accept_ballot_count += 1
                old_accepted = tuple(response["accepted_num"])

                if highest_ballot_accepted is None or old_accepted > highest_ballot_accepted:
                    highest_ballot_accepted = old_accepted
                    chosen_val = response["accepted_val"]
            elif response["type"] == "PROMISE":
                accept_ballot_count += 1
        
        if accept_ballot_count >= 2: # count self in majority so need 2 others to accept
            if chosen_val is None:
                # now process is "leader" and will try to find a nonce
                # chloe: find a nonce
                return True
        return False

        # once the a nonce is found, send accept messages
    
    def accept(self, ballot, value):
        message = {"type": "ACCEPT", "ballot": ballot, "val": value}
            
        # once a leader has found an a nonce, send an accept message to all other processes
        responses_for_accept = []
        for port in self.other_ports:
            response = self.send_message(port, message)
            if response: 
                responses_for_accept.append(response)
        
        accepted = 0
        for response in responses_for_accept:
            if response["type"] == "ACCEPTED":
                accepted += 1
        if accepted >= 2: # count self in majority so need 2 others to accept
            # majority accepted, so a decision is made. send out the value
            decision = {"type": "DECISION", "ballot": ballot, "val": value}

            for port in self.other_ports:
                self.send_message(port, decision)

            return 0
        else:
            return -1

    def handle_prepare(self, msg):
        ballot = tuple(msg["ballot"])
        depth = ballot[2]

        if depth not in self.promised_ballot:
            self.promised_ballot[depth] = (-1, -1, -1)

        if ballot > tuple(self.promised_ballot[depth]):
            self.promised_ballot[depth] = msg["ballot"]
            print(f"[{self.my_port}] Promising ballot {ballot} at depth {depth}")
            return {
                "type": "PROMISE",
                "accepted_num": self.accepted_ballot.get(depth),
                "accepted_val": self.accepted_val.get(depth)
            }

        print(f"[{self.my_port}] Rejecting ballot {ballot} at depth {depth}")
        return {
            "type": "REJECT",
            "accepted_num": self.accepted_ballot.get(depth),
            "accepted_val": self.accepted_val.get(depth)
        }

    def handle_accept(self, msg):
        ballot = tuple(msg["ballot"])
        depth = ballot[2]

        if depth not in self.promised_ballot:
            self.promised_ballot[depth] = (-1, -1, -1)

        if ballot >= tuple(self.promised_ballot[depth]):
            self.accepted_ballot[depth] = ballot
            self.accepted_val[depth] = msg["val"]
            print(f"[{self.my_port}] Accepted value {msg['val']} with ballot {ballot}")
            return {"type": "ACCEPTED"}

        print(f"[{self.my_port}] Rejecting accept for ballot {ballot}")
        return {"type": "REJECT"}

    def handle_decision(self, msg):
        depth = tuple(msg["ballot"])[2]
        self.accepted_val[depth] = msg["val"]
        print(f"[{self.my_port}] Decision received for depth {depth}: {msg['val']}")
        return {"type": "ACK"}