#python3.5 compiler.py > out.asm && cat out.asm && python3.5 assembler.py out.asm
import ast


def generate(tree):
    output = ""

    var = {

    }

    mem = 0

    def app(instr):
        nonlocal output
        output += instr+"\n"

    def push(value):
        app("PUSH %s" % value)

    def alloc(size=1):
        nonlocal mem
        push(size)
        app("ALLOC")
        mem += 1
        return mem-1

    def write(address, value):
        push(address)
        push(value)
        app("WRITE")

    def read(address):
        push(address)
        app("READ")

    def varaddr(name):
        if name in var:
            return var[name]
        else:
            raise Exception("UNALLOCATED VAR %s" % name)

    def readvar(name):
        read(varaddr(name))

    labels = 0

    def jump(typ="JUMP"):
        nonlocal labels
        labels += 1
        label = "label%i" % labels
        push(label)
        app(typ)
        return label+":"

    def pushvalue(node):
        if isinstance(node, ast.Name):
            readvar(node.id)
        elif isinstance(node, ast.Num):
            push(node.n)
        elif isinstance(node, ast.BinOp):
            #print(dir(node), node.left, node.op, node.right)
            pushvalue(node.left)
            pushvalue(node.right)
            if isinstance(node.op, ast.Add):
                app("ADD")
            else:
                raise Exception("Unsupported op %s" % node.op)
        else:
            raise Exception("Unknown value %s" % node)

    def recurse(tree):
        for node in tree.body:
            if isinstance(node, ast.Assign):
                name = node.targets[0].id
                if name not in var:
                    pointer = alloc()
                    var[name] = pointer
                push(var[name])
                pushvalue(node.value)
                app("WRITE")
            elif isinstance(node, ast.If):
                test = node.test
                if isinstance(test, ast.Compare):
                    pushvalue(test.left)
                    pushvalue(test.comparators[0])
                    if len(test.ops) == 1:
                        comp = test.ops[0]
                        if isinstance(comp, ast.Eq):
                            app("SUB")
                        else:
                            raise Exception("Unsupported comparator %s" % comp)
                    else:
                        raise Exception("Unsupported number of comparators %s" % test.comparators)
                else:
                    raise Exception("Unsupported test")
                label = jump("JZ")
                recurse(node)

                app(label)
            else:
                print("unknown node", node)
                exit()

    recurse(tree)
    return output

def compiler(code):
    tree = ast.parse(code)
    return generate(tree)

if __name__ == "__main__":
    code = """
a = 1
b = 2
a = b
if a==b:
    a = a + b
    a = 2
"""
    print(compiler(code))
