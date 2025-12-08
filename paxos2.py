import socket
import json
import threading
import argparse
from storage import Storage
from blockchain import Block, Blockchain

parser = argparse.ArgumentParser()
parser.add_argument('-port', type=int, required=True)
parser.add_argument('-node', type=int, required=True)
args = parser.parse_args()

DEST_HOST = "localhost"
MY_PORT = args.port
NODE_ID = args.node # associated node with port
PORTS = [8001, 8002, 8003, 8004, 8005] 
MY_PORTS = [port for port in PORTS if port != MY_PORT] # exclude own port when running

# process paxos vars
promised_ballot = {} # highest ballot promised at each depth
accepted_ballot = {} # ballot accepted at each depth
accepted_val = {} # value accepted at each depth
seq_num = {} # seq_num[depth] = number of attempted proposals at depth

#  the node vars shoved in with process stuff
blockchain = Blockchain()
table = {i: 100 for i in range(1,6)}
storage = Storage(NODE_ID)
storage.load_state(
    blockchain,
    table,
    seq_num,
    promised_ballot,
    accepted_ballot,
    accepted_val
)
failed = False
# node = Node(NODE_ID, MY_PORT, PORTS)

# DESIGN CHOICES (that you can change, chloe):
# types of messages = prepare, promise, accept, accepted, decision, reject
# ballot = (sequence_number[depth], node_id, depth)
# each message is slightly diferent based on message type

# send message to a process
def send_message(port, message):
    try: 
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5) # need to set time out ??
            s.connect((DEST_HOST, port))
            s.sendall(json.dumps(message).encode())
            data = s.recv(4096)
            return json.loads(data.decode()) if data else None # change up?
    except ConnectionRefusedError: # i don't what kind of error will happn, adjust accordingly
        return None

# in the background, need to listen for messages from all proccesses. re-use client server code.
def handle_all_connections(conn):
    with conn: 
        data = conn.recv(4096)
        if not data:
            return
        
        text = data.decode()
        response = None
        try:
            message = json.loads(text)
            if message["type"] == "PREPARE":
                response = handle_proposal(message)
            elif message["type"] == "ACCEPT":
                response = handle_accept(message)
            elif message["type"] == "DECISION":
                response = handle_decision(message)
            if response: 
                conn.sendall(json.dumps(response).encode())
        except json.JSONDecodeError:
            #if error decoding, just return
            return

def listener(): 
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((DEST_HOST, MY_PORT))
        s.listen()
        print(f"Client {NODE_ID} listening on port {MY_PORT}")
        
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_all_connections, args=(conn,), daemon=True).start()

# a process attempts to run paxos. 
def paxos(sender_id, receiver_id, amount):
    depth = len(blockchain.chain)

    if depth not in seq_num:
        seq_num[depth] = 0
    else:
        seq_num[depth] += 1

    ballot = (seq_num[depth], NODE_ID, depth)
    message = {"type": "PREPARE", "ballot": ballot}

    responses_for_prepare = []
    response = None
    for port in MY_PORTS: 
        response = send_message(port, message)
        
        if response:
            responses_for_prepare.append(response)

    # check if any previous values were accepted:
    nonce = None
    highest_ballot_accepted = None
    accept_ballot_count = 0
    for response in responses_for_prepare:
        if response["type"] == "PROMISE" and response["accepted_num"] is not None: # CASE WHERE PREV VALUE ACCEPTED
            accept_ballot_count += 1
            old_accepted = tuple(response["accepted_num"])

            if highest_ballot_accepted is None or old_accepted > highest_ballot_accepted:
                highest_ballot_accepted = old_accepted
                nonce = response["accepted_val"]
        elif response["type"] == "PROMISE":
            accept_ballot_count += 1
    
    if accept_ballot_count >= 2: # count self in majority so need 2 others to accept
        if nonce is None:
            # now process is "leader" and will try to find a nonce
            # chloe: find a nonce
            nonce, new_hash = blockchain.compute_nonce(sender_id, receiver_id, amount)
            # if blockchain is empty, prev_hash is set to 0
            prev_hash = blockchain.chain[-1].hash if blockchain.chain else 0

            # once the anonce is found, send accept messages
        message = {"type": "ACCEPT", "ballot": ballot, "nonce": nonce, "sender_id": sender_id, "receiver_id": receiver_id, "amount": amount, "prev_hash": prev_hash, "hash": new_hash}
            
        # once a leader has found an anonce, send an accept message to all other processes
        responses_for_accept = []
        for port in MY_PORTS:
            response = send_message(port, message)

            if response: 
                responses_for_accept.append(response)
        
        accepted = 0
        for response in responses_for_accept:
            if response["type"] == "ACCEPTED":
                accepted += 1
        if accepted >= 2: # count self in majority so need 2 others to accept
            # majority accepted, so a decision is made. send out the value
            msg = {"type": "DECISION", "ballot": message["ballot"], "nonce": nonce}

            for port in MY_PORTS:
                send_message(port, msg)

            blockchain.chain.append(nonce) # update blockchain accordingly (chloe got this covered)

            return {"sender_id": sender_id, "receiver_id": receiver_id, "amount": amount, "prev_hash": prev_hash, "nonce": nonce, "hash": new_hash}
        else:
            return None
    else:
        return None

# handle or decline a proposal (leader election)
def handle_proposal(message):
    ballot = tuple(message["ballot"])
    msg_seq_num, node_id, depth = ballot

    if depth not in promised_ballot:
        promised_ballot[depth] = (-1, -1, -1) # ballor has not been seen before, initialize.

    # promised_ballot vs incoming ballot ?
    if promised_ballot[depth][0] < msg_seq_num or ((promised_ballot[depth][0] == msg_seq_num and promised_ballot[depth][1] < node_id)):
        # then accept prepare
        promised_ballot[depth] = message["ballot"]
        response = {"type": "PROMISE", "ballot": message["ballot"],"node_id": NODE_ID, "accepted_num": accepted_ballot.get(depth), "accepted_val": accepted_val.get(depth)}
        return response
    else:
        response = {"type": "REJECT", "ballot": promised_ballot[depth], "node_id": NODE_ID} # return the ballot that i have accepted
        return response

# once leader finds an anonce, go ahead and accept it
def handle_accept(message):
    ballot = tuple(message["ballot"])
    depth = ballot[2]
    nonce = message["nonce"]

    if depth not in promised_ballot:
        promised_ballot[depth] = (-1, -1, -1) # ballot for depth has not been seen before, initialize.
    
    if promised_ballot[depth][0] < ballot[0] or (promised_ballot[depth][0] == ballot[0] and promised_ballot[depth][1] <= ballot[1]):
        accepted_ballot[depth] = ballot
        accepted_val[depth] = message["nonce"]
        if len(blockchain.chain) == depth:
            block = Block(
                sender_id=message["sender_id"],
                receiver_id=message["receiver_id"],
                amount=message["amount"],
                prev_hash=message["prev_hash"],
                nonce=message["nonce"],
                hash=message["hash"],
                tag="TENTATIVE"
            )
            blockchain.add(block)
        return {"type": "ACCEPTED", "ballot": ballot, "node_id": NODE_ID}
    else:
        return {"type": "REJECT", "node_id": NODE_ID, "ballot": promised_ballot[depth]} # return the ballot that i have accepted

# once a leader had made a decision, go ahead and implement it
def handle_decision(message):
    ballot = tuple(message["ballot"])
    depth = ballot[2]
    nonce = message["nonce"]

    # update blockchain accordingly
    if len(blockchain.chain) == depth:
        blockchain.chain.append(nonce)

    # not really necessary to respond for paxos..
    message = {"type": "ACK", "node_id": NODE_ID}
    return message
     
threading.Thread(target=listener, daemon=True).start()

# need this to stay alive 
# this is for testing only
def moneyTransfer(sender_id, receiver_id, amount):
    if sender_id != NODE_ID:
        print("You can only send from your node.")
        return

    if table[sender_id] < amount:
        print("Insufficient funds.")
        return

    decided = paxos(sender_id, receiver_id, amount)

    if not decided:
        print("Consensus failed,")
        return

    # block = Block(
    #     sender_id=decided["sender_id"],
    #     receiver_id=decided["receiver_id"],
    #     amount=decided["amount"],
    #     prev_hash=decided["prev_hash"],
    #     nonce=decided["nonce"],
    #     hash=decided["hash"],
    #     tag="COMMITTED"
    # )

    # blockchain.add(block)
    table[block.sender_id] -= block.amount
    table[block.receiver_id] += block.amount

    storage.persist(
        blockchain,
        table,
        seq_num,
        promised_ballot,
        accepted_ballot,
        accepted_val
    )        
    print("Money transferred.")

def failProcess():
    print("Process failed.")
    storage.persist(
        blockchain,
        table,
        seq_num,
        promised_ballot,
        accepted_ballot,
        accepted_val
    )        
    blockchain.chain.clear()
    table.clear()
    seq_num.clear()
    promised_ballot.clear()
    accepted_ballot.clear()
    accepted_val.clear()
    failed = True

def fixProcess():
    storage.load_state(
        blockchain,
        table,
        seq_num,
        promised_ballot,
        accepted_ballot,
        accepted_val
    )
    failed = False
    print("Process fixed.")

def printBlockchain():
    blockchain.print_blockchain()

def printBalance():
    print(table)

while True:
    cmd = input().strip()

    if cmd.startswith("moneyTransfer"):
        _, debit_node, credit_node, amount = cmd.split()
        moneyTransfer(int(debit_node), int(credit_node), int(amount))
    elif cmd == "failProcess":
        failProcess()
    elif cmd == "fixProcess":
        fixProcess()
    elif cmd == "printBlockchain":
        printBlockchain()
    elif cmd == "printBalance":
        printBalance()