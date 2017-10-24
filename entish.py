from collections import OrderedDict
import os

class AD(OrderedDict):
	__getattr__ = dict.__getitem__
	__setattr__ = dict.__setitem__
	__delattr__ = dict.__delitem__

def pretty(d, indent=0):
	for key, value in d.items():
		print('\t' * indent + str(key), end="")
		if isinstance(value, dict):
			pretty(value, indent+1)
		elif isinstance(value, list):# and all([isinstance(v, dict) for v in value]):
			print("")
			for v in value:
				if isinstance(v, dict):
					pretty(v, indent+1)
				else:
					print("\t" * (indent+1) + str(v))
		else:
			print('\t' * (indent+1) + str(value))

child = {
	"steps": 0,
	"index": 0,
	"memory": ["ADD", "JUMP"],
}

middle = {
	"steps": 0,
	"index": 0,
	"memory": ["COPY", AD(child), "JUMP"],
}

program = {
	"steps": 20,
	"index": 0,
	"memory": ["COPY", AD(child), "JUMP"],
}


def step(program):
	program.steps -= 1
	instr = program.memory[program.index]
	print("INSTR", instr)
	if isinstance(instr, dict):
		if instr["steps"] == 0:
			program.index += 1
		else:
			program.memory[program.index] = step(instr)
	elif instr == "ADD":
		program.memory.append(program.steps)
		program.index += 1
	elif instr == "JUMP":
		program.index = 0
	elif instr == "COPY":
		nextcell = program.memory[program.index+1]
		if isinstance(nextcell, dict):
			nextcell.steps = min(program.steps, 5)
		program.index += 1
	else:
		print("Invalid instruction", instr)

	return program

program = AD(program)
pretty(program)
iterations = 0
while True:
	program = step(program)
	iterations += 1
	print("ITER %i\n" % iterations)
	pretty(program)
	if program["steps"] == 0:
		print("Exiting main (OutOfGas).")
		break
	input()
	os.system("clear")
