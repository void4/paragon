import os

from utils import odict, pretty

#only bit32?

code = """
GAS
GAS
ADD
JUMP
"""

program = odict[
	"gas": 0,#should this be in parent program?
	"mem": 0,
	"index": 0,
	"status": 0,
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

# Stateless step function
def statestep(program):

	program.status = 0
	program.gas -= 1
	instr = program.code[program.index]
	print("INSTR", instr if not isinstance(instr, dict) else ">")
	if isinstance(instr, dict):
		if instr.gas == 0 or instr.status > 0:
			program.index += 1
		else:
			# add indirection penalty?
			program.code[program.index] = step(instr)
	elif instr.startswith("HALT"):
		program.status = 1#VOLUNTARY HALT
		#program.gas = 0
		program.index += 1
	elif instr == "GAS":#not deterministic?#used gas instead?
		if program.mem == 0:
			program.status = 2
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
	print("Exiting main (%s)." % ["OutOfGas", "VoluntaryHalt", "OutOfMemory"][program.status])
	return program

run(program, 40, 100)
