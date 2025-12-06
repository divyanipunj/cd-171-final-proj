import socket
import threading
import json
import time

class Network:
    def __init__(self, id, config_path, message_handler):
        self.id = id
        self.nodes = self.load_config(config_path)
        self.message_handler = message_handler

        threading.Thread(target=self.server_loop, daemon=True).start()

    def load_config(self, path):
        nodes = {}
        with open(path) as f:
            for line in f:
                id, ip, port = line.strip().split()
                nodes[int(id)] = (ip, int(port))
        return nodes

    def server_loop(self):
        ip, port = self.nodes[self.id]
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((ip, port))
        sock.listen()

        print(f"Node {self.id} listening on {ip}:{port}")

        while True:
            conn, _ = sock.accept()
            data = conn.recv(4096).decode()
            msg_dict = json.loads(data)
            msg = self.deserialize_message(msg_dict)
            self.message_handler(msg)

    def send_message(self, dest_id, message):
        ip, port = self.nodes[dest_id]
        msg_dict = message.__dict__
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, port))
        s.send(json.dumps(msg_dict).encode())
        s.close()
        time.sleep(3)

    def deserialize_message(self, d):
        msg_type = d.get("type", None)
        # TODO: map msg_type to appropriate class
        # for now return raw dict
        return d