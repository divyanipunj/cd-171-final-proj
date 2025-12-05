import socket
import time
import threading
import json
import argparse

class Client:
    def __init__(self, cid, port):
        self.cid = cid
        self.port = port
        self.host = "localhost"
        self.lamport = 0
        self.queue = []
        self.replies = 0
        self.successes = 0
        self.dictionary = {}
        self.clients = {1: 8001, 2: 8002, 3: 8003}
        self.lock = threading.Lock()

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(3)
        
        threading.Thread(target=self.accept_connections, daemon=True).start()

    def accept_connections(self):
        while True:
            connection, address = self.server_socket.accept()
            threading.Thread(target=self.handle_requests, args=(connection,), daemon=True).start()

    def handle_requests(self, connection):
        data = connection.recv(4096)
        if not data:
            connection.close()
            return

        message = json.loads(data.decode())
        threading.Thread(target=self.handle_message, args=(message,), daemon=True).start()
        connection.close()

    def handle_message(self, message):
        time.sleep(3)
        type = message["type"]
        sender = message["sender"]

        with self.lock:
            if type == "REQUEST":
                self.lamport = max(self.lamport, message["timestamp"]) + 1
                self.queue.append((message["timestamp"], sender))
                self.queue.sort()
                self.send(sender, {"type": "REPLY", "sender": self.cid})
            elif type == "REPLY":
                self.replies += 1
            elif type == "INSERT":
                key = message["perm"]
                value = message["grade"]
                self.dictionary[key] = value
                self.send(sender, {"type": "SUCCESS", "sender": self.cid})
            elif type == "SUCCESS":
                self.successes += 1
            elif type == "RELEASE":
                self.queue = [request for request in self.queue if request[1] != sender]

    def send(self, did, message):
        port = self.clients[did]
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("localhost", port))
        s.sendall(json.dumps(message).encode())
        s.close()

    def handle_commands(self, connection):
        data = connection.recv(1024)
        if not data:
            connection.close()
            return
        
        message = data.decode().strip().split()
        command = message[0]

        if command == "lookup":
            perm = message[1]
            with self.lock:
                grade = self.dictionary.get(perm)
            if grade:
                connection.sendall(f"LOOKUP <{perm}, {grade}>\n".encode())
            else:
                connection.sendall(f"LOOKUP <{perm}, NOT FOUND>\n".encode())
        elif command == "insert":
            perm = message[1]
            grade = message[2]
            self.insert(perm, grade)
            connection.sendall(f"SUCCESS <insert {perm} {grade} {self.cid}>\n".encode())
        elif command == "dictionary":
            with self.lock:
                connection.sendall(f"{self.dictionary}\n".encode())

        connection.close()

    def insert(self, perm, grade):
        with self.lock:
            self.lamport += 1
            self.replies = 0
            self.successes = 0
            self.queue.append((self.lamport, self.cid))
            self.queue.sort()

        for id in self.clients:
            if id != self.cid:
                self.send(id, {"type": "REQUEST", "timestamp": self.lamport, "sender": self.cid})

        while True:
            with self.lock:
                if self.replies >= len(self.clients) - 1:
                    break
            time.sleep(0.05)

        for id in self.clients:
            if id != self.cid:
                self.send(id, {"type": "INSERT", "perm": perm, "grade": grade, "sender": self.cid})

        with self.lock:
            self.dictionary[perm] = grade

        while True:
            with self.lock:
                if self.successes >= len(self.clients) - 1:
                    break
            time.sleep(0.05)

        for id in self.clients:
            if id != self.cid:
                self.send(id, {"type": "RELEASE", "sender": self.cid})

    def start(self):
        master_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        master_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        master_socket.bind(("localhost", self.port + 100))
        master_socket.listen(3)

        while True:
            connection, address = master_socket.accept()
            threading.Thread(target=self.handle_commands, args=(connection,), daemon=True).start()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-port", type=int, required=True)
    parser.add_argument("-client", type=int, required=True)
    args = parser.parse_args()

    client = Client(args.client, args.port)
    client.start()