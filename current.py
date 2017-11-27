import os

I_PUSH, I_POP, I_DUP, I_READ, I_WRITE, I_JUMP, I_ADD, I_ALLOC, I_GAS, I_RUN, I_HALT = range(11)
INSTRUCTIONS = ["push", "pop", "dup", "read", "write", "jump", "add", "alloc", "gas", "run", "halt"]
E_FROZEN, E_NORMAL, E_VOLHALT, E_OUTOFGAS, E_OUTOFMEM, E_OUTOFBOUNDS = range(6)
STATUS = ["Frozen", "Normal", "VoluntaryHalt", "OutOfGas", "OutOfMemory", "OutOfBounds"]

WORDLEN = 256
S_STATUS, S_INDEX, S_GAS, S_MEM, S_CODE, S_STACK, S_MEMORY, S_END = range(8)
indices = ["Status", "Index", "Gas", "Mem", "PCode", "PStack", "PMemory", "PEnd"]

HEADERLEN = 8

def step(program):

	if program[S_GAS] == 0:
		program[S_STATUS] = E_OUTOFGAS
		return program

	program[S_GAS] -= 1

	ip = program[S_INDEX]
	instrpos = program[S_CODE]+ip

	#Make this check generic (instruction_length)
	if program[S_MEMORY] <= instrpos < S_CODE or (program[instrpos]==I_PUSH and (program[S_MEMORY] <= instrpos+1 < S_CODE)):
		program[S_STATUS] = E_OUTOFBOUNDS
		return program

	instr = program[instrpos]

	def push(value):
		nonlocal program
		if program[S_MEM] > 0:
			program = program[:program[S_MEMORY]]+[value]+program[program[S_MEMORY]:]
			program[S_MEMORY] += 1
			program[S_END] += 1
			program[S_MEM] -= 1
			return True
		else:
			program[S_STATUS] = E_OUTOFMEM
			return False

	def proglen():
		nonlocal program
		return program[S_END]

	def stacklen():
		nonlocal program
		return program[S_MEMORY] - program[S_STACK]

	def memorylen():
		nonlocal program
		return program[S_END] - program[S_MEMORY]

	def top():
		nonlocal program
		if stacklen() == 0:
			return None
		else:
			return program[program[S_MEMORY]-1]

	def pop():
		nonlocal program
		if stacklen() == 0:
			return None
		else:
			value = program[program[S_MEMORY]-1]
			program = program[:program[S_MEMORY]-1]+program[program[S_MEMORY]:]
			program[S_MEMORY] -= 1
			program[S_END] -= 1
			program[S_MEM] += 1
			return value

	def next(steps=1):
		nonlocal program
		program[S_INDEX] += steps

	def alloc(size):
		nonlocal program
		if program[S_MEM] < size:
			program[S_STATUS] = E_OUTOFMEM
			return None
		else:
			program[S_MEM] -= size
			program += [0 for i in range(size)]#can only alloc 1 byte at a time?
			program[S_END] += size
			return len(program)-program[S_MEMORY]-size

	def dealloc(size):
		nonlocal program
		if memorylen() >= size:
			return None#hmmmm. could just set size=memorylen()-1
		else:
			program[S_MEM] += size
			program = program[:len(program)-size]
			program[S_END] -= size
			return size

	def read(address):
		nonlocal program
		if address >= proglen():
			return None
		else:
			return program[address]

	def readmem(address):
		return read(program[S_MEMORY]+address)

	def write(address, value):
		nonlocal program
		if address >= proglen():
			return None
		else:
			program[address] = value

	def writemem(address, value):
		return write(program[S_MEMORY]+address, value)

	# Return pointer to result/number of successful writes here?
	def copy(source, target, length):
		nonlocal program
		for i in range(length):
			writemem(target+i, readmem(source+i))

	if instr == I_RUN:
		# Recurse into and execute a substate for one step.
		if stacklen() < 1:
			# No address
			next()
		else:
			subcomp = top()
			status = readmem(subcomp+S_STATUS)
			subcompend = readmem(subcomp+S_END)

			if status == E_FROZEN:
				# Initialize subcomputation
				# Check if program is already on end, check for max length here
				if program[S_END] != program[S_MEMORY]+subcomp+subcompend:
					# Otherwise allocate enough memory. Do this first so no side effects twice
					pointer = alloc(subcompend)
					if pointer is not None:
						# Now copy the thing to the end
						copy(subcomp, pointer, subcompend)
						# And update the pointer on the stack
						pop()
						push(pointer)#could fail here if grandparent modifies
						subcomp = pointer
					else:
						print("FAILED TO ALLOCATE")
						return program

				# Limit memory
				writemem(subcomp+S_STATUS, E_NORMAL)
				mingas = min(program[S_MEM], readmem(subcomp+S_MEM))
				writemem(subcomp+S_MEM, mingas)

			if readmem(subcomp+S_STATUS) == E_NORMAL:
				# Add indirection penalty?
				parent = program[:program[S_MEMORY]+subcomp]
				child = program[program[S_MEMORY]+subcomp:]
				child = step(child)

				program = parent + child
				# Adjust parent length
				program[S_END] = len(program)
			else:
				# Subcomp has halted
				# Pop subcomp address
				# Still have to check here, grandparent could have modified...
				pop()
				next()
				writemem(subcomp+S_STATUS, E_FROZEN)#ignore this? (no additional memory write necessary)

	elif instr == I_PUSH:
		value = program[instrpos+1]
		if push(value):
			next(2)
	elif instr == I_POP:
		pop()
		next()
	elif instr == I_ADD:
		if stacklen() >= 2:
			top1 = pop()
			top2 = pop()
			push((top1+top2)%2**WORDLEN)
		next()
	elif instr == I_DUP:
		if push(top()):
			next()
	elif instr == I_WRITE:
		if stacklen() >= 2:
			addr = pop()
			value = pop()
			if addr >= memorylength():
				pass#???
			else:
				program[S_MEMORY+addr] = program[S_MEMORY-1]
		next()
	elif instr == I_READ:
		if stacklen() < 1:
			next()
		else:
			addr = pop()
			if addr >= memorylength():
				next()
			else:
				if push(program[S_MEMORY+addr]):
					next()

	elif instr == I_JUMP:
		target = pop()
		if target is not None:
			program[S_INDEX] = target
	elif instr == I_HALT:
		program[S_STATUS] = E_VOLHALT
		#program[S_GAS] = 0
		next()
	elif instr == I_ALLOC:
		if stacklen() < 1:
			next()
		else:
			size = pop()
			if alloc(size):
				next()
	else:
		print("Invalid instruction", instr)

	return program

from time import time, sleep
def run(program, gas, mem=0, stats=False):
	start = time()
	program[S_STATUS] = E_NORMAL
	program[S_GAS] = gas
	program[S_MEM] = mem
	iterations = 0
	os.system("clear")
	while True:
		if stats:
			print("ITER %i\n" % iterations)
		iterations += 1
		program = step(program)

		if stats:
			hexit = "".join(map(lambda x:hex(x)[2:],program))
			print(hexit)
			print(len(hexit))
			pretty(program)
			input()
			os.system("clear")
		if program[S_STATUS] > E_NORMAL:
			break

	pretty(program)
	print("Exiting main (%s)." % STATUS[program[S_STATUS]])
	diff = time()-start
	if not stats:
		print("%.6f s\t%i it\t%i it/s" % (diff, iterations, iterations/diff))
	return program

def pretty(program, depth=0):
	spacing = "\t"*depth
	print(spacing + "%s\t%i\t%s" % (indices[S_STATUS], program[S_STATUS], STATUS[program[S_STATUS]]))
	index = program[S_CODE] + program[S_INDEX]
	instr = program[index]
	print(spacing + "%s\t%i\t%s" % (indices[S_INDEX], program[S_INDEX], INSTRUCTIONS[instr]))
	for i in range(2, S_END+1):
		print(spacing + "%s\t%i" % (indices[i], program[i]))
	print(spacing + "Code\t"+" ".join(map(str, program[program[S_CODE]:program[S_STACK]])))
	print(spacing + "Stack\t"+" ".join(map(str, program[program[S_STACK]:program[S_MEMORY]])))

	if program[program[S_CODE] + program[S_INDEX]] == I_RUN:
		subcomp = program[program[S_MEMORY]-1]
		pre = program[program[S_MEMORY]:program[S_MEMORY]+subcomp]
		binary = program[program[S_MEMORY]+subcomp:]
		print(spacing + "Memory\t" + " ".join(map(str, pre)))
		print("^")
		pretty(binary, 0)#depth+1)
	else:
		print(spacing + "Memory\t" + " ".join(map(str, program[program[S_MEMORY]:])))


def inject(code, index=0, gas=0, mem=0, stack=[], memory=[]):
	code = transform(code)
	return [
		E_FROZEN,
		index,
		gas,
		mem,
		HEADERLEN,
		HEADERLEN+len(code),
		HEADERLEN+len(code)+len(stack),
		HEADERLEN+len(code)+len(stack)+len(memory),
		*code,
		*stack,
		*memory
	]

code = """
PUSH 1
DUP
DUP
ADD
PUSH 2
JUMP
"""

outer = """
PUSH 0
RUN
PUSH 0
JUMP
"""

def transform(code):
	code = code.strip().split("\n")
	newcode = []
	for instr in code:
		instr = instr.split(" ")
		instr[0] = globals()["I_"+instr[0]]
		if len(instr) == 2:
			instr[1] = int(instr[1])
		newcode.append(instr)
	newcode = sum(newcode, [])
	return newcode

child = inject(code, gas=50, mem=50)
program = inject(outer, memory=child)
print(len(program), len(child))
print(program)
print(child)
run(program, 150, 150, stats=True)
