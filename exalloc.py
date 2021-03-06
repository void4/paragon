from hashlib import sha256

BYTESIZE = 32
WORDSIZE = 8*BYTESIZE
WMAX = 2**WORDSIZE
WMASK = WMAX-1

STATUS, GAS, MEM, IP, LENCODE, LENSTACK, LENMAP, LENMEMORY, CODE, STACK, MAP, MEMORY = range(12)

NORMAL, FROZEN, VOLHALT, VOLRETURN, OOG, OOC, OOS, OOM, OOB, UOC = range(10)
STATI = ["NORMAL", "FROZEN", "HALT", "OUTOFGAS", "OUTOFCODE", "OUTOFSTACK", "OUTOFMEMORY", "OUTOFBOUNDS", "UNKNOWNCODE"]

HALT, RETURN, YIELD, RUN, JUMP, JZ, PUSH, POP, DUP, FLIP, KEYSET, KEYGET, KEYDEL, STACKLEN, MEMORYLEN, AREALEN, READ, WRITE, AREA, DEAREA, ALLOC, DEALLOC, ADD, SUB, NOT, MUL, DIV, MOD, SHA256 = range(29)

REQS = [
    # Name, Instruction length, Required Stack Size, Stack effect
    ["HALT",1,0,0],
    ["RETURN",1,0,0],
    ["YIELD",1,0,0],
    ["RUN",1,3,-3],
    ["JUMP",1,1,-1],
    ["JZ",1,2,-2],
    ["PUSH",2,0,1],
    ["POP",1,0,0],
    ["DUP",1,0,1],
    ["FLIP",1,2,0],

    ["KEYSET",1,2,-2],
    ["KEYGET",1,1,0],
    ["KEYDEL",1,1,-1],
    ["STACKLEN",1,0,1],
    ["MEMORYLEN",1,0,1],
    ["AREALEN",1,1,0],
    ["READ",1,2,-1],
    ["WRITE",1,3,-3],
    ["AREA",1,0,1],
    ["DEAREA",1,1,-1],#!use after free!
    ["ALLOC",1,2,-2],
    ["DEALLOC",1,2,-2],
    ["ADD",1,2,-1],
    ["SUB",1,2,-1],
    ["NOT",1,1,0],
    ["MUL",1,2,-1],
    ["DIV",1,2,-1],
    ["MOD",1,2,-1],
    ["SHA256",1,1,0],
]

def s(state):
    """Flattens and serializes the nested state structure"""
    flat = state[:LENCODE]
    flat += [len(state[CODE])]
    flat += [len(state[STACK])]
    flat += [len(state[MAP]) * 2]
    flat += [len(state[MEMORY])]
    flat += state[CODE]
    flat += state[STACK]
    for k,v in state[MAP]:
        flat += [k, v]
    for area in state[MEMORY]:
        flat += [len(area)]
        flat += area
    return flat

def d(state):
    """Deserializes and restores the runtime state structure from the flat version"""
    sharp = state[:LENMEMORY+1]
    lencode = state[LENCODE]
    lenstack = state[LENSTACK]
    lenmap = state[LENMAP]
    lenmemory = state[LENMEMORY]

    sharp.append(state[LENMEMORY+1:LENMEMORY+1+lencode])
    sharp.append(state[LENMEMORY+1+lencode:LENMEMORY+1+lencode+lenstack])
    hmap = state[LENMEMORY+1+lencode+lenstack:LENMEMORY+1+lencode+lenstack+lenmap]
    hmap = list(zip(hmap[::2], hmap[1::2]))
    sharp.append(hmap)

    sharp.append([])
    #print(lencode, lenstack, lenmemory)
    index = LENMEMORY+1+lencode+lenstack+lenmap
    for area in range(lenmemory):
        lenarea = state[index]
        sharp[-1].append(state[index+1:index+1+lenarea])
        index = index + 1 + lenarea
    return sharp

from utils import odict

def annotated(d):
    return odict[
        "header": d[:LENMEMORY+1],
        "code": d[LENMEMORY+1],
        "stack": d[LENMEMORY+2],
        "map": d[LENMEMORY+3],
        "memory": d[LENMEMORY+4],
    ]

def step(state):
    """Stateless step function. Maps states to states."""

    state = d(state)

    # Halt if out of gas
    if state[GAS] == 0:
        state[STATUS] = OOG
        return s(state)
    state[GAS] -= 1

    # Check if current instruction pointer is within code bounds
    ip = state[IP]
    if ip >= len(state[CODE]):
        state[STATUS] = OOC
        return s(state)

    instr = state[CODE][ip]
    reqs = REQS[instr]
    """
    print("")
    print(reqs[0])
    #print(instr, ip)
    print(state[STACK])
    print(state[MEMORY])
    #print(state[MAP])
    """

    #print(state[:-1])
    #for area in state[-1]:
    #    print(">",area)
    # Check if extended instructions are within code bounds
    if ip + reqs[1] - 1 >= len(state[CODE]):
        state[STATUS] = OOC
        return s(state)

    # Check whether stack has sufficient items for current instruction
    if len(state[STACK]) < reqs[2]:
        state[STATUS] = OOS
        return s(state)

    # Check if current instruction has enough memory for stack effects
    if state[MEM] < reqs[3]:
        state[STATUS] = OOM
        return s(state)

    def next(jump=None):
        """Pops arguments. Sets the instruction pointer"""
        nonlocal state

        if reqs[3] < 0:
            state[STACK] = state[STACK][:reqs[3]]
            state[MEM] += abs(reqs[3])

        if jump is None:
            state[IP] += reqs[1]
        else:
            state[IP] = jump

    # The following functions should have no or one side effect. If one, either
    # 1. Set a STATE flag and return False, True otherwise
    # 2. Have a side effect and be called _last_
    # This is to ensure failing instructions can be continued normally


    def top():
        """Returns the top of the stack"""
        if len(state[STACK]) == 0:
            return None
        else:
            return state[STACK][-1]

    def push(value):
        """Pushes a value onto the stack"""
        if state[MEM] == 0:
            state[STATUS] = OOM
            return False
        else:
            state[STACK].append(value)
            state[MEM] -= 1
            return True

    def validarea(area):
        """Checks if this memory area index exists"""
        nonlocal state
        if area >= len(state[MEMORY]):
            state[STATUS] = OOB
            return False
        else:
            return True

    def validmemory(area, addr):
        """Checks if the memory address and area exist"""
        nonlocal state
        if not validarea(area) or addr >= len(state[MEMORY][area]):
            state[STATUS] = OOB
            return False
        else:
            return True

    def hasmem(mem):
        """Checks if state has enough mem, sets flag otherwise"""
        nonlocal state
        if mem <= state[MEM]:
            return True
        else:
            state[STATUS] = OOM
            return False

    if instr == HALT:
        state[STATUS] = VOLHALT
        next()
    elif instr == RETURN:
        state[STATUS] = VOLRETURN
        state[IP] = 0
    elif instr == YIELD:
        state[STATUS] = VOLRETURN
        next()
    elif instr == RUN:
        area, gas, mem = state[STACK][-3:]
        if validarea(area) and len(state[MEMORY][area]) > 4:#HEADERLEN
            child = state[MEMORY][area]
            # Is this even required? nope.
            if child[STATUS] == FROZEN:
                child[STATUS] = NORMAL
                child[GAS] = gas
                child[MEM] = mem

            if child[STATUS] == NORMAL:
                #print(">>>")
                state[MEMORY][area] = step(state[MEMORY][area])
                #print("<<<")
            else:
                child[STATUS] = FROZEN
                next()
        else:
            next()
    elif instr == JUMP:
        next(top())
    elif instr == JZ:
        if state[STACK][-2] == 0:
            next(top())
        else:
            next()
    elif instr == PUSH:
        state[STACK].append(state[CODE][ip+1])
        next()
    elif instr == POP:
        if len(state[STACK]) > 0:
            state[STACK] = state[STACK][:-1]
            state[MEM] += 1
            next()
    elif instr == DUP:
        state[STACK].append(top())
        next()
    elif instr == FLIP:
        state[STACK][-2:] = state[STACK][:-3:-1]
        next()
    elif instr == KEYSET:

        if hasmem(2):
            kv = (state[STACK][-2], state[STACK][-1])
            for i, (k,v) in enumerate(state[MAP]):
                if k == state[STACK][-2]:
                    state[MAP][i] = kv
                    state[MEM] -= 2
                    break
            else:
                state[MAP].append(kv)
            next()
    elif instr == KEYGET:
        for i, (k,v) in enumerate(state[MAP]):
            if k == state[STACK][-1]:
                state[STACK][-1] = v
        next()
    elif instr == KEYDEL:
        newmap = []
        for i, (k,v) in enumerate(state[MAP]):
            if k != state[STACK][-1]:
                newmap.append((k,v))
                state[MEM] += 2
        state[MAP] = newmap
        next()
    elif instr == STACKLEN:
        if push(len(state[STACK])):
            next()
    elif instr == MEMORYLEN:
        if push(len(state[MEMORY])):
            next()
    elif instr == AREALEN:
        area = state[STACK][-1]
        if validarea(area):
            state[STACK][-1] = len(state[MEMORY][area])
            next()
    elif instr == READ:
        area, addr = state[STACK][-2:]
        if validmemory(area, addr):
            state[STACK][-2] = state[MEMORY][area][addr]
            next()
    elif instr == WRITE:
        area, addr, value = state[STACK][-3:]
        if validmemory(area, addr):
            state[MEMORY][area][addr] = value
            next()
    elif instr == AREA:
        # This should cost 1 mem
        if hasmem(1):
            state[MEMORY].append([])
            state[MEM] -= 1
            next()
    elif instr == DEAREA:
        state[MEM] += len(state[MEMORY][top()])
        state[MEMORY].pop(top())
        next()
    elif instr == ALLOC:
        area, size = state[STACK][-2:]
        # Technically, -2
        if hasmem(size):
            if validarea(area):
                state[MEM] -= size
                state[MEMORY][area] += [0] * size
                next()
    elif instr == DEALLOC:
        area, size = state[STACK][-2:]
        if validarea(area):
            if len(state[MEMORY][area]) >= size:
                state[MEM] += size
                state[MEMORY][area] = state[MEMORY][area][:-size]
                next()
            else:
                state[STATUS] = OOB
    elif instr == ADD:
        op1, op2 = state[STACK][-2:]
        state[STACK][-2] = op1 + op2
        next()
    elif instr == SUB:
        op1, op2 = state[STACK][-2:]
        state[STACK][-2] = (op1 - op2) % WMAX
        next()
    elif instr == NOT:
        state[STACK][-1] = ~state[STACK][-1] & WMASK
        next()
    elif instr == MUL:
        op1, op2 = state[STACK][-2:]
        state[STACK][-2] = (op1 * op2) % WMAX
        next()
    elif instr == DIV:
        op1, op2 = state[STACK][-2:]
        state[STACK][-2] = op1 // op2
        next()
    elif instr == MOD:
        op1, op2 = state[STACK][-2:]
        state[STACK][-2] = op1 % op2
        next()
    elif instr == SHA256:
        bytearr = state[STACK][-1].to_bytes(BYTESIZE, byteorder="big", signed=False)
        digest = sha256(bytearr)
        #print(bytearr)
        #print(digest.hexdigest())
        state[STACK][-1] = int.from_bytes(digest.digest(), byteorder="big", signed=False)
        next()
    else:
        state[STATUS] = UOC

    return s(state)

from time import sleep

def run(state, gas=100, mem=100, debug=False):
    state[STATUS] = NORMAL
    state[GAS] = gas
    state[MEM] = mem
    while True:
        if state[STATUS] > NORMAL:
            if debug:
                dstate = d(state)
                #print(STATI[dstate[STATUS]], dstate[GAS], dstate[MEM])
                print(dstate)
            break
        state = step(state)
        if debug:
            out = d(state)
            #print(out[STACK], out[MEMORY])
            #sleep(0.1)
    return state

def inject(code):
    return s([FROZEN, 0, 0, 0, code, [], []])
