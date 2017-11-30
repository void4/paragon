from assembler import assemble
code = """
PUSH 0
SHA256
PUSH 1
PUSH 1
PUSH 0
PUSH 0
ADD
ADD
"""
asm = assemble(code)
print(asm)
#print(run(asm, 100, 100))
