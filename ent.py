import os

from utils import odict, pretty

#only bit32?

code = """
PUSH 10
ALLOC
GAS
WRITE
READ
GAS
ADD
PUSH 2
JUMP
"""

program = odict[
	"status": 0,
	"gas": 0,#should this be in parent program?
	"mem": 0,
	"index": 0,
	"code": code.strip().split("\n"),
	"stack": [],
	"memory": [],
]

def deserialize(binary):
	program = binary
	return program

def serialize(program):
	binary = program
	return binary

def step(binary):
	program = deserialize(binary)
	program = statestep(program)
	return serialize(binary)

NORMAL, VOLHALT, OUTOFGAS, OUTOFMEM = range(4)
STATUS = ["Normal", "VoluntaryHalt", "OutOfGas", "OutOfMemory"]

# Stateless step function
def statestep(program):

	program.status = 0

	if program.gas == 0:
		program.status = OUTOFGAS
		return program

	program.gas -= 1

	instr = program.code[program.index]
	print("INSTR", instr if not isinstance(instr, dict) else ">")
	if isinstance(instr, dict):
		if instr.gas == 0 or instr.status > 0:#hm do this, otherwise recursion?
			program.index += 1
		else:
			# add indirection penalty?
			program.code[program.index] = step(instr)
	elif instr.startswith("HALT"):
		program.status = VOLHALT
		#program.gas = 0
		program.index += 1
	elif instr == "GAS":#not deterministic?#used gas instead?
		if program.mem == 0:
			program.status = OUTOFMEM
		else:
			program.stack.append(program.gas)
			program.mem -= 1
			program.index += 1
	elif instr == "ADD":
		if len(program.stack) >= 2:
			top = program.stack.pop()
			program.stack[-1] += top
			program.mem += 1
		program.index += 1
	elif instr == "ALLOC":
		if len(program.stack) < 1:
			program.index += 1
		else:
			alloc = program.stack[-1]
			if program.mem < alloc:
				program.status = OUTOFMEM
			else:
				program.mem -= alloc
				program.memory += [0 for i in range(alloc)]#can only alloc 1 byte at a time?
				program.index += 1
	elif instr.startswith("PUSH "):
		value = int(instr.split(" ")[1])
		if program.mem > 0:
			program.mem -= 1
			program.index += 1
			program.stack.append(value)
		else:
			program.status = OUTOFMEM
	elif instr == "POP":
		if len(program.stack) > 0:
			program.stack.pop()
			program.mem += 1
		program.index += 1
	elif instr == "WRITE":
		if len(program.stack) < 2:
			pass
		else:
			addr = program.stack[-2]

			if addr >= len(program.memory):
				pass#???
			else:
				program.memory[addr] = program.stack[-1]
		program.index += 1
	elif instr == "READ":
		if len(program.stack) < 2:
			program.index += 1
		else:
			addr = program.stack[-1]
			if addr >= len(program.memory):
				program.index += 1
			else:
				if program.mem == 0:
					program.status = OUTOFMEM
				else:
					program.mem -= 1
					program.stack.append(program.memory[addr])
					program.index += 1

	elif instr == "JUMP":
		if len(program.stack) > 0:
			target = program.stack[-1]
			program.stack.pop()
			program.mem += 1
		else:
			target = 0
		program.index = target
	else:
		print("Invalid instruction", instr)

	return program


from time import sleep
def run(program, gas, mem=0):

	program.gas = gas
	program.mem = mem
	iterations = 0
	os.system("clear")
	while True:
		print("ITER %i\n" % iterations)
		iterations += 1
		pretty(program)
		program = step(program)
		#input()
		sleep(0.1)
		os.system("clear")
		if program["status"] > 0:#program["gas"] == 0 or 
			break

	pretty(program)
	print("Exiting main (%s)." % STATUS[program.status])
	return program

run(program, 100, 100)
