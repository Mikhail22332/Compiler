class List:
    def __init__(self, name, memory_offset, size):
        self.name = name
        self.memory_offset = memory_offset
        self.size = size

    def get_memory_offset_at(self, index):
        if 0 <= index <= self.size-1:
            return self.memory_offset + index
