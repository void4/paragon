import os

#only bit32?

I_PUSH, I_POP, I_DUP, I_READ, I_WRITE, I_JUMP, I_ADD, I_ALLOC, I_GAS, I_RUN, I_HALT = range(11)
E_FROZEN, E_NORMAL, E_SUBCOMP, E_VOLHALT, E_OUTOFGAS, E_OUTOFMEM, E_OUTOFBOUNDS = range(7)
STATUS = ["Frozen", "Normal", "SubComp", "VoluntaryHalt", "OutOfGas", "OutOfMemory"]

code = """
PUSH 40
DUP
DUP
ADD
PUSH 0
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
S_STATUS, S_INDEX, S_GAS, S_MEM, S_POSCODE, S_POSSTACK, S_POSMEMORY, S_POSEND = range(8)

def pretty(program, depth=0):
	for i in range(S_POSMEMORY):
		print(("\t"*depth)+str(program[i]))
	for m in program[S_MEMORY]:
		if isinstance(m, list):
			if len(m) > 0:
				pretty(m, depth=depth+1)
			else:
				print(("\t"*depth)+str([]))
		else:
			print(("\t"*depth)+str(m))

def inject(code, index=0, gas=0, mem=0, stack=[], memory=[]):
	code = transform(code)
	return [
		E_FROZEN,
		index,
		gas,
		mem,
		S_POSCODE,#check accesses at runtime (S_CODE <= pos <= S_CODE+len(code))
		S_POSCODE+len(code),
		S_POSCODE+len(code)+len(stack),
		S_POSCODE+len(code)+len(stack)+len(memory),
		*code,
		*stack,#move stack to end?
		*memory
	]

program = inject(outer, stack=[], memory=inject(code, gas=100, mem=100))#WHY THE HELL DO I NEED STACK=[] here?!

def step(program):
	#program[S_STATUS] = E_NORMAL

	if program[S_GAS] == 0:
		program[S_STATUS] = E_OUTOFGAS
		return program

	program[S_GAS] -= 1

	ip = program[S_INDEX]
	instrpos = S_POSCODE+CODELEN*ip
	if program[S_POSMEMORY] <= instrpos < S_POSCODE:
		program[S_STATUS] = E_OUTOFBOUNDS
		return program
	instr = [program[instrpos], program[instrpos+1]]

	def push(value):
		nonlocal program
		if program[S_MEM] > 0:
			program = program[:program[S_POSMEMORY]]+[value]+program[program[S_POSMEMORY]:]
			program[S_POSMEMORY] += 1
			program[S_POSEND] += 1
			program[S_MEM] -= 1
			return True
		else:
			program[S_STATUS] = E_OUTOFMEM
			return False

	def stacklen():
		nonlocal program
		return program[S_POSMEMORY] - program[S_POSSTACK]

	def memorylen():
		nonlocal program
		return program[S_POSEND] - program[S_POSMEMORY]

	def top():
		nonlocal program
		if stacklen() > 0:
			return None
		else:
			return program[program[S_POSMEMORY]-1]

	def pop():
		nonlocal program
		if stacklength() > 0:
			return False
		else:
			value = program[program[S_POSMEMORY]-1]
			program = program[:program[S_POSMEMORY]-1]+program[program[S_POSMEMORY]:]
			program[S_POSMEMORY] -= 1
			program[S_POSEND] -= 1
			program[S_MEM] += 1
			return value

	#print("\nINSTR", instr if not isinstance(instr, dict) else ">")
	if instr[0] == I_PUSH:
		value = instr[1]
		if push(value):
			program[S_INDEX] += 1
	elif instr[0] == I_POP:
		pop()
		program[S_INDEX] += 1
	elif instr[0] == I_ADD:
		if stacklen() >= 2:
			top1 = pop()
			top2 = pop()
			push((top1+top2)%2**WORDLEN)
		program[S_INDEX] += 1
	elif instr[0] == I_DUP:
		if push(top()):
			program[S_INDEX] += 1
	elif instr[0] == I_WRITE:
		if stacklen() >= 2:
			addr = pop()
			value = pop()
			if addr >= memorylength():
				pass#???
			else:
				program[S_POSMEMORY+addr] = program[S_POSMEMORY-1]
		program[S_INDEX] += 1
	elif instr[0] == I_READ:
		if stacklen() < 1:
			program[S_INDEX] += 1
		else:
			addr = pop()
			if addr >= memorylength():
				program[S_INDEX] += 1
			else:
				if push(program[S_POSMEMORY+addr]):
					program[S_INDEX] += 1

	elif instr[0] == I_JUMP:
		target = pop()
		if target is not None:
			program[S_INDEX] = target
	elif instr[0] == I_HALT:
		program[S_STATUS] = E_VOLHALT
		#program[S_GAS] = 0
		program[S_INDEX] += 1
	elif instr[0] == I_ALLOC:
		if stacklen() < 1:
			program[S_INDEX] += 1
		else:
			alloc = pop()
			if program[S_MEM] < alloc:
				program[S_STATUS] = E_OUTOFMEM
			else:
				program[S_MEM] -= alloc
				program += [0 for i in range(alloc)]#can only alloc 1 byte at a time?
				program[S_POSEND] += alloc
				program[S_INDEX] += 1
	elif instr[0] == I_RUN:#Call it RECURSE/CALL/COMPUTE?#move this further to the top
		if stacklen() < 1:
			# No address
			program[S_INDEX] += 1
		else:
			if program[S_STATUS] == E_SUBCOMP:
				subcomp = top()
				status = program[S_POSMEMORY+subcomp+S_STATUS]
				print(status)
				if status in [E_FROZEN, E_NORMAL]:
						# add indirection penalty?
						print("Recursing")
						binarylen = program[program[S_POSMEMORY]+subcomp+S_POSEND]
						binary = program[program[S_POSMEMORY]+subcomp:program[S_POSMEMORY]+subcomp+binarylen]
						print("PRELEN", binarylen, len(binary))#should be the same
						newbinary = step(binary)
						print("POSTLEN", len(newbinary))
						program = program[:program[S_POSMEMORY]+subcomp]+newbinary+program[program[S_POSMEMORY]+subcomp+binarylen]#have to adjust
						program[S_POSEND] += len(newbinary)-binarylen
						#adjust S_MEM here for parent as well?
						#print("STACK", program[S_STACK])
				else:#good to have state field at index 0
					# Subcomp has halted
					print("HALT", program[S_INDEX])
					pop()#Pop subcomp address#still have to check here, grandparent could have modified...
					program[S_INDEX] += 1
					program[S_STATUS] = E_NORMAL
					program[program[S_POSMEMORY]+subcomp+S_STATUS] = E_FROZEN#ignore this? (no additional memory write necessary)
			else:
				# Initialize subcomputation
				program[S_STATUS] = E_SUBCOMP
				subcomp = top()
				program[program[S_POSMEMORY]+subcomp+S_STATUS]= E_NORMAL
				program[program[S_POSMEMORY]+subcomp+S_MEM] = min(program[S_MEM], program[program[S_POSMEMORY]+subcomp+S_MEM])

	else:
		print("Invalid instruction", instr)
		#print(program[S_INDEX])
		#print(program)

	return program

from time import time, sleep
def run(program, gas, mem=0, stats=False):
	print(program)
	start = time()
	program[S_GAS] = gas
	program[S_MEM] = mem
	iterations = 0
	#os.system("clear")
	while True:
		if stats:
			print("ITER %i\n" % iterations)
		iterations += 1
		print(iterations)
		program = step(program)

		if stats:
			#pretty(program)
			print(program)
			input()
			os.system("clear")
		if program[S_STATUS] > E_SUBCOMP:#program["gas"] == 0 or
			break

	print(program)
	print("Exiting main (%s)." % STATUS[program[S_STATUS]])
	diff = time()-start
	if not stats:
		print("%.6f s\t%i it\t%i it/s" % (diff, iterations, iterations/diff))
	return program
#input()
run(program, 50000, 100, stats=False)
