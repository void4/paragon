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

child = odict[
	"steps": 0,
	"index": 0,
	"memory": ["ADD", "JUMP"],
]

middle = odict[
	"steps": 0,
	"index": 0,
	"memory": ["COPY 6", child, "JUMP"],
]

# Stateless step function
def step(program):

	program.steps -= 1
	instr = program.memory[program.index]
	print("INSTR", instr if not isinstance(instr, dict) else ">")
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
	elif instr.startswith("COPY"):
		split = instr.split(" ")
		if len(split) == 2:
			increase = int(split[1])
		else:
			increase = program.steps
		nextcell = program.memory[program.index+1]
		if isinstance(nextcell, dict):
			nextcell.steps = min(program.steps, increase)
		program.index += 1
	else:
		print("Invalid instruction", instr)

	return program



def run(program, steps):
	shell = interpreter = odict[
		"steps": 0,
		"index": 0,
		"memory": ["COPY"],
	]

	shell.steps = steps
	shell.memory.append(program)
	iterations = 0
	os.system("clear")
	while True:
		print("ITER %i\n" % iterations)
		iterations += 1
		pretty(shell)
		shell = step(shell)
		input()
		os.system("clear")
		if shell["steps"] == 0:
			break

	pretty(shell)
	print("Exiting main (OutOfGas).")
	return program

run(middle, 20)
