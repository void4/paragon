
# a = a + #valid?!
code = """

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
import os
from hashlib import sha256
class Key:
    def __init__(self, depth):
        self.private = os.urandom(32)
        self.depth = depth
    def __next__(self):
        if self.depth == 0:
            raise Exception("Last key!")
        key = self.private
        for i in range(self.depth):
            key = sha256(key).digest()

        self.depth -= 1
        return key

key = Key(10)
for i in range(key.depth):
    print(next(key))
print(key.private)

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
        state[MEMORY].append(inp)#.append(int(inp))#
    else:
        pass#inp = []

    state = s(state)
