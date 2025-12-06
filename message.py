# messages.py

class Message:
    def __init__(self, src, dest):
        self.src = src
        self.dest = dest

class PrepareMsg(Message):
    def __init__(self, src, dest, ballot, depth):
        super().__init__(src, dest)
        self.ballot = ballot
        self.depth = depth

class PromiseMsg(Message):
    def __init__(self, src, dest, ballot, accepted_n, accepted_val):
        super().__init__(src, dest)
        self.ballot = ballot
        self.accepted_n = accepted_n
        self.accepted_val = accepted_val

class AcceptMsg(Message):
    def __init__(self, src, dest, ballot, depth, proposal):
        super().__init__(src, dest)
        self.ballot = ballot
        self.depth = depth
        self.proposal = proposal

class AcceptedMsg(Message):
    def __init__(self, src, dest, ballot, depth):
        super().__init__(src, dest)
        self.ballot = ballot
        self.depth = depth

class DecideMsg(Message):
    def __init__(self, src, dest, proposal):
        super().__init__(src, dest)
        self.proposal = proposal
