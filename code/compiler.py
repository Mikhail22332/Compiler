from sly import Lexer, Parser
from program import Program
from list import List
from procedure import Procedure, Variable
import sys


class ImpLexer(Lexer):
    tokens = {PROGRAM, PROCEDURE, IS, IN, END, WHILE, DO, ENDWHILE, 
              REPEAT, UNTIL, IF, THEN, ELSE, ENDIF, T, READ, WRITE,
              GETS, NEQ, GEQ, LEQ, EQ, GT, LT, PID, NUM, GETS}
    literals = {'+', '-', '*', '/', '%', ',', ':', ';', '(', ')', '[', ']'}
    ignore = ' \t'

    @_(r'\#.*')
    def ignore_comment(self, t):
        self.lineno += t.value.count('\n')

    @_(r'\n+')
    def ignore_newline(self, t):
        self.lineno += len(t.value)

    PROGRAM = r"PROGRAM"

    ENDWHILE = r"ENDWHILE"
    WHILE = r"WHILE"
    DO = r"DO"

    REPEAT = r"REPEAT"
    UNTIL = r"UNTIL"

    ENDIF = r"ENDIF"
    IF = r"IF"
    THEN = r"THEN"
    ELSE = r"ELSE"

    PROCEDURE = r"PROCEDURE"
    IS = r"IS"
    IN = r"IN"
    END = r"END"

    READ = r"READ"
    WRITE = r"WRITE"

    GETS = r":="
    NEQ = r"!="
    GEQ = r">="
    LEQ = r"<="
    EQ = r"="
    GT = r">"
    LT = r"<"
    PID = r"[_a-z]+"

    T = r"T"

    @_(r'\d+')
    def NUM(self, t):
        t.value = int(t.value)
        return t

    def error(self, t):
        raise Exception(f"Illegal character '{t.value[0]}'")


class ImpParser(Parser):
    tokens = ImpLexer.tokens
    currentProcedure = Procedure(0)
    code = None
    procedureTable = Program()
    consts = set()
    index = 0
    jump_proc = ""
    passed_params = []

    @_('procedures main')
    def program_all(self, p):
        return self.procedureTable
    
    @_('procedures PROCEDURE proc_head IS declarations IN commands END')
    def procedures(self, p):
        self.currentProcedure.set_commands(p.commands)
        self.procedureTable.add_procedure(self.currentProcedure)

    @_('procedures PROCEDURE proc_head IS IN commands END')
    def procedures(self, p):
        self.currentProcedure.set_commands(p.commands)
        self.procedureTable.add_procedure(self.currentProcedure)
    
    @_('')
    def procedures(self, p):
        pass

    @_('program IS declarations IN commands END')
    def main(self, p):
        self.currentProcedure.set_commands(p.commands)
        self.procedureTable.add_procedure(self.currentProcedure)
    
    @_('program IS IN commands END')
    def main(self, p):
        self.currentProcedure.set_commands(p.commands)
        self.procedureTable.add_procedure(self.currentProcedure)
    
    @_('PROGRAM')
    def program(self, p):
        self.currentProcedure = Procedure(self.procedureTable.memory_offset)
        self.currentProcedure.name = "PROGRAM"

    @_('commands command')
    def commands(self, p):
        return p[0] + [p[1]]

    @_('command')
    def commands(self, p):
        return [p[0]]

    @_('identifier GETS expression ";"')
    def command(self, p):
        return "assign", p[0], p[2]

    @_('IF condition THEN commands ELSE commands ENDIF')
    def command(self, p):
        resp = "ifelse", p[1], p[3], p[5], self.consts.copy()
        self.consts.clear()
        return resp

    @_('IF condition THEN commands ENDIF')
    def command(self, p):
        resp = "if", p[1], p[3], self.consts.copy()
        self.consts.clear()
        return resp

    @_('WHILE condition DO commands ENDWHILE')
    def command(self, p):
        resp = "while", p[1], p[3], self.consts.copy()
        self.consts.clear()
        return resp

    @_('REPEAT commands UNTIL condition ";"')
    def command(self, p):
        return "until", p[3], p[1]

    @_('proc_call ";"')
    def command(self, p):
        return 'proc_call', p[0]

    @_('READ identifier ";"')
    def command(self, p):
        return "read", p[1]

    @_('WRITE value ";"')
    def command(self, p):
        if p[1][0] == "const":
            self.consts.add(int(p[1][1]))
        return "write", p[1]

    @_('PID "(" args_decl ")"')
    def proc_head(self, p):
        if p[0] in self.procedureTable:
            raise Exception(f"Redeclaration of {p[0]} procedure at line {p.lineno}")
        self.currentProcedure.name = p[0]

    @_('PID "(" args ")"')
    def proc_call(self, p):
        self.jump_proc = p[0]
        if p[0] not in self.procedureTable:
            raise Exception(f"Unknown procedure at line {p.lineno}")
        if self.currentProcedure.name == p[0]:
            raise Exception(f"Recursion call at line {p.lineno}")

        procedure_to_jump = self.procedureTable[self.jump_proc]
        params = procedure_to_jump.parameters
        if len(self.passed_params) < len(self.procedureTable[self.jump_proc].parameters):
            raise Exception(f"Less arguments passed to procedure {self.jump_proc} at line {p.lineno}")
        if len(self.passed_params) > len(params):
            raise Exception(f"Too many arguments passed to procedure {self.jump_proc} at line {p.lineno}")
        for item in range(len(self.passed_params)):
            if self.passed_params[item] in self.currentProcedure.symbols.keys():
                if type(self.currentProcedure.symbols[self.passed_params[item] ]) == List and params[item] == "var" or type(self.currentProcedure.symbols[self.passed_params[item] ]) == Variable and params[item] == "array":
                    raise Exception(f"Bad parameters for procedure {self.jump_proc} at line {p.lineno}")
            elif self.passed_params[item] in self.currentProcedure.links.keys():
                if self.currentProcedure.links[self.passed_params[item] ].isArray and params[item] == "var" or not self.currentProcedure.links[self.passed_params[item] ].isArray and params[item] == "array":
                    raise Exception(f"Bad parameters for procedure {self.jump_proc} at line {p.lineno}")
        self.passed_params = []
        return p[0], p[2]

    @_('declarations "," PID')
    def declarations(self, p):
        if p[-1] in self.currentProcedure.links or p[-1] in self.currentProcedure.symbols:
            raise Exception(f"Redeclaration of variable {p[-1]} at line {p.lineno}")

        self.currentProcedure.add_variable(p[-1])

    @_('declarations "," PID "[" NUM "]"')
    def declarations(self, p):
        if p[4] <= 0:
            raise Exception(f"Wrong range in declaration of {p[2]} at line {p.lineno}")
        elif p[4] > 100:
            raise Exception(f"More than 100 elements in array {p[2]} at line {p.lineno}")
        self.currentProcedure.add_array(p[2], p[4])

    @_('PID')
    def declarations(self, p):
        if p[-1] in self.currentProcedure.links or p[-1] in self.currentProcedure.symbols :
            raise Exception(f"Redeclaration of variable {p[-1]} at line {p.lineno}")
        self.currentProcedure.add_variable(p[-1])

    @_('PID "[" NUM "]"')
    def declarations(self, p):
        if p[2] <= 0:
            raise Exception(f"Wrong range in declaration of {p[0]} at line {p.lineno}")
        elif p[2] > 100:
            raise Exception(f"More than 100 elements in array {p[0]} at line {p.lineno}")
        self.currentProcedure.add_array(p[0], p[2])

    @_('args_decl "," PID')
    def args_decl(self, p):
        self.currentProcedure.add_variable_link(p[2])
        self.currentProcedure.parameters.append("var")

    @_('args_decl "," T PID ')
    def args_decl(self, p):
        self.currentProcedure.add_array_link(p[3])
        self.currentProcedure.parameters.append("array")

    @_('PID')
    def args_decl(self, p):
        self.currentProcedure = Procedure(self.procedureTable.memory_offset)
        self.currentProcedure.add_variable_link(p[0])
        self.currentProcedure.parameters.append("var")

    @_('T PID')
    def args_decl(self, p):
        self.currentProcedure = Procedure(self.procedureTable.memory_offset)
        self.currentProcedure.add_array_link(p[1])
        self.currentProcedure.parameters.append("array")

    @_('args "," PID')
    def args(self, p):
        if p[2] in self.currentProcedure.symbols.keys():
            self.passed_params.append(p[2])
            return p[0] + [("load", p[2])]
        elif p[2] in self.currentProcedure.links.keys():
            self.passed_params.append(p[2])
            return p[0] + [("load", p[2])]
        else:
            self.passed_params.append(p[2])
            return p[0] + [("undeclared", p[2])]

    @_('PID')
    def args(self, p):
        if p[0] in self.currentProcedure.symbols.keys():
            self.passed_params.append(p[0])
            return [("load", p[0])]
        elif p[0] in self.currentProcedure.links.keys():
            self.passed_params.append(p[0])
            return [("load", p[0])]
        else:
            self.passed_params.append(p[0])
            return [("undeclared", p[0])]

    @_('value')
    def expression(self, p):
        if (type(p[0]) == tuple):
            if (type(p[0][1]) == tuple):
                if p[0][1][1] not in self.currentProcedure.links.keys() and p[0][1][1] not in self.currentProcedure.symbols.keys() and p[0][1][1] not in self.currentProcedure.consts.keys():
                    raise Exception(f"Undeclared variable {p[0][1][1]} at line {p.lineno}")
            else:
                if p[0][1] not in self.currentProcedure.links.keys() and p[0][1] not in self.currentProcedure.symbols.keys() and p[0][1] not in self.currentProcedure.consts.keys():
                    raise Exception(f"Undeclared variable {p[0][1]} at line {p.lineno}")
        else:
            if p[0][1] not in self.currentProcedure.links.keys() and p[0][1] not in self.currentProcedure.symbols.keys():
                raise Exception(f"Undeclared variable {p[0][1]} at line {p.lineno}")

        return p[0]

    @_('value "+" value')
    def expression(self, p):
        return "add", p[0], p[2]

    @_('value "-" value')
    def expression(self, p):
        return "sub", p[0], p[2]

    @_('value "*" value')
    def expression(self, p):
        return "mul", p[0], p[2]

    @_('value "/" value')
    def expression(self, p):
        return "div", p[0], p[2]

    @_('value "%" value')
    def expression(self, p):
        return "mod", p[0], p[2]

    @_('value EQ value')
    def condition(self, p):
        return "eq", p[0], p[2]

    @_('value NEQ value')
    def condition(self, p):
        return "ne", p[0], p[2]

    @_('value LT value')
    def condition(self, p):
        return "lt", p[0], p[2]

    @_('value GT value')
    def condition(self, p):
        return "gt", p[0], p[2]

    @_('value LEQ value')
    def condition(self, p):
        return "le", p[0], p[2]

    @_('value GEQ value')
    def condition(self, p):
        return "ge", p[0], p[2]

    @_('NUM')
    def value(self, p):
        self.currentProcedure.add_const(p[0])
        return "const", p[0]

    @_('identifier')
    def value(self, p):
        return "load", p[0]

    @_('PID')
    def identifier(self, p):
        if p[0] not in self.currentProcedure.links.keys() and p[0] not in self.currentProcedure.symbols.keys():
            if(type(p[0]) == tuple):
                print(1)
                raise Exception(f"Undeclared variable {p[0][1]} at line {p.lineno}")
            else:
                raise Exception(f"Undeclared variable {p[0]} at line {p.lineno}")
        elif p[0] in self.currentProcedure.symbols.keys() and type(self.currentProcedure.symbols[p[0]]) == List:
            raise Exception(f"Incorrect usage of array {p[0]} at line {p.lineno}")
        if p[0] in self.currentProcedure.symbols:
            self.currentProcedure.symbols[p[0]].pre_set = True
            return p[0]
        elif p[0] in self.currentProcedure.links:
            return p[0]
        else:
            return ("undeclared", p[0])

    @_('PID "[" NUM "]"')
    def identifier(self, p):
        if p[0] in self.currentProcedure.symbols and type(self.currentProcedure.symbols[p[0]]) == List:
            if p[2] >= self.currentProcedure.symbols[p[0]].size:
                raise Exception(f"Index {p[2]} out of range for array {p[0]} at line {p.lineno}")
            return "array", p[0], p[2]
        elif p[0] in self.currentProcedure.links:
            return "array", p[0], p[2]
        else:
            raise Exception(f"Undeclared array {p[0]} at line {p.lineno}")

    @_('PID "[" PID "]"')
    def identifier(self, p):
        if p[0] in self.currentProcedure.symbols and type(self.currentProcedure.symbols[p[0]]) == List:
            if p[2] in self.currentProcedure.symbols and type(self.currentProcedure.symbols[p[2]]) == Variable:
                if not self.currentProcedure.symbols[p[2]].pre_set:
                    raise Exception(f"Undeclared variable {p[2]} at line {p.lineno}")
                return "array", p[0], ("load", p[2])
            elif p[2] in self.currentProcedure.links:

                return "array", p[0], ("load", p[2])
            else:
                return "array", p[0], ("load", ("undeclared", p[2]))
        elif p[0] in self.currentProcedure.links:
            if p[2] in self.currentProcedure.symbols and type(self.currentProcedure.symbols[p[2]]) == Variable:
                if not self.currentProcedure.symbols[p[2]].pre_set:
                    raise Exception(f"Undeclared variable {p[2]} at line {p.lineno}")
                return "array", p[0], ("load", p[2])
            elif p[2] in self.currentProcedure.links:
                return "array", p[0], ("load", p[2])
            else:
                return "array", p[0], ("load", ("undeclared", p[2]))
        else:
            raise Exception(f"Undeclared array {p[0]} at line {p.lineno}")

    def error(self, token):
        raise Exception(f"Syntax error: '{token.value}' at line {token.lineno}")
        
if __name__ == '__main__':
    sys.tracebacklimit = 0
    lex = ImpLexer()
    pars = ImpParser()
    with open(sys.argv[1]) as in_f:
        text = in_f.read()
    tokenized = lex.tokenize(text)
    pars.parse(tokenized)
    procedureTable = pars.procedureTable
    procedureTable.code.append([f"JUMP main"])
    procedureTable.generate_code_to_file()
    with open(sys.argv[2], 'w') as out_f:
        for procedureCode in procedureTable.code:
            for line in procedureCode:
                print(line, file=out_f)

