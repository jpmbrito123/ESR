class Message:
    def __init__(self, ip_origem,stream_id,instruction):
        self.ip_origem = ip_origem
        self.stream_id = stream_id
        self.instruction = instruction
    
class Stream_package:
    def __init__(self, ip_origem,stream_id,number_package):
        self.ip_origem = ip_origem
        self.stream_id = stream_id
        self.instruction = number_package