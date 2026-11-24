#!/usr/bin/env python3
"""
Hack Assembler - Nand2Tetris Capstone, Part B
Usage: python assembler.py Prog.asm      -> writes Prog.hack

Extra feature (K = 17, K mod 3 = 2):
    prints a warning whenever the same label is declared more than once.
"""

import sys
import os

# ---------------------------------------------------------------- tables
JUMP_BITS = {
    "": "000", "JGT": "001", "JEQ": "010", "JGE": "011",
    "JLT": "100", "JNE": "101", "JLE": "110", "JMP": "111",
}

DEST_BITS = {
    "": "000", "M": "001", "D": "010", "MD": "011",
    "A": "100", "AM": "101", "AD": "110", "AMD": "111",
}

# computation field: 'a' bit + six c bits
COMP_BITS = {
    "0": "0101010", "1": "0111111", "-1": "0111010",
    "D": "0001100", "A": "0110000", "!D": "0001101",
    "!A": "0110001", "-D": "0001111", "-A": "0110011",
    "D+1": "0011111", "A+1": "0110111", "D-1": "0001110",
    "A-1": "0110010", "D+A": "0000010", "D-A": "0010011",
    "A-D": "0000111", "D&A": "0000000", "D|A": "0010101",
    "M": "1110000", "!M": "1110001", "-M": "1110011",
    "M+1": "1110111", "M-1": "1110010", "D+M": "1000010",
    "D-M": "1010011", "M-D": "1000111", "D&M": "1000000",
    "D|M": "1010101",
}

# commutative forms the official assembler also accepts
for _alias, _real in {
    "A+D": "D+A", "M+D": "D+M", "A&D": "D&A", "M&D": "D&M",
    "A|D": "D|A", "M|D": "D|M", "1+D": "D+1", "1+A": "A+1", "1+M": "M+1",
}.items():
    COMP_BITS[_alias] = COMP_BITS[_real]


def fresh_symbol_table():
    table = {
        "SP": 0, "LCL": 1, "ARG": 2, "THIS": 3, "THAT": 4,
        "SCREEN": 16384, "KBD": 24576,
    }
    for n in range(16):
        table["R%d" % n] = n
    return table


# ---------------------------------------------------------------- helpers
def strip_line(raw):
    """Remove comments and every kind of whitespace."""
    cut = raw.find("//")
    if cut != -1:
        raw = raw[:cut]
    return "".join(raw.split())


def is_valid_symbol(name):
    if not name or name[0].isdigit():
        return False
    return all(ch.isalnum() or ch in "_.$:" for ch in name)


class AsmError(Exception):
    pass


# ---------------------------------------------------------------- pass 1
def collect_labels(source_lines, symbols, warnings):
    """
    Walk through the file once, drop comments/blank lines and record
    the ROM address of each (LABEL).
    Returns a list of (line_number, cleaned_text) for real instructions.
    """
    program = []
    first_seen = {}          # label -> line number of first declaration
    rom_addr = 0

    for line_no, raw in enumerate(source_lines, start=1):
        text = strip_line(raw)
        if not text:
            continue

        if text.startswith("("):
            if not text.endswith(")") or len(text) < 3:
                raise AsmError("Line %d: invalid label '%s'" % (line_no, text))
            name = text[1:-1]
            if not is_valid_symbol(name):
                raise AsmError("Line %d: invalid label name '%s'" % (line_no, name))

            # ---- extra feature: duplicate label warning ----
            if name in first_seen:
                warnings.append(
                    "Warning: label '%s' on line %d was already defined on line %d "
                    "(the later definition is used)"
                    % (name, line_no, first_seen[name])
                )
            else:
                first_seen[name] = line_no
            symbols[name] = rom_addr
            continue

        program.append((line_no, text))
        rom_addr += 1

    return program


# ---------------------------------------------------------------- pass 2
class VariableAllocator:
    def __init__(self, symbols):
        self.symbols = symbols
        self.next_free = 16

    def lookup(self, name):
        if name not in self.symbols:
            self.symbols[name] = self.next_free
            self.next_free += 1
        return self.symbols[name]


def encode_a(body, line_no, allocator):
    if not body:
        raise AsmError("Line %d: empty @ instruction" % line_no)
    if body.isdigit():
        value = int(body)
    else:
        if not is_valid_symbol(body):
            raise AsmError("Line %d: invalid symbol '%s'" % (line_no, body))
        value = allocator.lookup(body)
    if value > 32767:
        raise AsmError("Line %d: address %d is too large" % (line_no, value))
    return format(value, "016b")


def encode_c(text, line_no):
    dest, comp, jump = "", text, ""

    if "=" in comp:
        dest, comp = comp.split("=", 1)
    if ";" in comp:
        comp, jump = comp.split(";", 1)

    if dest not in DEST_BITS:
        raise AsmError("Line %d: invalid destination '%s'" % (line_no, dest))
    if comp not in COMP_BITS:
        raise AsmError("Line %d: invalid computation '%s'" % (line_no, comp))
    if jump not in JUMP_BITS:
        raise AsmError("Line %d: invalid jump '%s'" % (line_no, jump))

    return "111" + COMP_BITS[comp] + DEST_BITS[dest] + JUMP_BITS[jump]


def translate(program, symbols):
    allocator = VariableAllocator(symbols)
    output = []
    for line_no, text in program:
        if text.startswith("@"):
            output.append(encode_a(text[1:], line_no, allocator))
        else:
            output.append(encode_c(text, line_no))
    return output


# ---------------------------------------------------------------- driver
def assemble_file(path):
    with open(path, "r") as handle:
        source_lines = handle.read().splitlines()

    symbols = fresh_symbol_table()
    warnings = []

    program = collect_labels(source_lines, symbols, warnings)
    machine_code = translate(program, symbols)

    out_path = os.path.splitext(path)[0] + ".hack"
    with open(out_path, "w", newline="\n") as handle:
        for word in machine_code:
            handle.write(word + "\n")

    for w in warnings:
        print(w)
    return out_path, len(machine_code)


def main():
    if len(sys.argv) != 2:
        print("Usage: python assembler.py <file.asm>")
        sys.exit(1)

    path = sys.argv[1]
    if not os.path.isfile(path):
        print("Error: file '%s' not found" % path)
        sys.exit(1)

    try:
        out_path, count = assemble_file(path)
    except AsmError as err:
        print("Error:", err)
        sys.exit(1)

    print("Assembled %d instructions -> %s" % (count, out_path))


if __name__ == "__main__":
    main()