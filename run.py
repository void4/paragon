
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
            a = $read($memorylen-1, 0)
        else:
            $dearea($memorylen - 1)
    else:
        a = $sha256(a)

"""

from parser import parse
state = parse(code)
#print(list(code))
from exalloc import run, d, s, MEMORY

while True:
    state = run(state, 0xffffffff, 100)
    state = d(state)
    inp = input()
    #if len(inp):
    if inp:
        inp = [int(inp)]
    else:
        inp = []
    state[MEMORY].append(inp)#.append(int(inp))#
    state = s(state)
