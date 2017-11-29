STATUS, GAS, MEM, IP, CODE, STACK, MEMORY = range(7)

NORMAL, FROZEN, HALT, OOG, OOC, OOS, OOM, OOB, UOC = range(9)

REQS = {
    # Stack-In Effect
    "RUN" : [1,0],
    "HALT" : [0,0],
    "PUSH" : [0,1],
    "READ" : [2,-1]
}

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
    if ip + reqs[2] >= len(state[CODE]):
        state[STATUS] = OOC
        return s(state)

    # Check whether stack has sufficient items for current instruction
    if len(state[STACK]) < reqs[0]:
        state[STATUS] = OOS
        return s(state)

    # Check if current instruction has enough memory for stack effects
    if state[MEM] < reqs[1]:
        state[STATUS] = OOM
        return s(state)

    def next():
        """Increments the instruction pointer"""
        nonlocal state
        state[IP] += 1

    def push(value):
        """Pushes a value onto the stack"""
        if state[MEM] == 0:
            state[STATUS] = OOM
            return False
        else:
            state[STACK].append(value)
            state[MEM] -= 1
            return True

    def pop():
        """Pops a value from the stack"""
        if len(state[STACK]) == 0:
            return None
        else:
            value = state[STACK].pop()
            state[MEM] += 1
            return value

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

    if instr == "RUN":
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
    elif instr == "HALT":
        state[STATUS] = HALT
        next()
    elif instr == "JUMP":
        state[IP] = pop()
    elif instr[:4] == "PUSH":
        state[STACK].append(instr.split()[1])
        next()
    elif instr == "STACKLEN":
        if push(len(state[STACK])):
            next()
    elif instr == "MEMORYLEN":
        if push(len(state[MEMORY])):
            next()
    elif instr == "AREALEN":
        area = stack[-1]
        if validarea(area):
            if push(len(state[MEMORY][area])):
                stack.pop()
                next()
    elif instr == "READ":
        area, addr = stack[-2:]
        if validmemory(area, addr):
            if push(state[MEMORY][area][addr]):
                stack = stack[:-2]
                next()
    elif instr == "WRITE":
        area, addr, value = stack[-3:]
        if validmemory(area, addr):
            state[MEMORY][area][addr] = value
            stack = stack[:-3]
            next()
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
