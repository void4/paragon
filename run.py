
# a = a + #valid?!
code = """
before = 0
after = 0
a = 0
while:
    # Remember number of memory areas
    before = $memorylen
    # Halt computation, expect input in new memory area
    halt
    # Check number of areas again
    # If they are different, there's a new one
    # Assuming none were deleted, of course
    if before != $memorylen:
        if $arealen($memorylen-1) != 0:
            pass
            #a = $read($memorylen-1, 0)
        #$dearea $memorylen - 1
    #else:
    #    a = $sha256(a)

"""

from parser import parse
state = parse(code)
#print(list(code))
from exalloc import run, d, s, MEMORY

while True:
    state = run(state, 100, 100)
    state = d(state)
    inp = input()
    if len(inp):
        state[MEMORY].append([int(inp)])#.append(int(inp))#
    state = s(state)

#print("".join([hex(v)[2:].zfill(16) for v in inject(asm)]))

from assembler import assemble
code = """
PUSH 0
SHA256
"""
asm = assemble(code)
#print(asm)
#print(run(asm, 100, 100))
