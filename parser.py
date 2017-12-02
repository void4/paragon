from lark import Lark, Tree, Transformer
from assembler import assemble
from exalloc import d,s, MEMORY
import inspect
grammar = r"""

NAME: /[a-zA-Z_]\w*/
COMMENT: /#[^\n]*/
_NEWLINE: ( /\r?\n[\t ]*/ | COMMENT)+

_DEDENT: "<DEDENT>"
_INDENT: "<INDENT>"

%import common.ESCAPED_STRING
string: ESCAPED_STRING
number: DEC_NUMBER
DEC_NUMBER: /0|[1-9]\d*/i

%ignore /[\t \f]+/  // Whitespace

start: (_NEWLINE | stmt)*


?stmt: simple_stmt | compound_stmt
?simple_stmt: (expr_stmt | flow_stmt | func_call | write_stmt | dealloc_stmt | dearea_stmt) _NEWLINE
?expr_stmt: NAME "=" (test | expr) -> assign
          | test

write_stmt: "$write" "(" expr "," expr "," expr ")"
dealloc_stmt: "$dealloc" "(" expr ")"
dearea_stmt: "$dearea" "(" expr ")"
?flow_stmt: pass_stmt | return_stmt | halt_stmt | area_stmt
pass_stmt: "pass"
return_stmt: "$return" //[test | NAME]
?halt_stmt: "halt"
?area_stmt: "$area"


?test: or_test
?or_test: and_test ("or" and_test)*
?and_test: not_test ("and" not_test)*
?not_test: "not" not_test -> not
| comparison
?comparison: expr _comp_op expr
!_comp_op: "==" | "!="

?expr: arith_expr
?arith_expr: term (_add_op term)*
?term: factor (_mul_op factor)*
?factor: _factor_op factor | molecule
?molecule: func_call
         | molecule "[" [subscriptlist] "]" -> getitem
         | atom
func_call: NAME ["<" expr ["," expr] ">"] "(" [arglist] ")"
?atom: "[" listmaker "]"
     | primitive | NAME | number | ESCAPED_STRING

?primitive: stacklen | memorylen | arealen_expr | read_expr | sha256_expr
arealen_expr: "$arealen" "(" expr ")"
read_expr: "$read" "(" expr "," expr ")"
sha256_expr: "$sha256" "(" expr ")"
stacklen: "$stacklen"
memorylen: "$memorylen"

!_factor_op: "+"|"-"|"~"
!_add_op: "+"|"-"
!_mul_op: "*"|"/"|"%"

listmaker: test ("," test)* [","]
?subscriptlist: subscript ("," subscript)* [","]
subscript: test
arglist: (argument ",")* (argument [","])
argument: expr

?compound_stmt: if_stmt | while_stmt | funcdef
if_stmt: "if" test ":" suite ["else" ":" suite]
suite: _NEWLINE _INDENT _NEWLINE? stmt+ _DEDENT _NEWLINE?

while_stmt: "while" [test] ":" suite

funcdef: "def" NAME "(" [parameters] ")" ":" suite
parameters: paramvalue ("," paramvalue)*
?paramvalue: param
?param: NAME
"""

def indent(line):
    return (len(line)-len(line.lstrip(" ")))//4

def prep(code):
    code = code.split("\n")
    code.append("\n")
    current = 0
    lines = ""
    for line in code:
        ind = indent(line)
        if ind > current:
            prefix = "<INDENT>" * (ind-current)
        elif ind < current:
            prefix = "<DEDENT>" * (current-ind)
        else:
            prefix = ""
        current = ind
        lines += prefix + line.lstrip() + "\n"
    return lines

# Variable storage
area = 0

class Meta:

    def __init__(self):
        self.code = []
        self.vard = []
        self.fund = []

    def __add__(self, meta):
        if isinstance(meta, Meta):
            self.code += meta.code
            # Check for collisions here!
            self.vard = list(set().union(self.vard, meta.vard))
            #self.fund = list(set().union(self.fund, meta.fund))
            for fun in meta.fund:
                if self.getfun(fun[0]) is not None:
                    raise Exception("Function name collision!")
            self.fund += meta.fund
        else:
            self.code += meta
        return self

    def append(self, x):
        self.code += [x]

    def initvar(self, name):
        if not name in self.vard:
            self.vard.append(name)

    def getfunindex(self, name):
        for index, fun in enumerate(self.fund):
            if fun[0] == name:
                return index + 1 #AREA

    def getfun(self, name):
        for fun in self.fund:
            if fun[0] == name:
                return fun

    def initfun(self, name, fun):
        if not name in self.fund:
            self.fund.append([name, fun])
        else:
            raise Exception("Function name collision: %s" % name)

    def isint(v):
        try:
            int(v)
            return True
        except:
            return False

    def final(self):
        print(self.vard)
        for i, line in enumerate(self.code):
            if isinstance(line, list):
                name = line[1]
                pos = self.getfunindex(name)
                if pos is None:
                    pos = self.vard.index(name) + 1

                if pos is None:
                    raise Exception("Not found: %s" % name)

                self.code[i] = "%s %i" % (line[0], pos)

        asm = assemble(self.code)
        mem = [[0]*(len(self.vard)+1)]+[v for k,v in self.fund]
        sharp = [1,0,0,0]
        sharp += [len(asm), 0, len(mem)]
        sharp += [asm, [], mem]
        sharp[MEMORY][0][0] = len(sharp[MEMORY])
        print(sharp)
        print(s(sharp))
        print(d(s(sharp)))
        return s(sharp)

def parse(code):

    labeli = 0
    def genlabel():
        nonlocal labeli
        labeli += 1
        return str("label%i" % labeli)

    def varint(node):
        #print("varint", node)
        #print(node, dir(node), type(node), isinstance(node, str))#, node.data)
        if isinstance(node, list) or isinstance(node, Meta):
            return node
        elif isinstance(node, str):
            return ["PUSH %i" % area, ["PUSH", node.value], "READ"]
        elif node.data == "number" and node.children[0].type == "DEC_NUMBER":
            return ["PUSH %i" % int(node.children[0].value)]
        else:
            raise Exception("Fail")

    class MyTransformer(Transformer):

        def start(self, node):
            #print(node)
            m = sum(node, Meta())
            return m.final()

        def write_stmt(self, node):
            out = sum(node, Meta())
            out.append("WRITE")
            return out

        def dearea_stmt(self, node):
            out = sum(node, Meta())
            out.append("DEAREA")
            return out

        def dealloc_stmt(self, node):
            out = sum(node, Meta())
            out.append("DEALLOC")
            return out

        def suite(self, node):
            return sum(node, Meta())

        def funcdef(self, node):
            m = Meta()
            print(node)
            m.initfun(node[0].value, node[-1].final())

            print(m.fund)
            return m

        def func_call(self, node):
            print("CALL", len(node), node)
            m = Meta()

            # Increase area size
            m.append(["PUSH", node[0].value])
            m.append("PUSH %i" % (len(node[-1].children) * 2))
            m.append("ALLOC")

            # Increase number of child areas
            m.append(["PUSH", node[0].value])
            m.append("PUSH %i" % MEMORY)
            m.append(["PUSH", node[0].value])
            m.append("PUSH %i" % MEMORY)
            m.append("READ")
            m.append("PUSH %i" % len(node[-1].children))
            m.append("ADD")
            m.append("WRITE")

            for num, arg in enumerate(node[-1].children[::-1]):

                # WRITE AREA SIZE
                # Push area index
                m.append(["PUSH", node[0].value])
                # Put AREALEN on stack
                m.append("DUP")
                m.append("AREALEN")
                # Get length position
                m.append("PUSH %i" % (num*2+2))
                m.append("SUB")
                # Write length 1
                m.append("PUSH 1")
                m.append("WRITE")

                # WRITE VALUE
                # Push area index
                m.append(["PUSH", node[0].value])
                # Put AREALEN on stack
                m.append("DUP")
                m.append("AREALEN")
                # Get length position
                m.append("PUSH %i" % (num*2+1))
                m.append("SUB")
                m += varint(arg.children[0])
                m.append("WRITE")

            m.append(["PUSH", node[0].value])
            if len(node) == 2:
                m.append("PUSH 9999999")
                m.append("PUSH 9999999")
            elif len(node) == 3:
                m += varint(node[1])
                m.append("PUSH 9999999")
            elif len(node) == 4:
                m += varint(node[1])
                m += varint(node[2])

            m.append("RUN")
            return m

        def if_stmt(self, node):
            #print("ifstmt", node)
            out = Meta()
            out += node[0]

            end_label = genlabel()

            if len(node) == 3:
                else_label = genlabel()
                out.append("PUSH %s" % else_label)
            else:
                out.append("PUSH %s" % end_label)
            out.append("JZ")
            out += node[1]
            if len(node) == 3:
                out.append("PUSH %s" % end_label)
                out.append("JUMP")
                out.append(else_label+":")
                out += node[2]
            out.append(end_label+":")
            return out

        def stacklen(self, node):
            return ["STACKLEN"]

        def memorylen(self, node):
            return ["MEMORYLEN"]

        def while_stmt(self, node):
            #print("while", node)
            out = Meta()
            start_label = genlabel()
            end_label = genlabel()

            out.append(start_label+":")

            if len(node) == 2:
                out += node[0]

                out.append("NOT")
                out.append("PUSH %s" % end_label)
                out.append("JZ")

                out += node[1]
            else:
                out += node[0]

            out.append("PUSH %s" % start_label)
            out.append("JUMP")
            out.append(end_label+":")
            return out

        def comparison(self, node):
            out = []
            #print("==", node)
            out += varint(node[0])
            out += varint(node[2])
            out.append("SUB")
            if node[1].value == "==":
                out.append("NOT")
            return out

        def term(self, node):
            out = []
            out += varint(node[0])
            out += varint(node[2])
            out.append("%s" % {"*":"MUL", "/":"DIV", "%":"MOD"}[node[1].value])
            return out

        def arith_expr(self, node):
            out = []
            out += varint(node[0])
            out += varint(node[2])
            out.append("%s" % {"+":"ADD", "-":"SUB", "~":"NOT"}[node[1].value])
            return out

        def arealen_expr(self, node):
            out = varint(node[0])
            out.append("AREALEN")
            return out

        def read_expr(self, node):
            #print("read", node)
            out = Meta()
            out += varint(node[0])
            out += varint(node[1])
            out.append("READ")
            return out

        def sha256_expr(self, node):
            out = varint(node[0])
            out.append("SHA256")
            return out

        def pass_stmt(self, node):
            return []

        def return_stmt(self, node):
            m = Meta()
            m.append("PUSH 0")
            m.append("PUSH 0")
            m.append("MEMORYLEN")
            m.append("WRITE")
            m.append("RETURN")
            return m

        def halt_stmt(self, node):
            return ["HALT"]

        def area_stmt(self, node):
            return ["AREA"]

        def assign(self, node):
            m = Meta()
            #print("=",node)
            target = node[0]

            m.append("PUSH %i" % area)

            m.initvar(target.value)
            m.append(["PUSH", target.value])
            m += varint(node[1])
            m.append("WRITE")
            return m

    l = Lark(grammar, debug=True)

    prepped = prep(code)
    print(prepped)
    parsed = l.parse(prepped)
    print(parsed)

    obj = MyTransformer().transform(parsed)

    return obj
