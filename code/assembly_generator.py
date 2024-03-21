from variable import Variable
from list import List
r_h = 'h'
list_of_procedures = {}
depth = 0


class AssemblyCodeGenerator:
    def __init__(self):
        self.code = []
        self.symbols = {}
        self.links = {}
        self.commands = {}
        self.consts = {}
        self.first_line = 0
        self.procedure_table = {}
        self.procedure = {}
        self.name = ""

    def gen_code_from_commands_entry(self, name, procedure_table):
        self.init_fields(name, procedure_table)
        self.gen_code_from_commands(self.commands)
        if name == 'PROGRAM':
            self.code.append("HALT")
        else:
            self.load_address_for_jump_back(self.procedure.memory_offset)

    def load_address_for_jump_back(self, memory_offset):
        r_e = 'e'
        self.gen_const(memory_offset, r_e)
        self.code.append(f"LOAD {r_e}")
        self.code.append(f"JUMPR a")

    def gen_code_from_commands(self, commands):
        global depth
        for command in commands:
            if command[0] == "write":
                value = command[1]
                register = 'b'
                register1 = 'c'
                if value[0] == "load":
                    if type(value[1]) == tuple:
                        if value[1][1] in self.links:
                            if value[1][0] == "undeclared":
                                var = value[1][1]
                                self.load_variable_link_address(var, register)
                            elif value[1][0] == "array":
                                self.load_array_link_address(value[1][1], value[1][2], register, register1)

                        else:
                            if value[1][0] == "undeclared":
                                var = value[1][1]
                                self.load_variable_address(var, register)
                            elif value[1][0] == "array":
                                self.load_array_address_at(value[1][1], value[1][2], register, register1)
                    else:
                        if value[1] in self.links:
                            self.load_variable_link_address(value[1], register)
                        elif value[1] in self.symbols:
                            if self.symbols[value[1]].initialized:
                                self.load_variable_address(value[1], register)
                            else:

                                raise Exception(f"Use of uninitialized variable {value[1]}")


                elif value[0] == "const":
                    address = self.consts[value[1]]
                    self.gen_const(address, register)
                    self.gen_const(value[1], register1)

                    self.code.append(f"GET {register1}")
                    self.code.append(f"STORE {register}")

                self.code.append(f"LOAD {register}")
                self.code.append(f"WRITE")

            elif command[0] == "read":
                target = command[1]
                register = 'a'
                register1 = 'b'
                if type(target) == tuple:
                    if target[0] == "undeclared":
                        raise Exception(f"Reading to undeclared variable {target[1]}")
                    elif target[0] == "array":
                        if target[1] in self.links:
                            self.load_array_link_address(target[1], target[2], register1, register)
                        else:
                            self.load_array_address_at(target[1], target[2], register1, register)
                else:
                    if target in self.links:
                        self.load_variable_link_address(target, register1)
                        self.links[target].initialized = True
                    else:
                        if type(self.symbols[target]) == Variable:
                            self.load_variable_address(target, register1)
                            self.symbols[target].initialized = True

                self.code.append(f"READ")

                self.code.append(f"STORE {register1}")

            elif command[0] == "assign":
                target = command[1]
                expression = command[2]

                second_reg = 'b'
                third_reg = 'c'
                self.calculate_expression(expression, second_reg)

                if type(target) == tuple:
                    if target[0] == "undeclared":
                        raise Exception(f"Assigning to undeclared variable {target[1]}")
                    elif target[0] == "array":
                        if target[1] in self.links:
                            self.load_array_link_address(target[1], target[2], third_reg, second_reg)
                            self.code.append(f"GET {r_h}")
                        else:
                            self.load_array_address_at(target[1], target[2], third_reg, second_reg)
                            self.code.append(f"GET {r_h}")
                else:
                    if target in self.links:
                        self.load_variable_link_address(target, third_reg)
                        self.code.append(f"GET {r_h}")
                        self.links[target].initialized = True

                    elif type(self.symbols[target]) == Variable:
                        self.load_variable_address(target, third_reg)
                        self.code.append(f"GET {r_h}")
                        self.symbols[target].initialized = True
                    else:
                        raise Exception(f"Assigning to array {target} with no index provided")

                self.code.append(f"STORE {third_reg}")

            elif command[0] == "if":
                condition = self.simplify_condition(command[1])
                if isinstance(condition, bool):
                    if condition:
                        self.gen_code_from_commands(command[2])
                else:
                    self.prepare_consts_before_block(command[-1])
                    self.check_condition(condition)
                    if_start = len(self.code)
                    self.gen_code_from_commands(command[2])
                    if_end = len(self.code)
                    self.code[if_start-1] = self.code[if_start-1].replace('finish', str(if_end+self.first_line))

            elif command[0] == "ifelse":
                condition = self.simplify_condition(command[1])
                if isinstance(condition, bool):
                    if condition:
                        self.gen_code_from_commands(command[2])
                    else:
                        self.gen_code_from_commands(command[3])
                else:
                    self.prepare_consts_before_block(command[-1])
                    self.check_condition(command[1])
                    if_start = len(self.code)
                    self.gen_code_from_commands(command[2])
                    self.code.append(f"JUMP finish")
                    else_start = len(self.code)
                    self.gen_code_from_commands(command[3])
                    else_end = len(self.code)
                    self.code[if_start - 1] = self.code[if_start - 1].replace('finish', str(else_start+self.first_line))
                    self.code[else_start-1] = self.code[else_start-1].replace('finish', str(else_end+self.first_line))

            elif command[0] == "while":
                condition = self.simplify_condition(command[1])
                if isinstance(condition, bool):
                    if condition:
                        self.prepare_consts_before_block(command[-1])
                        loop_start = len(self.code)
                        self.gen_code_from_commands(command[2])
                        self.code.append(f"JUMP {loop_start - len(self.code) +self.first_line}")
                else:
                    self.prepare_consts_before_block(command[-1])
                    condition_start = len(self.code)
                    self.check_condition(command[1])
                    loop_start = len(self.code)
                    depth += 1
                    self.gen_code_from_commands(command[2])

                    self.code.append(f"JUMP {condition_start+self.first_line}")
                    loop_end = len(self.code)
                    self.code[loop_start-1] = self.code[loop_start-1].replace('finish', str(loop_end+self.first_line))

            elif command[0] == "until":
                loop_start = len(self.code)
                self.gen_code_from_commands(command[2])
                self.check_condition(command[1])
                condition_end = len(self.code)
                depth -= 1
                self.code[condition_end-1] = self.code[condition_end-1].replace('finish', str(loop_start+self.first_line))
            elif command[0] == "proc_call":
                r_a = 'a'
                r_b = 'b'
                r_c = 'c'
                r_d = 'd'
                procedure_name = command[1][0]

                if procedure_name in list_of_procedures:
                    if procedure_name == self.name:
                        raise Exception(f"Recursion call for procedure {procedure_name}")
                    procedure_to_jump = list_of_procedures[procedure_name]
                    passed_parameters = command[1][1]
                    if len(procedure_to_jump.links) == len(passed_parameters):
                        keys = list(procedure_to_jump.links.keys())

                        current_offset = procedure_to_jump.memory_offset + 1
                        for i in range(len(passed_parameters)):
                            self.gen_const(current_offset, r_b)
                            self.code.append(f"GET {r_b}")

                            if(passed_parameters[i][1] in self.symbols):

                                if type(self.symbols[passed_parameters[i][1]]) == List:
                                    if procedure_to_jump.links[keys[i]].isArray:

                                        address = self.symbols[passed_parameters[i][1]].memory_offset
                                        self.gen_const(address, r_a)

                                        self.code.append(f"STORE {r_b}")
                                    else:
                                        raise Exception(f"Array {passed_parameters[i][1]} was passed instead of variable!")
                                else:
                                    if not procedure_to_jump.links[keys[i]].isArray:
                                        if not self.symbols[passed_parameters[i][1]].initialized:
                                            if procedure_to_jump.links[keys[i]].initialized:
                                                self.symbols[passed_parameters[i][1]].initialized = True
                                        self.load_variable_address(passed_parameters[i][1], r_a)
                                        procedure_to_jump.links[keys[i]].initialized = True
                                        self.code.append(f"STORE {r_b}")
                                    else:
                                        raise Exception(f"Variable {passed_parameters[i][1]} was passed instead of array!")
                            else:
                                self.load_variable_link_address(passed_parameters[i][1], r_a)
                                procedure_to_jump.links[keys[i]].initialized = True
                                self.code.append(f"STORE {r_b}")
                            current_offset += 1

                        address = self.procedure_table[procedure_name].memory_offset
                        jump_to = self.procedure_table[procedure_name].first_line
                        self.gen_const(address, r_c)
                        self.gen_const(4, r_d)
                        self.code.append(f"STRK a")
                        self.code.append(f"ADD {r_d}")
                        self.code.append(f"STORE {r_c}")
                        self.code.append(f"JUMP {jump_to}")
                    else:
                        raise Exception(f"Number of arguments passed differs {procedure_name}")
                else:
                    raise Exception(f"Use of undefined procedure {procedure_name}")


    def calculate_expression(self, expression, target_reg='a', second_reg='b', third_reg='c', fourth_reg='d',
                             fifth_reg='e', sixth_reg='f'):
        if expression[0] == "const":
            self.gen_const(expression[1], target_reg)
            self.code.append(f"GET {target_reg}")
            self.code.append(f"PUT {r_h}")

        elif expression[0] == "load":
            if type(expression[1]) == tuple:
                if expression[1][0] == "undeclared":
                    self.load_variable(expression[1][1], target_reg)
                    if target_reg != 'a':
                        self.code.append(f"PUT {target_reg}")

                elif expression[1][0] == "array":
                    if expression[1][1] in self.links:
                        self.load_array_link(expression[1][1], expression[1][2], target_reg, second_reg)
                        self.code.append(f"PUT {r_h}")
                    else:

                        self.load_array_at(expression[1][1], expression[1][2], target_reg, second_reg)
                        self.code.append(f"PUT {r_h}")
            else:
                if expression[1] in self.links:
                    self.load_variable_link_address(expression[1], target_reg)
                    self.code.append(f"LOAD {target_reg}")
                    self.code.append(f"PUT {r_h}")
                    if target_reg != 'a':
                        self.code.append(f"PUT {target_reg}")

                elif self.symbols[expression[1]].initialized or not self.symbols[expression[1]].initialized and depth > 0:

                    self.load_variable(expression[1], target_reg)
                    self.code.append(f"GET {target_reg}")
                    self.code.append(f"PUT {r_h}")
                else:
                    raise Exception(f"Use of uninitialized variable {expression[1]}")


        else:
            if expression[1][0] == 'const':
                const, var = 1, 2
            elif expression[2][0] == 'const':
                const, var = 2, 1
            else:
                const = None

            if expression[0] == "add":
                if expression[1][0] == expression[2][0] == "const":
                    self.gen_const(expression[1][1] + expression[2][1], target_reg)
                    self.code.append(f"GET {target_reg}")
                    self.code.append(f"PUT {r_h}")

                elif expression[1] == expression[2]:
                    self.calculate_expression(expression[1], target_reg)
                    self.code.append(f"SHL {target_reg}")
                    self.code.append(f"GET {target_reg}")
                    self.code.append(f"PUT {r_h}")

                else:
                    if(expression[1][0] == "load" and expression[2][0] == "const"):
                        self.calculate_expression(expression[1], second_reg)
                        self.calculate_expression(expression[2], third_reg)
                        self.code.append(f"ADD {second_reg}")
                        self.code.append(f"PUT {r_h}")

                    elif(expression[1][0] == "const" and expression[2][0] == "load"):
                        self.calculate_expression(expression[1], second_reg)
                        self.calculate_expression(expression[2], third_reg)
                        self.code.append(f"ADD {second_reg}")
                        self.code.append(f"PUT {r_h}")
                    else:
                        self.calculate_expression(expression[1], second_reg)
                        self.code.append(f"PUT {sixth_reg}")
                        self.calculate_expression(expression[2], third_reg)
                        self.code.append(f"ADD {sixth_reg}")
                        self.code.append(f"PUT {r_h}")

            elif expression[0] == "sub":
                if expression[1][0] == expression[2][0] == "const":
                    val = max(0, expression[1][1] - expression[2][1])
                    if val:
                        self.gen_const(val, target_reg)
                        self.code.append(f"GET {target_reg}")
                        self.code.append(f"PUT {r_h}")
                    else:
                        self.code.append(f"RST {target_reg}")
                        self.code.append(f"GET {target_reg}")
                        self.code.append(f"PUT {r_h}")

                elif expression[1] == expression[2]:

                    self.code.append(f"RST {target_reg}")
                    self.code.append(f"GET {target_reg}")
                    self.code.append(f"PUT {r_h}")


                elif const and const == 1 and expression[const][1] == 0:

                    self.code.append(f"RST {target_reg}")
                    self.code.append(f"GET {target_reg}")
                    self.code.append(f"PUT {r_h}")

                else:
                    if (expression[1][0] == "load" and expression[2][0] == "const"):
                        self.calculate_expression(expression[1], second_reg)
                        self.calculate_expression(expression[2], third_reg)
                        self.code.append(f"GET {second_reg}")
                        self.code.append(f"SUB {third_reg}")
                        self.code.append(f"PUT {r_h}")
                    elif (expression[1][0] == "const" and expression[2][0] == "load"):

                        self.calculate_expression(expression[1], third_reg)
                        self.calculate_expression(expression[2], second_reg)
                        self.code.append(f"PUT {sixth_reg}")
                        self.code.append(f"GET {third_reg}")
                        self.code.append(f"SUB {sixth_reg}")
                        self.code.append(f"PUT {r_h}")
                    else:
                        self.calculate_expression(expression[1], second_reg)
                        self.code.append(f"PUT {second_reg}")
                        self.calculate_expression(expression[2], third_reg)
                        self.code.append(f"PUT {sixth_reg}")
                        self.code.append(f"GET {second_reg}")
                        self.code.append(f"SUB {sixth_reg}")
                        self.code.append(f"PUT {r_h}")

            elif expression[0] == "mul":
                if expression[1][0] == expression[2][0] == "const":
                    self.gen_const(expression[1][1] * expression[2][1], target_reg)
                    self.code.append(f"GET {target_reg}")
                    self.code.append(f"PUT {r_h}")
                    return

                elif const:
                    val = expression[const][1]
                    if val == 0:
                        self.code.append(f"RST {target_reg}")
                        self.code.append(f"GET {target_reg}")
                        self.code.append(f"PUT {r_h}")
                        return
                    elif val == 1:
                        self.calculate_expression(expression[var], target_reg)
                        self.code.append(f"GET {target_reg}")
                        self.code.append(f"PUT {r_h}")
                        return
                    elif val & (val - 1) == 0:

                        self.calculate_expression(expression[var], target_reg)
                        self.code.append(f"GET {target_reg}")
                        self.code.append(f"PUT {r_h}")
                        while val > 1:
                            self.code.append(f"SHL {target_reg}")
                            self.code.append(f"GET {target_reg}")
                            self.code.append(f"PUT {r_h}")
                            val /= 2
                        return



                if expression[1][0] == "load" and expression[2][0] == "const":
                    self.calculate_expression(expression[1], second_reg)
                    self.code.append(f"PUT {second_reg}")
                    self.calculate_expression(expression[2], third_reg)
                    self.perform_multiplication(second_reg, third_reg, fourth_reg)
                    self.code.append(f"GET {fourth_reg}")
                    self.code.append(f"PUT {second_reg}")
                    self.code.append(f"PUT {r_h}")
                elif expression[2][0] == "load" and expression[1][0] == "const":
                    self.calculate_expression(expression[1], second_reg)
                    self.calculate_expression(expression[2], third_reg)
                    self.code.append(f"PUT {third_reg}")
                    self.perform_multiplication(second_reg, third_reg, fourth_reg)
                    self.code.append(f"GET {fourth_reg}")
                    self.code.append(f"PUT {second_reg}")
                    self.code.append(f"PUT {r_h}")
                else:
                    self.calculate_expression(expression[1], second_reg)
                    self.code.append(f"PUT {second_reg}")
                    self.calculate_expression(expression[2], third_reg)
                    self.code.append(f"PUT {third_reg}")

                    self.perform_multiplication(second_reg, third_reg, fourth_reg)
                    self.code.append(f"GET {fourth_reg}")
                    self.code.append(f"PUT {r_h}")

            elif expression[0] == "div":
                if expression[1][0] == expression[2][0] == "const":
                    if expression[2][1] > 0:
                        self.gen_const(expression[1][1] // expression[2][1], target_reg)
                        self.code.append(f"GET {target_reg}")
                        self.code.append(f"PUT {r_h}")
                    else:
                        self.code.append(f"RST {target_reg}")
                        self.code.append(f"GET {target_reg}")
                        self.code.append(f"PUT {r_h}")
                    return

                elif const and const == 1 and expression[const][1] == 0:
                    self.code.append(f"RST {target_reg}")
                    self.code.append(f"GET {target_reg}")
                    self.code.append(f"PUT {r_h}")
                    return

                elif const and const == 2:
                    val = expression[const][1]
                    if val == 0:
                        self.code.append(f"RST {target_reg}")
                        self.code.append(f"GET {target_reg}")
                        self.code.append(f"PUT {r_h}")
                        return
                    elif val == 1:
                        self.calculate_expression(expression[var], second_reg)
                        self.code.append(f"GET {target_reg}")
                        self.code.append(f"PUT {r_h}")
                        return
                    elif val & (val - 1) == 0:
                        self.calculate_expression(expression[var], second_reg)
                        self.code.append(f"GET {target_reg}")
                        self.code.append(f"PUT {r_h}")
                        while val > 1:
                            self.code.append(f"SHR {target_reg}")
                            self.code.append(f"GET {target_reg}")
                            self.code.append(f"PUT {r_h}")
                            val /= 2
                        return
                if(expression[1][0] == "load" and expression[2][0] == "const"):
                    self.calculate_expression(expression[1], second_reg)
                    self.code.append(f"PUT {second_reg}")
                    self.calculate_expression(expression[2], third_reg)
                    self.perform_division(fourth_reg, fifth_reg, second_reg, third_reg)
                    self.code.append(f"GET {fourth_reg}")
                    self.code.append(f"PUT {second_reg}")
                    self.code.append(f"PUT {r_h}")
                elif (expression[2][0] == "load" and expression[1][0] == "const"):
                    self.calculate_expression(expression[1], second_reg)
                    self.calculate_expression(expression[2], third_reg)
                    self.code.append(f"PUT {third_reg}")
                    self.perform_division(fourth_reg, fifth_reg, second_reg, third_reg)
                    self.code.append(f"GET {fourth_reg}")
                    self.code.append(f"PUT {second_reg}")
                    self.code.append(f"PUT {r_h}")
                elif (expression[2][0] == "load" and expression[1][0] == "load"):
                    self.calculate_expression(expression[1], second_reg)
                    self.code.append(f"PUT {second_reg}")
                    self.calculate_expression(expression[2], third_reg)
                    self.code.append(f"PUT {third_reg}")
                    self.perform_division(fourth_reg, fifth_reg, second_reg, third_reg)
                    self.code.append(f"GET {fourth_reg}")
                    self.code.append(f"PUT {second_reg}")
                    self.code.append(f"PUT {r_h}")

            elif expression[0] == "mod":
                if expression[1][0] == expression[2][0] == "const":
                    if expression[2][1] > 0:
                        self.gen_const(expression[1][1] % expression[2][1], target_reg)
                        self.code.append(f"GET {target_reg}")
                        self.code.append(f"PUT {r_h}")
                    else:
                        self.code.append(f"RST {target_reg}")
                        self.code.append(f"GET {target_reg}")
                        self.code.append(f"PUT {r_h}")
                    return

                elif expression[1] == expression[2]:
                    self.code.append(f"RST {target_reg}")
                    self.code.append(f"GET {target_reg}")
                    self.code.append(f"PUT {r_h}")
                    return

                elif const and const == 1 and expression[const][1] == 0:
                    self.code.append(f"RST {target_reg}")
                    self.code.append(f"GET {target_reg}")
                    self.code.append(f"PUT {r_h}")
                    return

                elif const and const == 2:
                    val = expression[const][1]
                    if val < 2:
                        self.code.append(f"RST {target_reg}")
                        self.code.append(f"GET {target_reg}")
                        self.code.append(f"PUT {r_h}")
                        return
                if (expression[1][0] == "load" and expression[2][0] == "const"):
                    self.calculate_expression(expression[1], second_reg)
                    self.code.append(f"PUT {second_reg}")
                    self.calculate_expression(expression[2], third_reg)
                    self.perform_division(fourth_reg, fifth_reg, second_reg, third_reg)
                    self.code.append(f"GET {fifth_reg}")
                    self.code.append(f"PUT {second_reg}")
                    self.code.append(f"PUT {r_h}")
                elif (expression[2][0] == "load" and expression[1][0] == "const"):
                    self.calculate_expression(expression[1], second_reg)
                    self.calculate_expression(expression[2], third_reg)
                    self.code.append(f"PUT {third_reg}")
                    self.perform_division(fourth_reg, fifth_reg, second_reg, third_reg)
                    self.code.append(f"GET {fifth_reg}")
                    self.code.append(f"PUT {second_reg}")
                    self.code.append(f"PUT {r_h}")
                elif (expression[2][0] == "load" and expression[1][0] == "load"):
                    self.calculate_expression(expression[1], second_reg)
                    self.code.append(f"PUT {second_reg}")
                    self.calculate_expression(expression[2], third_reg)
                    self.code.append(f"PUT {third_reg}")
                    self.perform_division(fourth_reg, fifth_reg, second_reg, third_reg)
                    self.code.append(f"GET {fifth_reg}")
                    self.code.append(f"PUT {third_reg}")
                    self.code.append(f"PUT {r_h}")

    def perform_division(self, quotient_reg='a', remainder_reg='b', dividend_reg='c',
                         divisor_reg='d'):

        first_line = self.first_line + len(self.code)-1
        self.code.append(f"RST {quotient_reg}")
        self.code.append(f"RST {remainder_reg}")
        self.code.append(f"GET {divisor_reg}")
        self.code.append(f"JZERO {first_line + 42}")
        self.code.append(f"GET {dividend_reg}")
        self.code.append(f"PUT {remainder_reg}")
        self.code.append(f"GET {divisor_reg}")
        self.code.append(f"PUT {dividend_reg}")
        self.code.append(f"RST a")
        self.code.append(f"ADD {remainder_reg}")
        self.code.append(f"SUB {dividend_reg}")
        self.code.append(f"JZERO {first_line + 21}")
        self.code.append(f"RST a")
        self.code.append(f"ADD {dividend_reg}")
        self.code.append(f"SUB {remainder_reg}")
        self.code.append(f"JZERO {first_line + 19}")
        self.code.append(f"SHR {dividend_reg}")
        self.code.append(f"JUMP {first_line + 21}")
        self.code.append(f"SHL {dividend_reg}")
        self.code.append(f"JUMP {first_line + 13}")


        self.code.append(f"RST a")
        self.code.append(f"ADD {dividend_reg}")
        self.code.append(f"SUB {remainder_reg}")
        self.code.append(f"JZERO {first_line + 26}")
        self.code.append(f"JUMP {first_line + 42}")
        self.code.append(f"GET {remainder_reg}")
        self.code.append(f"SUB {dividend_reg}")
        self.code.append(f"PUT {remainder_reg}")
        self.code.append(f"INC {quotient_reg}")


        self.code.append(f"RST a")
        self.code.append(f"ADD {dividend_reg}")
        self.code.append(f"SUB {remainder_reg}")
        self.code.append(f"JZERO {first_line + 21}")
        self.code.append(f"SHR {dividend_reg}")
        self.code.append(f"RST a")
        self.code.append(f"ADD {divisor_reg}")
        self.code.append(f"SUB {dividend_reg}")
        self.code.append(f"JZERO {first_line + 40}")
        self.code.append(f"JUMP {first_line + 42}")
        self.code.append(f"SHL {quotient_reg}")
        self.code.append(f"JUMP {first_line + 30}")

    def perform_multiplication(self, second_reg='b', third_reg='c', temp_res_reg='d'):
        first_line = self.first_line + len(self.code)-1
        self.code.append(f"RST {temp_res_reg}")
        self.code.append(f"GET {third_reg}")
        self.code.append(f"SUB {second_reg}")
        self.code.append(f"JPOS {first_line + 21}")
        self.code.append(f"JUMP {first_line + 8}")
        self.code.append(f"SHL {second_reg}")
        self.code.append(f"SHR {third_reg}")

        self.code.append(f"GET {third_reg}")
        self.code.append(f"JZERO {first_line + 32}")
        self.code.append(f"SHR {third_reg}")
        self.code.append(f"SHL {third_reg}")
        self.code.append(f"SUB {third_reg}")
        self.code.append(f"JPOS {first_line + 15}")
        self.code.append(f"JUMP {first_line + 6}")

        self.code.append(f"GET {temp_res_reg}")
        self.code.append(f"ADD {second_reg}")
        self.code.append(f"PUT {temp_res_reg}")
        self.code.append(f"JUMP {first_line + 6}")


        self.code.append(f"SHL {third_reg}")
        self.code.append(f"SHR {second_reg}")

        self.code.append(f"GET {second_reg}")
        self.code.append(f"JZERO {first_line + 32}")
        self.code.append(f"SHR {second_reg}")
        self.code.append(f"SHL {second_reg}")
        self.code.append(f"SUB {second_reg}")
        self.code.append(f"JPOS {first_line + 28}")
        self.code.append(f"JUMP {first_line + 19}")

        self.code.append(f"GET {temp_res_reg}")
        self.code.append(f"ADD {third_reg}")
        self.code.append(f"PUT {temp_res_reg}")
        self.code.append(f"JUMP {first_line + 19}")

    def simplify_condition(self, condition):
        if condition[1][0] == "const" and condition[2][0] == "const":
            if condition[0] == "le":
                return condition[1][1] <= condition[2][1]
            elif condition[0] == "ge":
                return condition[1][1] >= condition[2][1]
            elif condition[0] == "lt":
                return condition[1][1] < condition[2][1]
            elif condition[0] == "gt":
                return condition[1][1] > condition[2][1]
            elif condition[0] == "eq":
                return condition[1][1] == condition[2][1]
            elif condition[0] == "ne":
                return condition[1][1] != condition[2][1]

        elif condition[1][0] == "const" and condition[1][1] == 0:
            if condition[0] == "le":
                return True
            elif condition[0] == "gt":
                return False
            else:
                return condition

        elif condition[2][0] == "const" and condition[2][1] == 0:
            if condition[0] == "ge":
                return True
            elif condition[0] == "lt":
                return False
            else:
                return condition

        elif condition[1] == condition[2]:
            if condition[0] in ["ge", "le", "eq"]:
                return True
            else:
                return False

        else:
            return condition

    def check_condition(self, condition, second_reg='b', third_reg='c'):
        if condition[1][0] == "const" and condition[1][1] == 0:
            if condition[0] == "ge" or condition[0] == "eq":
                self.calculate_expression(condition[2], second_reg)
                self.code.append(f"GET {r_h}")
                self.code.append(f"JZERO {self.first_line +len(self.code) + 2}")
                self.code.append("JUMP finish")

            elif condition[0] == "lt" or condition[0] == "ne":
                self.calculate_expression(condition[2], second_reg)
                self.code.append(f"GET {r_h}")
                self.code.append(f"JZERO finish")

        elif condition[2][0] == "const" and condition[2][1] == 0:

            if condition[0] == "le" or condition[0] == "eq":
                self.calculate_expression(condition[1], second_reg)
                self.code.append(f"GET {r_h}")
                self.code.append(f"JZERO {self.first_line + len(self.code) + 2}")
                self.code.append("JUMP finish")

            elif condition[0] == "gt" or condition[0] == "ne":
                self.calculate_expression(condition[1], second_reg)
                self.code.append(f"GET {r_h}")
                self.code.append(f"JZERO finish")

        else:
            if condition[1][0] == "load" and condition[2][0] == "const":
                self.calculate_expression(condition[1], second_reg)
                self.code.append(f"PUT {second_reg}")
                self.calculate_expression(condition[2], third_reg)
            elif condition[1][0] == "const" and condition[2][0] == "load":
                self.calculate_expression(condition[1], second_reg)
                self.calculate_expression(condition[2], third_reg)
                self.code.append(f"PUT {third_reg}")
            elif condition[2][0] == "load" and condition[1][0] == "load":
                self.calculate_expression(condition[1], second_reg)
                self.code.append(f"PUT {second_reg}")
                self.calculate_expression(condition[2], third_reg)
                self.code.append(f"PUT {third_reg}")
            else:
                self.calculate_expression(condition[1], second_reg)
                self.calculate_expression(condition[2], third_reg)

            if condition[0] == "gt":
                self.code.append(f"RST a")
                self.code.append(f"GET {second_reg}")
                self.code.append(f"SUB {third_reg}")
                self.code.append(f"JPOS {self.first_line +len(self.code) + 2}")
                self.code.append(f"JUMP finish")

            elif condition[0] == "lt":
                self.code.append(f"RST a")
                self.code.append(f"GET {third_reg}")
                self.code.append(f"SUB {second_reg}")
                self.code.append(f"JPOS {self.first_line +len(self.code) + 2}")
                self.code.append(f"JUMP finish")

            elif condition[0] == "ge":
                self.code.append(f"RST a")
                self.code.append(f"GET {third_reg}")
                self.code.append(f"SUB {second_reg}")
                self.code.append(f"JZERO {self.first_line +len(self.code) + 2}")
                self.code.append(f"JUMP finish")

            elif condition[0] == "le":
                #8>1
                self.code.append(f"RST a")
                self.code.append(f"GET {second_reg}")
                self.code.append(f"SUB {third_reg}")

                self.code.append(f"JZERO {self.first_line +len(self.code) + 2}")
                self.code.append(f"JUMP finish")

            elif condition[0] == "eq":
                self.code.append(f"RST a")
                self.code.append(f"GET {third_reg}")
                self.code.append(f"SUB {second_reg}")
                self.code.append(f"JZERO {self.first_line +len(self.code) + 2}")
                self.code.append(f"JUMP {self.first_line +len(self.code) + 5}")
                self.code.append(f"RST a")
                self.code.append(f"GET {second_reg}")
                self.code.append(f"SUB {third_reg}")
                self.code.append(f"JZERO {self.first_line +len(self.code) + 2}")
                self.code.append(f"JUMP finish")

            elif condition[0] == "ne":
                self.code.append(f"RST a")
                self.code.append(f"GET {third_reg}")
                self.code.append(f"SUB {second_reg}")
                self.code.append(f"JPOS {self.first_line +len(self.code) + 7}")
                self.code.append(f"RST a")
                self.code.append(f"GET {second_reg}")
                self.code.append(f"SUB {third_reg}")
                self.code.append(f"JPOS {self.first_line +len(self.code) + 2}")
                self.code.append(f"JUMP finish")

    def load_array_at(self, array, index, reg1, reg2):
        self.load_array_address_at(array, index, reg1, reg2)
        self.code.append(f"LOAD {reg1}")
        if reg1 != 'a':
            self.code.append(f"PUT {reg1}")

    def load_array_address_at(self, array, index, reg1, reg2):
        if type(index) == int:
            address = self.symbols[array].get_memory_offset_at(index)
            self.gen_const(address, reg1)
        elif type(index) == tuple:

            if type(index[1]) == tuple:
                self.load_variable(index[1], reg1)
            else:
                if index[1] in self.links:
                    self.load_variable_link_address(index[1], reg1)
                    self.code.append(f"LOAD {reg1}")
                    if reg1 != 'a':
                        self.code.append(f"PUT {reg1}")
                else:
                    if not self.symbols[index[1]].initialized:
                        raise Exception(f"Trying to use {array}[{index[1]}] where variable {index[1]} is uninitialized")
                    self.load_variable(index[1], reg1)

            var = self.symbols[array].memory_offset

            temp_reg = "g"
            self.gen_const(var, temp_reg)
            self.code.append(f"ADD {temp_reg}")
            self.code.append(f"PUT {reg1}")

    def load_variable(self, name, reg):
        if depth > 0:
            if name in self.symbols:
                if not self.symbols[name].initialized:
                    print(f"WARNING: variable {name} might be used before it was initialized in procedure {self.name}")
                self.load_variable_address(name, reg)
                self.code.append(f"LOAD {reg}")
                if reg != 'a':
                    self.code.append(f"PUT {reg}")
            else:
                raise Exception(f"Undeclared variable {name}")

        else:
            if name in self.symbols:
                self.load_variable_address(name, reg)
                self.code.append(f"LOAD {reg}")
                if reg != 'a':
                    self.code.append(f"PUT {reg}")
            else:
                raise Exception(f"Undeclared variable {name}")

    def load_variable_address(self, name, reg):
        address = self.symbols[name].memory_offset
        self.gen_const(address, reg)

    def load_variable_link_address(self, name, reg):
        if name in self.links:
            link_address = self.links[name].memory_offset
            self.gen_const(link_address, reg)
            self.code.append(f"LOAD {reg}")
            if reg != 'a':
                self.code.append(f"PUT {reg}")
        else:
            raise Exception(f"Such variable link doesn't exist {name}")

    def load_array_link(self, array, index, reg1, reg2):
        if array in self.links:
            self.load_array_link_address(array, index, reg1, reg2)
            self.code.append(f"LOAD {reg1}")
            if reg1 != 'a':
                self.code.append(f"PUT {reg1}")
        else:
            raise Exception(f"Such array link doesn't exist {array}")

    def load_array_link_address(self, array, index, reg1, reg2):
        if type(index) == int:
            address = self.links[array].memory_offset
            self.gen_const(address, reg1)
            self.code.append(f"LOAD {reg1}")
            temp_reg = "e"
            self.gen_const(index, temp_reg)
            self.code.append(f"ADD {temp_reg}")
            self.code.append(f"PUT {reg1}")
        elif type(index) == tuple:
            if type(index[1]) == tuple:
                self.load_variable(index[1], reg1)
            else:
                if index[1] in self.links:
                    self.load_variable_link_address(index[1], reg1)
                    self.code.append(f"LOAD {reg1}")
                    if reg1 != 'a':
                        self.code.append(f"PUT {reg1}")
                else:

                    if not self.symbols[index[1]].initialized:
                        raise Exception(f"Trying to use {array}[{index[1]}] where variable {index[1]} is uninitialized")
                    self.load_variable(index[1], reg1)

            var = self.links[array].memory_offset
            temp_reg = "g"
            self.gen_const(var, temp_reg)
            self.code.append(f"LOAD {temp_reg}")
            self.code.append(f"ADD {reg1}")
            self.code.append(f"PUT {reg1}")

    def prepare_consts_before_block(self, consts, reg1='a'):
        for c in consts:
            address = self.consts[c]
            self.gen_const(address, reg1)
            self.code.append(f"STORE {reg1}")
            self.code.append(f"RST {reg1}")

    def gen_const(self, const, reg='a'):
        self.code.append(f"RST {reg}")
        if const > 0:
            bits = bin(const)[2:]
            for bit in bits[:-1]:
                if bit == '1':
                    self.code.append(f"INC {reg}")
                self.code.append(f"SHL {reg}")
            if bits[-1] == '1':
                self.code.append(f"INC {reg}")

    def init_fields(self, name, procedure_table):
        list_of_procedures[name] = procedure_table[name]
        self.name = name
        self.procedure_table = procedure_table
        self.procedure = procedure_table[name]
        self.commands = self.procedure.commands
        self.symbols = self.procedure.symbols
        self.consts = self.procedure.consts
        self.links = self.procedure.links
        self.code = []
        self.first_line = procedure_table.current_line
