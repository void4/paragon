from lark import Lark, Tree, Transformer

grammar = r"""

NAME: /[a-zA-Z_]\w*/
COMMENT: /#[^\n]*/
_NEWLINE: ( /\r?\n[\t ]*/ | COMMENT)+

_DEDENT: "<DEDENT>"
_INDENT: "<INDENT>"

%import common.ESCAPED_STRING
string: ESCAPED_STRING
?number: DEC_NUMBER
DEC_NUMBER: /0|[1-9]\d*/i

%ignore /[\t \f]+/  // Whitespace

start: (_NEWLINE | stmt)*


?stmt: simple_stmt | compound_stmt
?simple_stmt: (expr_stmt | flow_stmt | write_stmt | dealloc_stmt | dearea_stmt) _NEWLINE
?expr_stmt: NAME "=" (test | expr) -> assign
          | test

write_stmt: "$write" "(" expr "," expr "," expr ")"
dealloc_stmt: "$dealloc" "(" expr ")"
dearea_stmt: "$dearea" "(" expr ")"
?flow_stmt: pass_stmt | return_stmt | halt_stmt | area_stmt
pass_stmt: "pass"
return_stmt: "return" (test | NAME)
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
?molecule: molecule "(" [arglist] ")" -> func_call
         | molecule "[" [subscriptlist] "]" -> getitem
         | atom
?atom: "[" listmaker "]"
     | primitive | NAME | number | ESCAPED_STRING

?primitive: stacklen | memorylen | arealen_expr | read_expr | sha256_expr
arealen_expr: "$arealen" "(" expr ")"
read_expr: "$read" "(" expr "," expr ")"
sha256_expr: "$sha256" "(" expr ")"
?stacklen: "$stacklen"
?memorylen: "$memorylen"

!_factor_op: "+"|"-"|"~"
!_add_op: "+"|"-"
!_mul_op: "*"|"/"|"%"

listmaker: test ("," test)* [","]
?subscriptlist: subscript ("," subscript)* [","]
subscript: test
arglist: (argument ",")* (argument [","])
argument: test

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

def parse(code):
    vard = {

    }

    def init(name):
        nonlocal vard
        if name not in vard:
            vard[name] = len(vard)
        return vard[name]

    def var(name):
        nonlocal vard
        return vard[name]

    def varint(node):
        if isinstance(node, list):
            return node
        elif isinstance(node, Tree):
            if node.data == "stacklen":
                return ["STACKLEN"]
            elif node.data == "memorylen":
                return ["MEMORYLEN"]
            else:
                raise Exception("Unknown TREE")
        if node.type == "DEC_NUMBER":
            return ["PUSH %i" % int(node.value)]
        else:
            return ["PUSH %i" % area, "PUSH %i" % vard[node.value], "READ"]#["READ %i %i" % (area, var(node.value))]

    labeli = 0
    def genlabel():
        nonlocal labeli
        labeli += 1
        return str("label%i" % labeli)

    # Variable storage
    area = 0
    class MyTransformer(Transformer):

        def start(self, node):
            out = []
            out.append("AREA")
            out.append("PUSH %i" % area)
            out.append("PUSH %i" % len(vard))
            out.append("ALLOC")
            out += sum(node, [])
            return out

        def write_stmt(self, node):
            out = node[0]
            out = node[1]
            out = node[2]
            out.append("WRITE")
            return out

        def dearea_stmt(self, node):
            out = node[0]
            out.append("DEAREA")
            return out

        def dealloc_stmt(self, node):
            out = node[0]
            out.append("DEALLOC")
            return out

        def suite(self, node):
            return sum(node, [])

        def if_stmt(self, node):
            print("ifstmt", node)
            out = []
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

        def while_stmt(self, node):
            #print("while", node)
            out = []
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
            out = varint(node[0]) + varint(node[1])
            out.append("READ")
            return out

        def sha256_expr(self, node):
            out = varint(node[0])
            out.append("SHA256")
            return out

        def pass_stmt(self, node):
            return []

        def halt_stmt(self, node):
            return ["HALT"]

        def area_stmt(self, node):
            return ["AREA"]

        def assign(self, node):
            nonlocal vard
            #print("=",node)
            target = node[0]

            out = []
            out.append("PUSH %i" % area)
            if isinstance(target, str):
                if not target in vard:
                    vard[target] = len(vard)
                target = vard[target]
            out.append("PUSH %i" % target)
            out += varint(node[1])
            out.append("WRITE")
            return out

    l = Lark(grammar, debug=True)

    from assembler import assemble
    prepped = prep(code)
    #print(prepped)
    parsed = l.parse(prepped)
    #print(parsed)

    text = MyTransformer().transform(parsed)

    asm = assemble(text)

    print(asm)
    print(vard)
    return asm
