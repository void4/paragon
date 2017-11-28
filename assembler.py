from current import INSTRUCTIONS as opcodes
import sys

def assemble(text):
    lines = text.split("\n")

    labels = {}
    opcounter = 0

    def intorlabel(arg):
        try:
            return int(arg)
        except:
            return arg

    lines = [{"source":line} for line in lines]
    for line in lines:
        clean = line["source"].strip().lower()
        if ";" in clean:
            clean = clean[:clean.find(";")]

        line["clean"] = clean

        opline = clean.split(" ")
        line["opline"] = opline

        if len(opline) == 1 and opline[0].endswith(":"):
            label = opline[0][:-1]
            line["name"] = label
            labels[label] = {"opc":opcounter}
            ignore = True
            line["type"] = "label"
        elif opline[0] in opcodes:#meh
            opcounter += 1
            ignore = False
            line["type"] = "code"
        elif opline[0]:
            raise Exception("Invalid symbol:", opline[0])
        else:
            line["type"] = "whitespace"
            ignore = True
        line["ignore"] = ignore
        line["opcount"] = opcounter

        if line["ignore"]:
            continue
        op = line["opline"][0]
        if op == "push":
            line["code"] = [0, intorlabel(line["opline"][1])]
        elif op in opcodes:
            line["code"] = [opcodes.index(op)]
        else:
            raise Exception("Unknown opcode %s" % line)

    # Calculate label offsets from expanded code
    offset = 0
    for line in lines:
        line["offset"] = offset
        if line["type"] == "label":
            labels[line["name"]] = offset
        elif line["type"] == "code":
            offset += len(line["code"])

    # Lastly, replace all labels with offsets
    total = []
    for line in lines:
        if line["type"] == "code":
            line["code"] = [labels[exp] if exp in labels else exp for exp in line["code"]]
            total += line["code"]

    for i, line in enumerate(lines):
        if line["type"] == "code":
            print("%i\t%i\t%s\t%s" % (line["opcount"], line["offset"], " ".join(map(str, line["code"])), "\t".join(line["opline"])))
        elif line["type"] == "label":
            print("%i\t%i\t%s" % (line["opcount"], line["offset"], line["name"]))

    #print("".join(map(lambda x:hex(x)[2:].zfill(16), total)))
    print(total)
    return total
#bfile = open("bytecode.js", "w+")
#bfile.write("var code = "+str(code))
#bfile.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("need input file")
        exit()

    inp = sys.argv[1]

    with open(inp, "r") as f:
        text = f.read()
    assemble(text)
