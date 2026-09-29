#!/usr/bin/env python3
"""How deep can the stack get? From the machine code of a build: what every
function puts on the stack (registers, room for its variables, the return
address of whatever it calls), and the deepest chain of calls, with the most
expensive interrupt on top.

  python3 tools/lab/stack_depth.py [game|diag] [-v]
"""
import re, subprocess, sys, glob, os

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")) + "/"
build = sys.argv[1] if len(sys.argv) > 1 else "game"
elf = ROOT + "build/" + build + "/SmallTheftAuto.ino.elf"
od = glob.glob(ROOT + ".toolchain/data/packages/arduino/tools/avr-gcc/*/bin/avr-objdump")[0]
text = subprocess.run([od, "-d", "-C", elf], capture_output=True, text=True, check=True).stdout

funcs = {}          # name -> dict(addr, lines)
order = []
cur = None
for line in text.splitlines():
    m = re.match(r"^([0-9a-f]{8}) <(.+)>:$", line)
    if m:
        cur = m.group(2)
        funcs[cur] = dict(addr=int(m.group(1), 16), lines=[])
        order.append(cur)
        continue
    m = re.match(r"^\s+([0-9a-f]+):\t([0-9a-f ]+)\t(\S+)\s*(.*)$", line)
    if m and cur:
        funcs[cur]["lines"].append((int(m.group(1), 16), m.group(3), m.group(4)))

by_addr = {f["addr"]: n for n, f in funcs.items()}


def analyse(name):
    f = funcs[name]
    depth = 0           # bytes on the stack at this point of the function
    most = 0
    calls = []          # (callee, bytes on the stack at the call)
    frame = 0
    lines = f["lines"]
    for i, (addr, op, args) in enumerate(lines):
        if op == "push":
            depth += 1
        elif op == "pop":
            depth = max(0, depth - 1)
        elif op in ("sbiw", "subi", "sbci") and args.startswith("r28"):
            # room for variables: sbiw r28, N  (then out SP)  or  subi r28, N / sbci r29, M
            m = re.match(r"r28, 0x([0-9a-fA-F]+)", args)
            if m and i > 0 and any(l[1] == "in" and "0x3d" in l[2] for l in lines[max(0, i - 4):i]):
                n = int(m.group(1), 16)
                if op == "subi" and n > 127:
                    n = 256 - n if n > 200 else n
                frame = max(frame, n)
                depth += n
        elif op in ("call", "rcall"):
            m = re.search(r"0x([0-9a-f]+)", args)
            target = None
            if m:
                target = by_addr.get(int(m.group(1), 16))
            if op == "rcall" and args.strip() == ".+0":
                depth += 2              # (a way of making room)
                continue
            calls.append((target, depth + 2, addr))
        elif op in ("icall", "eicall"):
            calls.append((None, depth + 2, addr))
        most = max(most, depth)
    return most, calls, frame


info = {n: analyse(n) for n in order}
memo = {}


def deepest(name, seen=()):
    if name in memo:
        return memo[name]
    if name in seen:
        return (0, [name + " (again)"])
    most, calls, frame = info[name]
    best = (most, [name])
    for callee, at, addr in calls:
        if callee is None or callee not in info:
            d, chain = 0, ["?"]
        else:
            d, chain = deepest(callee, seen + (name,))
        if at + d > best[0]:
            best = (at + d, [name] + chain)
    memo[name] = best
    return best


isrs = [n for n in order if n.startswith("__vector_")]
print("interrupts:")
worst_isr = 0
for n in isrs:
    d, chain = deepest(n)
    d += 2          # the return address the interrupt itself puts there
    worst_isr = max(worst_isr, d)
    print("  %-14s %3d bytes  %s" % (n, d, " > ".join(chain[1:4])))
d, chain = deepest("main")
print("main: %d bytes at the deepest: %s" % (d, " > ".join(chain)))
print("with the most expensive interrupt on top: %d bytes" % (d + worst_isr))
if "-v" in sys.argv:
    for n in order:
        most, calls, frame = info[n]
        dd, ch = deepest(n)
        if dd > 20:
            print("  %-60s own %3d, deepest %3d" % (n[:60], most, dd))
