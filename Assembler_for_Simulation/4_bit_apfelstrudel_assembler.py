#!/usr/bin/env python3
"""Assembler fuer die 4-bit CPU.

Instruction (14 Bit): [S5..S0 OPCODE][V3..V0][RS1 RS0][RT1 RT0]
S5 (MSB des Opcodes) = 1 bei allen Befehlen, die in ein Register schreiben
(SET, MOVE, ADD, SUB, AND, OR, XOR, NOT, MUL), sonst 0.

Zeilenzaehlung im Assembly: Sprungziele sind 1-basiert (1..16), der Assembler
schreibt die 0-basierte CPU-Adresse (0..15). Leer-/Kommentarzeilen zaehlen nicht.

Verwendung:
    python assembler.py programm.asm            # Ausgabe auf stdout
    python assembler.py programm.asm -o out.txt
    python assembler.py programm.asm --compact  # ohne Leerzeichen zwischen Feldern
    python assembler.py programm.asm --definition  # Format "AAAA=BBBBBBBBBBBBB" pro Zeile
"""
import argparse
import sys

OPCODES = {
    "SET": 31, "MOVE": 30, "ADD": 29, "SUB": 28, "AND": 27, "OR": 26,
    "XOR": 25, "NOT": 24, "MUL": 23, "CMP": 22,
    "BLT": 0, "BGT": 1, "BNE": 2, "BEQ": 3, "JMP": 4, "HALT": 5, "NOP": 6,
}
# Basis-Opcodes oben sind die unteren 5 Bit (S4..S0). S5 wird je nach Befehlsart gesetzt.
WRITES_REG = {"SET", "MOVE", "ADD", "SUB", "AND", "OR", "XOR", "NOT", "MUL"}
S5 = 0b100000
REGS = {"INA": 0, "INB": 1, "GPA": 2, "GPB": 3}
COND_BRANCHES = {"BLT", "BGT", "BNE", "BEQ"}      # benoetigen vorheriges CMP

ALU_OPS = {"ADD", "SUB", "AND", "OR", "XOR", "NOT", "MUL"}
BRANCH_OPS = {"BLT", "BGT", "BNE", "BEQ", "JMP"}


class AsmError(Exception):
    pass


def parse_int(tok, what):
    try:
        return int(tok, 0)
    except ValueError:
        raise AsmError(f"{what} '{tok}' ist keine gueltige Zahl")


def parse_reg(tok):
    r = REGS.get(tok.upper())
    if r is None:
        raise AsmError(f"Unbekanntes Register '{tok}' (erlaubt: INA, INB, GPA, GPB)")
    return r


def check_args(mnemonic, args, n):
    if len(args) != n:
        raise AsmError(f"{mnemonic} erwartet {n} Operand(en), bekam {len(args)}")


def clean(line):
    for c in (";", "#", "//"):
        line = line.split(c)[0]
    return line.strip()


def first_pass(lines):
    """Sammelt Instruktionen und Labels. Leerzeilen/Kommentare zaehlen nicht als Zeile."""
    instrs, labels = [], {}
    for lineno, raw in enumerate(lines, 1):
        line = clean(raw)
        if not line:
            continue
        while ":" in line:  # Label am Zeilenanfang
            label, line = line.split(":", 1)
            label = label.strip()
            if not label or " " in label:
                raise AsmError(f"Zeile {lineno}: ungueltiges Label")
            if label.upper() in labels:
                raise AsmError(f"Zeile {lineno}: Label '{label}' doppelt definiert")
            labels[label.upper()] = len(instrs)
            line = line.strip()
        if line:
            instrs.append((lineno, line))
    return instrs, labels


def encode(mnemonic, args, labels, base):
    m = mnemonic.upper()
    if m not in OPCODES:
        raise AsmError(f"Unbekannter Befehl '{mnemonic}'")
    op, v, rs, rt = OPCODES[m], 0, 0, 0

    if m == "SET":
        check_args(m, args, 2)
        v = parse_int(args[0], "Wert")
        if not 0 <= v <= 15:
            raise AsmError(f"SET-Wert {v} ausserhalb 0..15 (4 Bit)")
        rt = parse_reg(args[1])
    elif m == "MOVE":
        check_args(m, args, 2)
        rs, rt = parse_reg(args[0]), parse_reg(args[1])
    elif m in ALU_OPS:
        check_args(m, args, 1)
        rt = parse_reg(args[0])
        if rt in (0, 1):
            raise AsmError(f"{m}: ALU-Ergebnis darf nicht in INA/INB (Feedback-Loop)")
    elif m in BRANCH_OPS:
        check_args(m, args, 1)
        t = args[0]
        if t.upper() in labels:
            v = labels[t.upper()]              # Label -> bereits 0-basierte CPU-Adresse
        else:
            line_no = parse_int(t, "Sprungziel")   # User-Zaehlung: 1-basiert
            if not 1 <= line_no <= 16:
                raise AsmError(f"Sprungziel {line_no} ausserhalb 1..16 (CPU-Adresse hat nur 4 Bit)")
            v = line_no - 1
        if not 0 <= v <= 15:
            raise AsmError(f"Label zeigt auf Zeile {v + 1} - nur Zeilen 1..16 sind adressierbar")
    elif m in ("CMP", "HALT", "NOP"):
        check_args(m, args, 0)

    if m in WRITES_REG:
        op |= S5
    return op, v, rs, rt


def assemble(source_lines, compact=False):
    instrs, labels = first_pass(source_lines)
    if len(instrs) > 16:
        print(f"WARNUNG: {len(instrs)} Instruktionen, aber Sprungadressen "
              f"erreichen nur Zeilen 1..16.", file=sys.stderr)
    out = []
    seen_cmp = False
    for idx, (lineno, line) in enumerate(instrs):
        parts = line.replace(",", " ").split()
        mn = parts[0].upper()
        if mn == "CMP":
            seen_cmp = True
        elif mn in COND_BRANCHES and not seen_cmp:
            print(f"WARNUNG: Zeile {lineno} ('{line}'): {mn} ohne vorheriges CMP "
                  f"im Quelltext - Flag-Register evtl. undefiniert.", file=sys.stderr)
        try:
            op, v, rs, rt = encode(parts[0], parts[1:], labels, idx)
        except AsmError as e:
            raise AsmError(f"Zeile {lineno} ('{line}'): {e}")
        fields = [f"{op:06b}", f"{v:04b}", f"{rs:02b}", f"{rt:02b}"]
        out.append(("" if compact else " ").join(fields))
    return out


def main():
    ap = argparse.ArgumentParser(description="Assembler fuer die 4-bit CPU")
    ap.add_argument("input")
    ap.add_argument("-o", "--output")
    ap.add_argument("--compact", action="store_true", help="Felder ohne Leerzeichen")
    ap.add_argument("--definition", action="store_true",
                    help="Jede Zeile mit 4-Bit-Zeilenadresse als Prefix, z.B. 0000=1111101010000 "
                         "(erzwingt kompakte Ausgabe)")
    ap.add_argument("--annotate", action="store_true",
                    help="Adresse und Quellzeile als Kommentar anhaengen")
    a = ap.parse_args()

    with open(a.input, encoding="utf-8") as f:
        src = f.read().splitlines()
    try:
        result = assemble(src, a.compact or a.definition)
    except AsmError as e:
        print(f"Fehler: {e}", file=sys.stderr)
        sys.exit(1)

    if a.definition:
        if len(result) > 16:
            print(f"Fehler: {len(result)} Instruktionen, aber die 4-Bit-Zeilenadresse "
                  f"reicht nur fuer 16 (0000..1111).", file=sys.stderr)
            sys.exit(1)
        result = [f"{i:04b}={r}" for i, r in enumerate(result)]

    if a.annotate:
        instrs, _ = first_pass(src)
        result = [f"{r}  ; {i:2d}: {instrs[i][1]}" for i, r in enumerate(result)]

    text = "\n".join(result) + "\n"
    if a.output:
        with open(a.output, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
