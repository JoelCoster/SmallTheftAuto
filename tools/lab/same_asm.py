#!/usr/bin/env python3
"""Are the routines written in assembly the same in two builds, instruction
for instruction? The two interrupt routines are timed by hand (the display
routine sends a byte every 18 cycles), so an option of the compiler or the
linker that swaps one instruction for a shorter one must not reach them. The
renderer's loops and the arithmetic are not timed: there a call that has
become a short one is to the good.

  python3 tools/lab/same_asm.py game dev

Addresses in memory and in the program differ from build to build and are
left out of the comparison; which instruction, which registers and how far a
jump goes are compared.
"""
import glob, os, re, subprocess, sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")) + "/"
SOURCES = ("display.S", "sound.S", "render.S", "fastmath.S")
TIMED = ("display.S", "sound.S")


def routines(build):
    elf = ROOT + "build/" + build + "/SmallTheftAuto.ino.elf"
    od = glob.glob(ROOT + ".toolchain/data/packages/arduino/tools/avr-gcc/*/bin/avr-objdump")[0]
    text = subprocess.run([od, "-d", "-l", elf], capture_output=True, text=True, check=True).stdout
    out = {}                # file -> list of instructions, in the order of the program
    where = None
    symbol_at = None
    for line in text.splitlines():
        m = re.match(r"^[0-9a-f]{8} <(.+)>:$", line)
        if m:
            where = None
            continue
        m = re.match(r"^(/.*?|\S+?)([^/]+\.(?:S|h|ino|cpp|c)):(\d+)", line)
        if m:
            where = m.group(2)
            continue
        m = re.match(r"^\s+([0-9a-f]+):\t((?:[0-9a-f]{2} )+)\s*\t(\S+)\s*(.*)$", line)
        if m and where in SOURCES:
            at, raw, op, args = int(m.group(1), 16), m.group(2).split(), m.group(3), m.group(4)
            args = args.split(";")[0].strip()
            if op in ("lds", "sts"):
                args = re.sub(r"0x[0-9a-fA-F]+", "(memory)", args)
            elif op in ("call", "jmp"):
                args = "(program)"
            elif op in ("ldi", "subi", "sbci", "cpi"):
                # the two halves of an address are numbers like any other: leave them out
                args = args.split(",")[0] + ", (number)"
            out.setdefault(where, []).append((op, args, len(raw)))
    return out


def main():
    a, b = routines(sys.argv[1]), routines(sys.argv[2])
    bad = 0
    for f in SOURCES:
        x, y = a.get(f, []), b.get(f, [])
        if x == y:
            print("%-12s the same: %d instructions, %d bytes" % (f, len(x), sum(i[2] for i in x)))
            continue
        if f in TIMED:
            bad += 1
        print("%-12s %s: %d instructions and %d bytes in %s, %d and %d in %s"
              % (f, "DIFFERS" if f in TIMED else "differs (not timed by hand)", len(x), sum(i[2] for i in x),
                 sys.argv[1], len(y), sum(i[2] for i in y), sys.argv[2]))
        for k, (i, j) in enumerate(zip(x, y)):
            if i != j:
                print("    the first difference, instruction %d: %s %s  /  %s %s" % (k, i[0], i[1], j[0], j[1]))
                break
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
