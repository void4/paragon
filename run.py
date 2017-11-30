

code = """
a = 0

while a!=2000:
    a = a + 1

"""

from parser import parse
asm = parse(code)
#print(list(code))
from exalloc import run
run(asm, 100, 100)
"""
#print("".join([hex(v)[2:].zfill(16) for v in inject(asm)]))
def conv(array):
    return sum([[int(i) for i in element.to_bytes(4, byteorder="big", signed=False)] for element in array], [])

byte = conv(asm)
#print(byte)
import zlib
bytearr = bytearray(byte)
compressed = zlib.compress(bytearr)
print("Uncompressed:", len(bytearr), "Compressed:", len(compressed))

import hashlib
hsh = hashlib.sha224(bytearr).hexdigest()


hex_string = "".join("%02x" % b for b in compressed)
print(hex_string, len(hex_string))
print(hsh)
"""
