class Link:
    def __init__(self, memory_offset, is_array):
        self.memory_offset = memory_offset
        self.initialized = False
        self.isArray = is_array