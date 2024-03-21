from assembly_generator import AssemblyCodeGenerator


class Program(dict):
    def __init__(self):
        super().__init__()
        self.memory_offset = 0
        self.code = []
        self.current_line = 1

    def add_procedure(self, procedure):
        self.setdefault(procedure.name, procedure)
        self.memory_offset = procedure.last_indeks

    def generate_code_to_file(self):
        assembly_generator = AssemblyCodeGenerator()
        for name in self:
            self[name].first_line = self.current_line
            assembly_generator.gen_code_from_commands_entry(name, self)
            self.code.append(assembly_generator.code)
            if name == "PROGRAM":
                self.code[0][0] = self.code[0][0].replace('main', str(self.current_line))
            self.current_line += len(assembly_generator.code)
