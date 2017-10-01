from bitarray import bitarray
import inspect

#could have just serialized the json...

class dotdict(dict):
	"""dot.notation access to dictionary attributes"""
	__getattr__ = dict.get
	__setattr__ = dict.__setitem__
	__delattr__ = dict.__delitem__

#only works with multiple of 4 bits
IL = 32
def bl(i, l=IL):
	return bitarray(("{:0%ib}" % l).format(i&int("0x"+("f"*(l//4)), 16)))

HEADER = "exe\0".encode("ascii")#"paragon\0".encode("ascii")
HEADERLEN = len(HEADER)*8

# Converts nested list to nested dotdicts
def ldict(active, depth, gas, totalgas, ic, code, state):#, children):
	frame = inspect.currentframe()
	args, _, _, values = inspect.getargvalues(frame)
	d = {i : values[i] for i in args}
	return dotdict(d)

OROOT, OACTIVE, ODEPTH, OGAS, OTOTALGAS, OIC, OLENCODE, OCODE = range(0, 32*8, 32)
def write(current):
	global OACTIVE, ODEPTH, OGAS, OTOTALGAS, OIC, OLENCODE, OCODE
	b = bitarray()
	b.frombytes(HEADER)#0
	b += bl(current.active)#32
	b += bl(current.depth)#64
	b += bl(current.gas)#96
	b += bl(current.totalgas)#128
	b += bl(current.ic)#160
	b += bl(len(current.code))#192
	b += current.code#224
	b += bl(len(current.state))#224+lencode
	b += current.state#256+lencode
	return b

def bits2int(bits):
	if not bits[0]:
		return int(bits.to01(), 2)
	else:
		return -int((~bits).to01(), 2)-1

#variable size encoding?
#would make runtime optimisation harder
def read(binary):

	temp = binary.copy()
	def rb(l):
		nonlocal temp
		bits = temp[:l]
		temp = temp[l:]
		return bits
	
	def lb(l=IL):
		bits = rb(l)
		return bits2int(bits)

	header = rb(HEADERLEN).tobytes()
	if header != HEADER:
		print("Invalid header", header)
		exit(1)
		return
	
	active = lb()
	depth = lb()
	gas = lb()
	totalgas = lb()
	ic = lb()
	lencode = lb()
	code = rb(lencode)
	lenstate = lb()
	state = rb(lenstate)
	return ldict(active, depth, gas, totalgas, ic, code, state)#, children)

def test():
	current = [-1, 0, 1000, 0, 0, bitarray("1"), bitarray(), [[-1, 0, 1000, 0, 0, bitarray("1"), bitarray()]]]
	current = ldict(*current)
	print("Dict representation:")
	print(current)
	print("\nConverting dict to binary representation...")
	binary = write(current)
	print("Writing binary representation to file...")
	with open("paragon.bit", "wb+") as f:
		binary.tofile(f)
	
	print("Reading binary representation from file...")
	binary2 = bitarray()
	with open("paragon.bit", "rb+") as f:
		binary2.fromfile(f)#this is bytewise!
	
	print("\nBinary representation:")
	print(binary2)
	
	print("\nConverting binary to dict representation...")
	rbinary = read(binary2)
	#print("\nDict representation:")
	#print(rbinary)
	print("Converting dict to binary representation again...")
	binary3 = write(rbinary)
	print(len(binary), len(binary2), len(binary3))
	print(binary==binary3)


if __name__ == "__main__":
	test()

