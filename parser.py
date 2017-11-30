from lark import Lark, Transformer
from exalloc import inject

grammar = r"""

NAME: /[a-zA-Z_]\w*/
COMMENT: /#[^\n]*/
_NEWLINE: ( /\r?\n[\t ]*/ | COMMENT)+

_DEDENT: "<DEDENT>"
_INDENT: "<INDENT>"

%import common.ESCAPED_STRING
string: ESCAPED_STRING
?number: DEC_NUMBER
DEC_NUMBER: /[1-9]\d*l?/i

%ignore /[\t \f]+/  // Whitespace

start: (_NEWLINE | stmt)*


?stmt: simple_stmt | compound_stmt
?simple_stmt: (expr_stmt | flow_stmt) _NEWLINE
?expr_stmt: NAME "=" (test | expr) -> assign
          | test

?flow_stmt: return_stmt
return_stmt: "return" (test | NAME)

?test: or_test
?or_test: and_test ("or" and_test)*
?and_test: not_test ("and" not_test)*
?not_test: "not" not_test -> not
| comparison
?comparison: expr comp_op expr
?comp_op: "=="

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

?compound_stmt: if_stmt | funcdef
if_stmt: "if" test ":" suite ["else" ":" suite]
suite: _NEWLINE _INDENT _NEWLINE? stmt+ _DEDENT _NEWLINE?

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
            return "\n".join(out)

        def suite(self, node):
            return sum(node, [])

        def if_stmt(self, node):
            print("ifstmt", node)
            out = []
            out += node[0]
            label = genlabel()
            out.append("PUSH %s" % label)
            out.append("JZ")
            out += node[1]
            out.append(label+":")
            return out


        def comparison(self, node):
            out = []
            print("==", node)
            out += varint(node[0])
            out += varint(node[2])
            out.append("SUB")
            #out.append("NOT")
            print(out)
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


    prepped = prep(code)
    print(prepped)
    parsed = l.parse(prepped)
    print(parsed)

    t = MyTransformer().transform(parsed)
    print(t)

    from assembler import assemble
    asm = assemble(t)
    print(asm)
    return inject(asm)
