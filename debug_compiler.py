import apfelstrudelCompiler

def format_instruction(bit_string):
    """Makes an operation more readable for the human eye"""
    lengths = [8, 8, 4, 4]
    parts = []
    start = 0
    for length in lengths:
        parts.append(bit_string[start:start+length])
        start += length
    return parts

# read contents from assembly code
with open("./apfelstrudel.apf", "r") as asm_file:
    asm_lines = [part.replace("\n", "") for part in asm_file.readlines()]

# compile every single line from assembly code
for line in asm_lines:
    translated_line = apfelstrudelCompiler.translate(line)
    print(format_instruction(translated_line))
    