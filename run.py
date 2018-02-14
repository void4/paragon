
code = """

await

while:
    if NUMARGS == 1:
        lastarea = $memorylen-1
        if $arealen(lastarea) == 1:
            $write(lastarea, 0, $read(lastarea, 0)+1)
    await

"""

from parser import parse
state = parse(code)
#print(list(code))
from exalloc import run, annotated, d, s, STATUS, MEMORY, VOLRETURN

# Append an argument
state = d(state)
#state[MEMORY].append([0])
state = s(state)

# Run state
while True:
    state = run(state, 10000, 10000, debug=True)
    if state[STATUS] == VOLRETURN:
        state = d(state)
        state[MEMORY].append([int(input("Ready>"))])
        state = s(state)
#print(d(state))

print(annotated(d(state)))

from PIL import Image

SIZE = 32
SCALE = 8
img = Image.new("RGB", (SIZE,SIZE), )
for i,v in enumerate(state):
    img.putpixel((int(i%SIZE), int(i/SIZE)), int(v%256))
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
