STATUS, GAS, MEM, IP, CODE, STACK, MEMORY = range(7)

HALT, OOG, OOC, OOS, OOM, OOB, UOC = range(7)

REQS = {
    # Stack-In Effect
    "RUN" : [1,0],
    "HALT" : [0,0],
    "PUSH" : [0,1],
    "READ" : [2,-1]
}

def s(state):
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
    index = CODE
    sharp = state[:index]
    end = index + state[index]
    sharp.append(state[index:end])
    index = end
    end = index + state[index]
    sharp.append(state[index:end])
    index = end
    sharp.append([])
    index += 1
    for area in range(state[index-1]):
        end = index + state[index]
        sharp[-1].append(state[index:end])
        index = end
    return sharp

def step(state):

    state = d(state)

    if state[GAS] == 0:
        state[STATUS] = OOG
        return state
    state[GAS] -= 1

    ip = state[IP]
    if ip >= len(state[CODE]):
        state[STATUS] = OOC
        return s(state)

    instr = state[CODE][ip]

    reqs = REQS[instr.split()[0]]

    if len(state[STACK]) < reqs[0]:
        state[STATUS] = OOS
        return s(state)

    if state[MEM] < reqs[1]:
        state[STATUS] = OOM
        return s(state)

    def next():
        nonlocal state
        state[IP] += 1

    def push(value):
        if state[MEM] == 0:
            state[STATUS] = OOM
            return False
        else:
            state[STACK].append(value)
            return True

    def validarea(area):
        nonlocal state
        if area >= len(state[MEMORY]):
            state[STATUS] = OOB
            return False
        else:
            return True

    def validmemory(area, addr):
        nonlocal state
        if not validarea(area) or addr >= len(state[MEMORY][area]):
            state[STATUS] = OOB
            return False
        else:
            return True

    if instr == "RUN":
        area = stack[-1]
        if validarea(area):
            state[MEMORY][area] = step(state[MEMORY][area])
        else:
            next()

    elif instr == "STACKLEN":
        if push(len(state[STACK])):
            next()
    elif instr == "HALT":
        state[STATUS] = HALT
        next()
    elif instr[:4] == "PUSH":
        state[STACK].append(instr.split()[1])
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

state = s([0, 100, 100, 0, [], [], []])
print(state)
while True:
    if state[0] > 0:
        break
    state = step(state)
    print(state)
