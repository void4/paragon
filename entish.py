import os

from utils import odict, pretty

code = """
GAS
GAS
ADD
MOD
IFZERO
GAS
JUMP
"""

program = odict[
	"gas": 0,#should this be in parent program?
	"index": 0,
	"code": code.strip().split("\n"),
	"stack": [],
	"memory": [],
]
# Stateless step function
def step(program):

	program.gas -= 1
	instr = program.code[program.index]
	print("INSTR", instr if not isinstance(instr, dict) else ">")
	if isinstance(instr, dict):
		if instr["gas"] == 0:
			program.index += 1
		else:
            # add indirection penalty?
			program.code[program.index] = step(instr)
	elif instr == "GAS":#not deterministic?
		program.memory.append(program.gas)
		program.index += 1
	elif instr == "ADD":
		if len(program.stack) >= 2:
			top = program.stack.pop()
			program.stack[-1] += top
		program.index += 1
	elif instr == "SUB":
		if len(program.stack) >= 2:
			top = program.stack.pop()
			program.stack[-1] -= top
		program.index += 1
	elif instr == "MOD":
		if len(program.stack) >= 2:
			top = program.stack.pop()
			program.stack[-1] %= top
		program.index += 1
	elif instr == "IFZERO":
		split = instr.split(" ")
		if len(split) == 2:
			target = int(split[1])
		else:
			target = 0
		if len(program.stack) > 0 and program.stack.pop() == 0:
			program.index = target
		else:
			program.index += 1
	elif instr == "JUMP":
		split = instr.split(" ")
		if len(split) == 2:
			target = int(split[1])
		else:
			target = 0
		program.index = target
	elif instr.startswith("COPY"):
		split = instr.split(" ")
		if len(split) == 2:
			increase = int(split[1])
		else:
			increase = program.gas
		nextcell = program.code[program.index+1]
		if isinstance(nextcell, dict):
			nextcell.gas = min(program.gas, increase)
		program.index += 1
	else:
		print("Invalid instruction", instr)

	return program



def run(program, gas):

	program.gas = gas
	iterations = 0
	os.system("clear")
	while True:
		print("ITER %i\n" % iterations)
		iterations += 1
		pretty(program)
		program = step(program)
		input()
		os.system("clear")
		if program["gas"] == 0:
			break

	pretty(program)
	print("Exiting main (OutOfGas).")
	return program

run(program, 40)
