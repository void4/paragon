from bitarray import bitarray
from pprint import PrettyPrinter
from copy import deepcopy
from time import sleep

from asm import read, write, ldict, IL, bits2int, bl, OACTIVE, ODEPTH, OGAS, OTOTALGAS, OIC, OLENCODE, OCODE

def nasm(s):
	code = bitarray()
	code.frombytes(s.encode("ascii"))
	return code

#read vs write types
code = nasm("""nop
jump 0""")

subprocess = ldict(*[-1, 1, 0, 0, 0, code, bitarray()])

code = nasm("""nop
gas 0 100
active 0
jump 0""")
binary = write(ldict(*[-1, 0, 200, 0, 0, code, write(subprocess)]))

#child mirror or in memory?
#mirror would require extra instructions, but would make outsourcing easier
#don't need these instructions!
#program should not be able to externalize costs (memory management etc.) without incurring gas costs

def isint(n):
	try:
		int(n)
		return True
	except ValueError:
		return False

# binary, offset, value
def wb(b, o, v):
	b[o:o+IL] = bl(v)

# binary, offset
def rb(b, o):
	return bits2int(b[o:o+IL])

def step(binary):
	state = read(binary)
	
	parent = None
	current = state
	offset = 0
	parentoffset = None
	while current["active"] != -1:
		parent = current
		parentoffset = offset
		offset += current["active"]+OCODE+len(current["code"])+IL
		current = read(binary[offset:])
	
	print("OFFSET %i" % offset)
	if current["gas"] == 0:
		if parent is None:
			print("Exiting main, out of gas")
			exit(0)
		else:
			print("Out of gas, returning to parent")
			wb(binary, parentoffset+OACTIVE, -1)
			return binary

	code = current["code"].tobytes().decode("ascii").split("\n")
	
	try:
		instr = code[current["ic"]]
	except IndexError:
		if parent is None:
			print("Exiting main, no instruction")
			exit(0)
		else:
			wb(binary, parentoffset+OACTIVE, -1)
			print("No instructions, returning to parent")
			#give parent some form of notice?
			return binary
	
	instra = instr.split()
	print("INSTR:", instr)
	if instr == "nop":
		pass
	elif instra[0]=="jump":
		wb(binary, offset+OIC, int(instra[1])-1)
	elif instra[0]=="gas":
		wb(binary, offset+OGAS, rb(binary, OGAS)-int(instra[2]))#check for underflow
		childoffset = IL+OCODE+len(current["code"])+int(instra[1])
		wb(binary, childoffset+OGAS, rb(binary, childoffset+OGAS)+int(instra[2]))
	elif instra[0]=="active":
		wb(binary, offset+OACTIVE, int(instra[1]))
	else:
		print("Unknown instruction")
		#should not exit here, because subprocess could crash parent
		
	
	wb(binary, offset+OIC, rb(binary, offset+OIC)+1)
	wb(binary, offset+OGAS, rb(binary, offset+OGAS)-1)
	wb(binary, offset+OTOTALGAS, rb(binary, offset+OTOTALGAS)+1)
	return binary

import os
while True:
	binary = step(binary)
	os.system("clear")
	print(binary)
	
	#state = read(binary)
	#state["state"] = read(state["state"])
	#PrettyPrinter(depth=3).pprint(state)
	#print("\n"*2)
	sleep(0.1)
