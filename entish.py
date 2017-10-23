class AD(dict):
	__getattr__ = dict.__getitem__
	__setattr__ = dict.__setitem__
	__delattr__ = dict.__delitem__

child = {
	"active": -1,
	"steps": 10,
	"stack": [],
	"index": 0,
	"memory": ["PUSH1", "ADD", "JUMP"],
	"children": []
}

program = {
	"active": 0,
	"steps": 5,
	"stack": [],
	"index": 0,
	"memory": [],
	"children": [AD(child)]
}

def pretty(d, indent=0):
	for key, value in d.items():
		print('\t' * indent + str(key), end="")
		if isinstance(value, dict):
			pretty(value, indent+1)
		elif isinstance(value, list) and all([isinstance(v, dict) for v in value]):
			print("")
			for v in value:
				pretty(v, indent+1)
		else:
			print('\t' * (indent+1) + str(value))

def step(program):

	parent = None
	current = program
	while current.active >= 0:
		parent = current
		current = current.children[current.active]

	def finalize():
		parent = None
		current = program
		current.steps -= 1
		if current.steps == 0:
			print("Out of gas. Exiting main loop.")
			return program, False#exit(1)
		while current.active >= 0:
			parent = current
			current = current.children[current.active]
			current.steps -= 1
			if current.steps == 0:
				parent.active = -1

		return program, True

	if current.index >= len(current.memory):
		print("Invalid memory address, ascending.")
		return finalize()

	instr = current.memory[current.index]
	current.index += 1

	if instr == "PUSH1":
		current.stack.append(1)
	elif instr == "POP":
		if len(current.stack) > 0:
			current.stack.pop()
	elif instr == "ADD":
		if len(current.stack) > 1:
			top = current.stack.pop()
			current.stack[-1] += top
	elif instr == "JUMP":
		current.index = 0

	if current.steps == 0:
		print("Out of Gas, ascending.")
		return finalize()

	return finalize()

program = AD(program)
pretty(program)
iterations = 0
while True:
	program, run = step(program)
	iterations += 1
	print("ITER %i\n" % iterations)
	pretty(program)
	if not run:
		break
