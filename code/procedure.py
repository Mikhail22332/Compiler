from list import List
from link import Link
from variable import Variable


class Procedure:
    def __init__(self, memory_offset):
        super().__init__()
        self.name = ''
        self.memory_offset = memory_offset
        self.last_indeks = memory_offset + 1
        self.commands = []
        self.symbols = {}
        self.links = {}
        self.consts = {}
        self.parameters = []
        self.first_line = 0

    def set_commands(self, commands):
        self.commands = commands

    def add_variable(self, name):
        self.symbols.setdefault(name, Variable(self.last_indeks))
        self.last_indeks += 1

    def add_array(self, name, size):
        self.symbols.setdefault(name, List(name, self.last_indeks, size))
        self.last_indeks += size

    def add_const(self, value):
        self.consts.setdefault(value, self.last_indeks)
        self.last_indeks += 1
        return self.last_indeks - 1

    def add_variable_link(self, name):
        self.links.setdefault(name, Link(self.last_indeks, False))
        self.last_indeks += 1

    def add_array_link(self, name):
        self.links.setdefault(name, Link(self.last_indeks, True))
        self.last_indeks += 1
