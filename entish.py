from collections import OrderedDict
import os

# Allows for dot dict access, but is also ordered (but not nested yet)
# Evil hack 1 from
#https://stackoverflow.com/questions/2352181/how-to-use-a-dot-to-access-members-of-dictionary
class OrderedAttributeDict(OrderedDict):
	__getattr__ = dict.__getitem__
	__setattr__ = dict.__setitem__
	__delattr__ = dict.__delitem__

# Allows to create ordered dicts with simple syntax
# Evil hack 2 from
#https://stackoverflow.com/questions/7878933/override-the-notation-so-i-get-an-ordereddict-instead-of-a-dict
class _OrderedDictMaker(object):
	def __getitem__(self, keys):
		if not isinstance(keys, tuple):
			keys = (keys,)
		assert all(isinstance(key, slice) for key in keys)

		return OrderedAttributeDict([(k.start, k.stop) for k in keys])

odict = _OrderedDictMaker()

# Pretty prints a dictionary
def pretty(d, indent=0):
	for key, value in d.items():
		print('\t' * indent + str(key), end="")
		if isinstance(value, dict):
			pretty(value, indent+1)
		elif isinstance(value, list):
			print("")
			for v in value:
				if isinstance(v, dict):
					pretty(v, indent+1)
				else:
					print("\t" * (indent+1) + str(v)	)
		else:
			print('\t' * (indent+1) + str(value))

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
	"gas": 0,
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
			program.code[program.index] = step(instr)
	elif instr == "GAS":
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
