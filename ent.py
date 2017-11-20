import os

from utils import odict, pretty

#only bit32?

code = """
ALLOC 2
GAS
WRITE 0
READ 0
GAS
ADD
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
	elif instr.startswith("ALLOC "):
		alloc = int(instr.split(" ")[1])
		if program.mem < alloc:
			program.status = OUTOFMEM
		else:
			program.mem -= alloc
			program.memory += [0 for i in range(alloc)]#can only alloc 1 byte at a time?
			program.index += 1
	elif instr.startswith("WRITE"):
		skip = False
		if " " in instr:
			addr = int(instr.split(" ")[1])
		else:
			if len(program.stack) < 2:
				skip = True
			else:
				addr = program.stack[-1]

		if not skip:
			if addr >= len(program.memory):
				pass#???
			else:
				program.memory[addr] = program.stack[-1]
		program.index += 1
	elif instr.startswith("READ"):
		skip = False
		if " " in instr:
			addr = int(instr.split(" ")[1])
		else:
			if len(program.stack) < 2:
				skip = True
				program.index += 1
			else:
				addr = program.stack[-1]
		if not skip:
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
		split = instr.split(" ")
		if len(split) == 2:
			target = int(split[1])
		else:
			target = 0
		program.index = target
	else:
		print("Invalid instruction", instr)

	return program



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
		input()
		os.system("clear")
		if program["gas"] == 0 or program["status"] > 0:
			break

	pretty(program)
	print("Exiting main (%s)." % STATUS[program.status])
	return program

run(program, 40, 10)
