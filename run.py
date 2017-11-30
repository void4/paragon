

code = """
a = 3
b = 3
if a == b:
    a = 1
"""

c2 = """
if a == b:
    a = 3
else:
    a = 5

def test():
    a = 3
    if a == 3:
        a = 4
"""

from parser import parse
asm = parse(code)
#print(list(code))
from exalloc import run
run(asm, 100, 100)

#print("".join([hex(v)[2:].zfill(16) for v in inject(asm)]))
def conv(array):
    return sum([[int(i) for i in element.to_bytes(4, byteorder="big", signed=False)] for element in array], [])

byte = conv(asm)
#print(byte)
import zlib
compressed = zlib.compress(bytearray(byte))
print("Uncompressed:", len(byte), "Compressed:", len(compressed))
