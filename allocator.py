from bitarray import bitarray
from struct import pack

STARTMEM = 1024
BLOCKSIZE = 256

m = bitarray("0"*STARTMEM)
print(len(m))

# Ready byte from bit index
def r(i):
	return int(m[i:i+8].to01(), 2)

# Writes byte to bit index
def w(i, v):
	v = pack(">B", v)
	b = bitarray()
	b.frombytes(v)
	m[i:i+8] = b

# Prints memory contents with comments
def p(*args):
	print(*args)
	print(m.to01())
	print("\n")

"""
Block Header
free: bit
next: I7 - just stores relative address/number of occupied blocks
"""

# Initialize first header
w(0,0x7f&(STARTMEM//BLOCKSIZE))

# Zero out full memory? Otherwise no guarantees. Zero on malloc()?

p()

def malloc(size):
	index = 0
	#required number of blocks
	#slight round error here as not every following block has header
	need = (size//BLOCKSIZE)+1
	while True:
		v = r(index)
		free = v>>7 == 0
		blocks = (v&0x7f)
		if free and blocks>=need:
			w(index, 0x80|need)
			if blocks > need:
				w(index+BLOCKSIZE*need, 0x7f&(blocks-need))
			p("MALLOC", size)
			return index+8
		else:
			index += blocks*256
			if index>len(m):
				print("Failed to allocate")
				break

	p("MALLOCFAIL", size)	

def realloc(pointer, size):
	raise NotImplementedError()

def free(pointer, fillzero=True):
	hindex = pointer-8
	header = r(hindex)
	free = header>>7
	if free == 0:
		#Try to merge anyway?
		print("Already free")
		return

	blocks = header&0x7f
	
	# Merge with next block header if that one is free
	nhindex = hindex+BLOCKSIZE*blocks
	nheader = r(nhindex)
	nhfree = nheader>>7 == 0
	totalblocks = blocks
	if nhfree:
		nhblocks = nheader&0x7f
		totalblocks += nhblocks
		print("MERGING")
	
	# Don't have to zero out already free block, only header
	if fillzero:
		for byteindex in range(BLOCKSIZE*blocks):
			w(hindex+byteindex, 0)
		
		if nhfree:
			w(nhindex, 0)
	
	w(hindex, 0x7f&totalblocks)
	p("FREE", pointer, fillzero)
	

from random import randint
def fillrandom(pointer, size):
	for i in range(size//8):
		w(pointer+i*8, randint(0,255))
	p("RANDOM", pointer, size)

reqmem = 255
pointer1 = malloc(reqmem)
print("POINTER: ", pointer1)
fillrandom(pointer1, reqmem)
pointer2 = malloc(reqmem)
fillrandom(pointer2, reqmem)
pointer3 = malloc(reqmem)
fillrandom(pointer3, reqmem)
free(pointer2)
free(pointer1)
