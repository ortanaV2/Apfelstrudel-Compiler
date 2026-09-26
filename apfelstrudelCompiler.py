opcode = {
    "SET":"00000000", # define variable
    "LOAD":"00000001", # load variable from memory
    "MOVE":"00000010", # copy variable to another register
    "ADD":"00000011", # add A & B
    "SUB":"00000100", # subract A & B
    "MUL":"00000101", # multiply A & B
    "DIV":"00000110", # divide A & B
    "AND":"00000111", # A & B
    "OR":"00001000", # A || B
    "XOR":"00001001", # A ^ B
    "NOT":"00001010", # not A
    "CMP":"00001011", # compare A & B and set flags
    "JUMP":"00001100", # jump to line
    "BEQ":"00001101", # jump to line if equal
    "BNE":"00001110", # jump to line if not equal
    "BGT":"00001111", # jump to line if greater than
    "BLT":"00010000", # jump to line if lower than
    "NOP":"00010001", # no operation, ignore
    "HALT":"00010010", # stop execution
    "RET":"00010011" # return to initial jump statement where originated
}

register = {
    "GP0":"0000",
    "GP1":"0001",
    "GP2":"0010",
    "GP3":"0011",
    "GP4":"0100",
    "GP5":"0101",
    "IN0":"0110",
    "IN1":"0111"
}

class UnknownOperator(Exception): pass
class ArgumentError(Exception): pass

def translate(asm_line: str) -> str:
    asm_parts = asm_line.replace(",", "").split(" ")
    operator = asm_parts[0]
    try:
        if operator in ["ADD", "SUB", "MUL", "DIV", "AND", "OR", "XOR", "NOT"]:
            return f"{opcode[operator]}000000000000{register[asm_parts[1]]}"
        elif operator in ["SET", "LOAD"]:
            return f"{opcode[operator]}{int(asm_parts[1]):08b}0000{register[asm_parts[2]]}"
        elif operator == "MOVE":
            return f"{opcode[operator]}00000000{register[asm_parts[1]]}{register[asm_parts[2]]}"
        elif operator in ["CMP", "NOP", "HALT", "RET"]:
            return f"{opcode[operator]}0000000000000000"
        elif operator in ["JUMP", "BEQ", "BNE", "BGT", "BLT"]:
            return f"{opcode[operator]}{int(asm_parts[1]):016b}"
        else:
            raise UnknownOperator(f"{operator}")
    except UnknownOperator: 
        raise
    except Exception:
        raise ArgumentError(f"Line: '{asm_line}' has faulty arguments.")