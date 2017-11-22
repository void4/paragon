import os

#only bit32?

I_PUSH, I_POP, I_DUP, I_READ, I_WRITE, I_JUMP, I_ADD, I_ALLOC, I_GAS, I_RUN, I_HALT = range(11)
INSTRUCTIONS = ["push", "pop", "dup", "read", "write", "jump", "add", "alloc", "gas", "run", "halt"]
E_FROZEN, E_NORMAL, E_VOLHALT, E_OUTOFGAS, E_OUTOFMEM, E_OUTOFBOUNDS = range(6)
STATUS = ["Frozen", "Normal", "VoluntaryHalt", "OutOfGas", "OutOfMemory", "OutOfBounds"]

code = """
PUSH 1
DUP
DUP
ADD
PUSH 1
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
		else:
			instr.append(0)
		newcode.append(instr)
	newcode = sum(newcode, [])
	return newcode
#print(code)

WORDLEN = 256
CODELEN = 2
S_STATUS, S_INDEX, S_GAS, S_MEM, S_CODE, S_STACK, S_MEMORY, S_END = range(8)
indices = ["Status", "Index", "Gas", "Mem", "PCode", "PStack", "PMemory", "PEnd"]
def pretty(program, depth=0):
	print(("\t"*depth)+indices[S_STATUS]+"\t"+str(program[S_STATUS])+"\t"+STATUS[program[S_STATUS]])
	for i in range(1, S_END+1):
		print(("\t"*depth)+indices[i]+"\t"+str(program[i]))
	print(("\t"*depth)+"Code\t"+" ".join(map(str, program[program[S_CODE]:program[S_STACK]])))
	print(("\t"*depth)+"Stack\t"+" ".join(map(str, program[program[S_STACK]:program[S_MEMORY]])))
	isrun = program[program[S_CODE]+CODELEN*program[S_INDEX]]==I_RUN
	print(isrun)
	if isrun:
		#program[program[S_MEMORY]+program[program[S_MEMORY]-1]+S_STATUS] == E_NORMAL#unfrozen
		subcomp = program[program[S_MEMORY]-1]
		binarylen = program[program[S_MEMORY]+subcomp+S_END]
		substart = program[S_MEMORY]+subcomp
		subend = program[S_MEMORY]+subcomp+binarylen
		pre = program[program[S_MEMORY]:substart]
		binary = program[substart:subend]
		post = program[subend:]
		print(("\t"*depth)+"Pre\t"+" ".join(map(str, pre)))
		pretty(binary, depth+1)
		print(("\t"*depth)+"Post\t"+" ".join(map(str, post)))
	else:
		print(("\t"*depth)+"Memory\t"+" ".join(map(str, program[program[S_MEMORY]:])))

HEADERLEN = 8


def step(program):
	#program[S_STATUS] = E_NORMAL

	if program[S_GAS] == 0:
		program[S_STATUS] = E_OUTOFGAS
		return program

	program[S_GAS] -= 1

	ip = program[S_INDEX]
	instrpos = program[S_CODE]+CODELEN*ip
	#print(instrpos, program[instrpos])
	if program[S_MEMORY] <= instrpos < S_CODE:
		program[S_STATUS] = E_OUTOFBOUNDS
		return program
	instr = [program[instrpos], program[instrpos+1]]
	print(INSTRUCTIONS[instr[0]], instr[1])

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
			return False
		else:
			value = program[program[S_MEMORY]-1]
			program = program[:program[S_MEMORY]-1]+program[program[S_MEMORY]:]
			program[S_MEMORY] -= 1
			program[S_END] -= 1
			program[S_MEM] += 1
			return value

	def next():
		nonlocal program
		program[S_INDEX] += 1

	#print("\nINSTR", instr if not isinstance(instr, dict) else ">")
	if instr[0] == I_PUSH:
		value = instr[1]
		if push(value):
			next()
	elif instr[0] == I_POP:
		pop()
		next()
	elif instr[0] == I_ADD:
		if stacklen() >= 2:
			top1 = pop()
			top2 = pop()
			push((top1+top2)%2**WORDLEN)
		next()
	elif instr[0] == I_DUP:
		if push(top()):
			next()
	elif instr[0] == I_WRITE:
		if stacklen() >= 2:
			addr = pop()
			value = pop()
			if addr >= memorylength():
				pass#???
			else:
				program[S_MEMORY+addr] = program[S_MEMORY-1]
		next()
	elif instr[0] == I_READ:
		if stacklen() < 1:
			next()
		else:
			addr = pop()
			if addr >= memorylength():
				next()
			else:
				if push(program[S_MEMORY+addr]):
					next()

	elif instr[0] == I_JUMP:
		target = pop()
		if target is not None:
			program[S_INDEX] = target
	elif instr[0] == I_HALT:
		program[S_STATUS] = E_VOLHALT
		#program[S_GAS] = 0
		next()
	elif instr[0] == I_ALLOC:
		if stacklen() < 1:
			next()
		else:
			alloc = pop()
			if program[S_MEM] < alloc:
				program[S_STATUS] = E_OUTOFMEM
			else:
				program[S_MEM] -= alloc
				program += [0 for i in range(alloc)]#can only alloc 1 byte at a time?
				program[S_END] += alloc
				next()
	elif instr[0] == I_RUN:#Call it RECURSE/CALL/COMPUTE?#move this further to the top
		if stacklen() < 1:
			# No address
			next()
		else:
			subcomp = top()
			status = program[program[S_MEMORY]+subcomp+S_STATUS]
			#remove this?
			if status == E_FROZEN:
				# Initialize subcomputation
				print("init")
				program[program[S_MEMORY]+subcomp+S_STATUS] = E_NORMAL
				program[program[S_MEMORY]+subcomp+S_MEM] = min(program[S_MEM], program[program[S_MEMORY]+subcomp+S_MEM])

			#print(status)
			#have to reread status
			if program[program[S_MEMORY]+subcomp+S_STATUS] == E_NORMAL:
				# add indirection penalty?
				print("Recursing")
				binarylen = program[program[S_MEMORY]+subcomp+S_END]
				substart = program[S_MEMORY]+subcomp
				subend = program[S_MEMORY]+subcomp+binarylen
				pre = program[:substart]
				binary = program[substart:subend]
				post = program[subend:]
				print("PRELEN", binarylen)
				newbinary = step(binary)
				print("POSTLEN", len(newbinary))
				program = pre+newbinary+post
				program[S_END] += len(newbinary)-binarylen
				#adjust S_MEM here for parent as well?
				#print("STACK", program[S_STACK])
			else:#good to have state field at index 0
				# Subcomp has halted
				print("HALT", status)
				pop()#Pop subcomp address#still have to check here, grandparent could have modified...
				next()
				#!!!
				#program[program[S_MEMORY]+subcomp+S_STATUS] = E_FROZEN#ignore this? (no additional memory write necessary)

	else:
		print("Invalid instruction", instr)
		#print(program[S_INDEX])
		#print(program)

	return program

from time import time, sleep
def run(program, gas, mem=0, stats=False):
	#print(program)
	start = time()
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
			pretty(program)
			input()
			os.system("clear")
		if program[S_STATUS] > E_NORMAL:#program["gas"] == 0 or
			break

	pretty(program)
	print("Exiting main (%s)." % STATUS[program[S_STATUS]])
	diff = time()-start
	if not stats:
		print("%.6f s\t%i it\t%i it/s" % (diff, iterations, iterations/diff))
	return program
#input()

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
		*stack,#move stack to end?
		*memory
	]

program = inject(outer, stack=[], memory=inject(code, gas=100, mem=10))#WHY THE HELL DO I NEED STACK=[] here?!


run(program, 100, 20, stats=True)
