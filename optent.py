import os

#only bit32?

I_PUSH, I_POP, I_DUP, I_READ, I_WRITE, I_JUMP, I_ADD, I_ALLOC, I_GAS, I_RUN, I_HALT = range(11)
E_FROZEN, E_NORMAL, E_SUBCOMP, E_VOLHALT, E_OUTOFGAS, E_OUTOFMEM = range(6)
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
		newcode.append(instr)
	return newcode
#print(code)

S_STATUS, S_INDEX, S_GAS, S_MEM, S_CODE, S_STACK, S_MEMORY = range(7)

def pretty(program, depth=0):
	for i in range(S_MEMORY):
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
	return [
		E_FROZEN,
		index,
		gas,
		mem,
		transform(code),
		stack,
		memory
	]

program = inject(outer, stack=[], memory=[inject(code, gas=100, mem=100)])#WHY THE HELL DO I NEED STACK=[] here?!

def step(program):
	#program[S_STATUS] = E_NORMAL

	if program[S_GAS] == 0:
		program[S_STATUS] = E_OUTOFGAS
		return program

	program[S_GAS] -= 1

	instr = program[S_CODE][program[S_INDEX]]
	print("\nINSTR", instr if not isinstance(instr, dict) else ">")
	if instr[0] == I_PUSH:
		value = instr[1]
		if program[S_MEM] > 0:
			program[S_MEM] -= 1
			program[S_INDEX] += 1
			program[S_STACK].append(value)
		else:
			program[S_STATUS] = E_OUTOFMEM
	elif instr[0] == I_POP:
		if len(program[S_STACK]) > 0:
			program[S_STACK].pop()
			program[S_MEM] += 1
		program[S_INDEX] += 1
	elif instr[0] == I_ADD:
		if len(program[S_STACK]) >= 2:
			top = program[S_STACK].pop()
			program[S_STACK][-1] = (program[S_STACK][-1]+top)%2**256
			program[S_MEM] += 1
		program[S_INDEX] += 1
	elif instr[0] == I_DUP:
		if program[S_MEM] == 0:
			program[S_STATUS] = E_OUTOFMEM
		else:
			program[S_STACK].append(program[S_STACK][-1])
			program[S_MEM] -= 1
			program[S_INDEX] += 1
	elif instr[0] == I_WRITE:
		if len(program[S_STACK]) < 2:
			pass
		else:
			addr = program[S_STACK][-2]

			if addr >= len(program[S_MEMORY]):
				pass#???
			else:
				program[S_MEMORY][addr] = program[S_STACK][-1]
		program[S_INDEX] += 1
	elif instr[0] == I_READ:
		if len(program[S_STACK]) < 2:
			program[S_INDEX] += 1
		else:
			addr = program[S_STACK][-1]
			if addr >= len(program[S_MEMORY]):
				program[S_INDEX] += 1
			else:
				if program[S_MEM] == 0:
					program[S_STATUS] = E_OUTOFMEM
				else:
					program[S_MEM] -= 1
					program[S_STACK].append(program[S_MEMORY][addr])
					program[S_INDEX] += 1

	elif instr[0] == I_JUMP:
		if len(program[S_STACK]) > 0:
			target = program[S_STACK][-1]
			program[S_STACK].pop()
			program[S_MEM] += 1
		else:
			target = 0
		program[S_INDEX] = target
	elif instr[0] == I_HALT:
		program[S_STATUS] = E_VOLHALT
		#program[S_GAS] = 0
		program[S_INDEX] += 1
	elif instr[0] == I_GAS:#not deterministic?#used gas instead?
		if program[S_MEM] == 0:
			program[S_STATUS] = E_OUTOFMEM
		else:
			program[S_STACK].append(program[S_GAS])
			program[S_MEM] -= 1
			program[S_INDEX] += 1
	elif instr[0] == I_ALLOC:
		if len(program[S_STACK]) < 1:
			program[S_INDEX] += 1
		else:
			alloc = program[S_STACK].pop()
			program[S_MEM] += 1
			if program[S_MEM] < alloc:
				program[S_STATUS] = E_OUTOFMEM
			else:
				program[S_MEM] -= alloc
				program[S_MEMORY] += [0 for i in range(alloc)]#can only alloc 1 byte at a time?
				program[S_INDEX] += 1
	elif instr[0] == I_RUN:#Call it RECURSE/CALL/COMPUTE?#move this further to the top
		if len(program[S_STACK]) < 1:
			# No address
			program[S_INDEX] += 1
		else:
			#print(subcomp)
			#print(program[S_MEMORY][subcomp])

			#print("SUBCOMP STATUS", status)

			if program[S_STATUS] == E_SUBCOMP:
				if len(program[S_STACK])<1:
					program[S_INDEX] += 1
				else:
					subcomp = program[S_STACK][-1]
					status = program[S_MEMORY][subcomp][S_STATUS]
					print(status)
					if status in [E_FROZEN, E_NORMAL]:
							# add indirection penalty?
							print("Recursing")
							#program[S_CODE][program[S_INDEX]] = statestep(instr)#have to deserialize here too
							#print("STACK", program[S_STACK])
							program[S_MEMORY][subcomp] = step(program[S_MEMORY][subcomp])
							#print("STACK", program[S_STACK])
					else:#good to have state field at index 0
						# Subcomp has halted
						print("HALT", program[S_INDEX])
						program[S_STACK].pop()#Pop subcomp address#still have to check here, grandparent could have modified...
						program[S_MEM] += 1
						program[S_INDEX] += 1
						program[S_STATUS] = E_NORMAL
			else:
				program[S_STATUS] = E_SUBCOMP

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
			pretty(program)
			input()
			os.system("clear")
		if program[S_STATUS] > E_SUBCOMP:#program["gas"] == 0 or
			break

	pretty(program)
	print("Exiting main (%s)." % STATUS[program[S_STATUS]])
	diff = time()-start
	if not stats:
		print("%.6f s\t%i it\t%i it/s" % (diff, iterations, iterations/diff))
	return program
#input()
run(program, 50000, 100, stats=False)
