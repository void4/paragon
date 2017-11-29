STATUS, GAS, MEM, IP, CODE, STACK, MEMORY = range(7)

NORMAL, FROZEN, HALT, OOG, OOC, OOS, OOM, OOB, UOC = range(9)

HALT, RUN, JUMP, PUSH, STACKLEN, MEMORYLEN, AREALEN, READ, WRITE, AREA, ALLOC, DEALLOC = range(12)

REQS = [
    # Name, Instruction length, Required Stack Size, Stack effect
    ["HALT",1,0,0],
    ["RUN",1,1,0],
    ["JUMP",1,1,-1],
    ["PUSH",2,0,1],
    ["STACKLEN",1,0,1],
    ["MEMORYLEN",1,0,1],
    ["AREALEN",1,1,0],
    ["READ",1,2,-1],
    ["WRITE",1,3,-3],
    ["AREA",1,0,1],
    #["DEAREA",1,1,0],#!use after free!
    ["ALLOC",1,2,-2],
    ["DEALLOC",1,2,-2]
]

def s(state):
    """Flattens and serializes the nested state structure"""
    flat = state[:CODE]
    flat += [len(state[CODE])]
    flat += state[CODE]
    flat += [len(state[STACK])]
    flat += state[STACK]
    flat += [len(state[MEMORY])]
    for area in state[MEMORY]:
        flat += [len(area)]
        flat += area
    return flat

def d(state):
    """Deserializes and restores the runtime state structure from the flat version"""
    index = CODE
    sharp = state[:index]
    end = index + state[index] + 1
    sharp.append(state[index+1:end])
    index = end
    end = index + state[index] + 1
    sharp.append(state[index+1:end])
    index = end
    sharp.append([])
    index += 1
    for area in range(state[index-1]):
        end = index + state[index] + 1
        sharp[-1].append(state[index+1:end])
        index = end
    return sharp

def step(state):
    """Stateless step function. Maps states to states."""

    state = d(state)

    # Halt if out of gas
    if state[GAS] == 0:
        state[STATUS] = OOG
        return state
    state[GAS] -= 1

    # Check if current instruction pointer is within code bounds
    ip = state[IP]
    if ip >= len(state[CODE]):
        state[STATUS] = OOC
        return s(state)

    instr = state[CODE][ip]

    reqs = REQS[instr.split()[0]]

    # Check if extended instructions are within code bounds
    if ip + reqs[1] >= len(state[CODE]):
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

    # The following functions should have no or one side effect. If one, either
    # 1. Set a STATE flag and return False, True otherwise
    # 2. Have a side effect and be called _last_
    # This is to ensure failing instructions can be continued normally

    def next(jump=None):
        """Increments the instruction pointer"""
        nonlocal state
        if reqs[3] < 0:
            state[STACK] = state[STACK][:-reqs[3]]
            state[MEM] += abs(reqs[3])

        if jump is None:
            state[IP] += reqs[1]
        else:
            state[IP] = jump

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
        state[STATUS] = HALT
        next()
    elif instr == RUN:
        area, gas, mem = stack[-3:]
        if validarea(area):
            child = state[MEMORY][area]
            # Is this even required? nope.
            if child[STATUS] == FROZEN:
                child[STATUS] = NORMAL
                child[GAS] = gas
                child[MEM] = mem

            if child[STATUS] == NORMAL:
                state[MEMORY][area] = step(state[MEMORY][area])
            else:
                next()
        else:
            next()
    elif instr == JUMP:
        next(top())
    elif instr[:4] == PUSH:
        state[STACK].append(instr.split()[1])
        next()
    elif instr == STACKLEN:
        if push(len(state[STACK])):
            next()
    elif instr == MEMORYLEN:
        if push(len(state[MEMORY])):
            next()
    elif instr == AREALEN:
        area = stack[-1]
        if validarea(area):
            if push(len(state[MEMORY][area])):
                next()
    elif instr == READ:
        area, addr = stack[-2:]
        if validmemory(area, addr):
            if push(state[MEMORY][area][addr]):
                stack = stack[:-2]
                next()
    elif instr == WRITE:
        area, addr, value = stack[-3:]
        if validmemory(area, addr):
            state[MEMORY][area][addr] = value
            stack = stack[:-3]
            next()
    elif instr == AREA:
        # This should cost 1 mem
        if hasmem(1):
            state[MEMORY].append()
            state[MEM] -= 1
            next()
    elif instr == ALLOC:
        area, size = stack[-2:]
        # Technically, -2
        if hasmem(size):
            if validarea(area):
                state[MEM] -= size
                state[MEMORY][area] += [0] * size
                next()
    elif instr == DEALLOC:
        area, size = stack[-2:]
        if validarea(area):
            if len(state[MEMORY][area]) <= size:
                state[MEM] += size
                state[MEMORY][area] = state[MEMORY][area][:-size]
                next()
            else:
                state[STATUS] = OOB
    else:
        state[STATUS] = UOC

    return s(state)

state = s([0, 100, 100, 0, [], [], [
    s([0, 100, 100, 0, [], [], []])]
])
print(state)
while True:
    if state[0] > NORMAL:
        break
    state = step(state)
    print(state)
