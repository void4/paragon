
# a = a + #valid?!
code = """
a = 4
$return
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

code = """
while:
    def f():
        x = 1
        $return

    x = 42
    f(x)
"""

code = """
while:
    x = 1

"""

# TODO ADD HASHMAP/TRIE to PROGRAM REPRESENTATION

from parser import parse
state = parse(code)
#print(list(code))
from exalloc import run, d, s, MEMORY

# Append an argument
state = d(state)
state[MEMORY].append([0])
state = s(state)

# Run state
print(d(run(state, 15, 100, debug=False)))
"""
import sys, select
import os
from time import sleep
clear = lambda : os.system('tput reset')
while False:
    state = run(state, 0xffffffff, 100)
    state = d(state)
    clear()
    i, o, e = select.select( [sys.stdin], [], [], 0)
    print(state)
    if i:
        inp = [int(sys.stdin.readline().strip())]
        state[MEMORY].append(inp)#.append(int(inp))#

    state = s(state)
    sleep(0.1)
"""
