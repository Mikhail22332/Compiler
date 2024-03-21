class Variable:
    def __init__(self, memory_offset):
        self.memory_offset = memory_offset
        self.initialized = False
        self.pre_set = False