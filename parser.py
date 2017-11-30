from lark import Lark, Transformer

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
?simple_stmt: (expr_stmt | flow_stmt) _NEWLINE
?expr_stmt: NAME "=" (test | expr) -> assign
          | test

?flow_stmt: return_stmt | halt_stmt
?halt_stmt: "halt"
return_stmt: "return" (test | NAME)

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
     | NAME | number | ESCAPED_STRING


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

while_stmt: "while" test ":" suite

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
            out += sum(node, [])
            return out

        def suite(self, node):
            return sum(node, [])

        def if_stmt(self, node):
            #print("ifstmt", node)
            out = []
            out += node[0]
            else_label = genlabel()
            end_label = genlabel()
            out.append("PUSH %s" % else_label)
            out.append("JZ")
            out += node[1]
            out.append("PUSH %s" % end_label)
            out.append("JUMP")
            out.append(else_label+":")
            out += node[2]
            out.append(end_label+":")
            return out

        def while_stmt(self, node):
            print("while", node)
            out = []
            start_label = genlabel()
            end_label = genlabel()

            out.append(start_label+":")

            out += node[0]

            out.append("NOT")
            out.append("PUSH %s" % end_label)
            out.append("JZ")

            out += node[1]

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

        def halt_stmt(self, node):
            return ["HALT"]

        def assign(self, node):
            nonlocal vard
            #print("=",node)
            target = node[0]

            out = []
            out.append("PUSH %i" % area)
            if isinstance(target, str):
                if target not in vard:
                    out.append("PUSH %i" % area)
                    out.append("PUSH 1")
                    out.append("ALLOC")
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

    text_unopt = "\n".join(text)
    text_opt = optimize(text)
    text_opt = "\n".join(text_opt)
    print(text_opt)
    asm = assemble(text_opt)

    print("Optimized:", len(asm), "Unoptimized:", len(assemble(text_unopt)))
    print(asm)
    return asm

def optimize(text):
    optimized = []
    last = None
    lastpushed = None
    for line in text:

        if line[:4] == "PUSH":
            if line == lastpushed:
                optimized.append("DUP")
            else:
                lastpushed = line
                optimized.append(line)
        elif line == "NOT" and last == "NOT":
            lastpushed = None
            continue
        else:
            lastpushed = None
            optimized.append(line)
        last = line
    return optimized
