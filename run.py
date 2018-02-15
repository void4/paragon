
code = """

return 0
while:
    if $arealen($memorylen-1) == 1:
        return $read($memorylen-1, 0)+1


"""

code = """

def f(x):
    return x+1

yield 0
while:
    yield f<50,50>($read($memorylen-1, 0))

"""

from parser import parse
state = parse(code)
#print(list(code))
from exalloc import run, annotated, d, s, STATUS, MEMORY, VOLRETURN

print(len(state), "words")
# Append an argument
state = d(state)
state[MEMORY].append([])
state = s(state)

# Run state
while True:
    state = run(state, 10000, 10000, debug=False)
    if state[STATUS] == VOLRETURN:
        state = d(state)
        #if state[MEMORY][0][0] == 1:
        if len(state[MEMORY]) > 1:
            print("Returned: ", state[MEMORY][-1])
            state[MEMORY] = state[MEMORY][:-1]
        inp = input("Ready>")
        if len(inp):
            state[MEMORY].append([int(inp)])
        else:
            state = s(state)
            break
        state = s(state)
#print(d(state))

print(annotated(d(state)))

from PIL import Image

SIZE = 32
SCALE = 8
img = Image.new("RGB", (SIZE,SIZE))
for i,v in enumerate(state):
    img.putpixel((int(i%SIZE), int(i/SIZE)), int(v%256)<<20)
img = img.resize((SIZE*SCALE, SIZE*SCALE))
#img.show()
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
