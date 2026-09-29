#!/usr/bin/env python3
"""Where does the program space go? From a build's machine code and what the
compiler noted about where every instruction comes from: bytes for every
function as it is written in the sources, wherever the compiler put its
instructions (most of the game ends up inside main), for every table, and
for what comes from Arduino's own code.

  python3 tools/lab/size_map.py [build] [-l] [-f name]     build: the name of its folder (game, dev, diag ...)

  -l        the sources line by line: the 40 most expensive lines
  -f name   the lines of one function
"""
import glob, os, re, subprocess, sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")) + "/"


def listing(build):
    elf = ROOT + "build/" + build + "/SmallTheftAuto.ino.elf"
    od = glob.glob(ROOT + ".toolchain/data/packages/arduino/tools/avr-gcc/*/bin/avr-objdump")[0]
    return subprocess.run([od, "-d", "-l", "-C", elf], capture_output=True, text=True, check=True).stdout


def functions_of(path):
    """(first line, last line, name) of every function written in a source file"""
    out = []
    try:
        lines = open(path, errors="replace").read().splitlines()
    except OSError:
        return out
    start = name = None
    for i, line in enumerate(lines, 1):
        if start is None:
            m = re.match(r"^[A-Za-z_][\w \*&:<>,]*?[\s\*&]+(\w+)\s*\([^;]*$", line)
            if m and not line.startswith(("typedef", "#", "//", "return", "extern \"C\"")) and m.group(1) not in ("if", "while", "for", "switch"):
                start, name = i, m.group(1)
                if line.rstrip().endswith("}"):
                    out.append((start, i, name))
                    start = None
        elif line.startswith("}"):
            out.append((start, i, name))
            start = None
    return out


def measure(build):
    text = listing(build)
    symbol = func = where = None
    by_line = {}            # (file, line) -> bytes
    by_symbol = {}          # symbol -> bytes with no line noted
    total = 0
    for line in text.splitlines():
        m = re.match(r"^[0-9a-f]{8} <(.+)>:$", line)
        if m:
            symbol, where = m.group(1), None
            continue
        m = re.match(r"^\s+[0-9a-f]+:\t((?:[0-9a-f]{2} )+)\s*\t", line)
        if m:
            n = len(m.group(1).split())
            total += n
            if where:
                by_line[where] = by_line.get(where, 0) + n
            else:
                by_symbol[symbol] = by_symbol.get(symbol, 0) + n
            continue
        m = re.match(r"^(/.*):(\d+)(?: \(discriminator \d+\))?$", line)
        if m:
            where = (m.group(1), int(m.group(2)))
    return total, by_line, by_symbol


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    want = [a for k, a in enumerate(sys.argv[1:]) if not a.startswith("-") and sys.argv[k] != "-f"]
    build = want[0] if want else "game"
    total, by_line, by_symbol = measure(build)

    files = {}
    for (f, l), n in by_line.items():
        files.setdefault(f, {})[l] = n
    rows = []               # (bytes, group, name)
    lines_of = {}
    for f, ls in files.items():
        short = os.path.basename(f)
        mine = "/SmallTheftAuto/SmallTheftAuto/" in f or "/sketch/" in f
        group = "game" if mine else "Arduino"
        if not mine or f.endswith(".S"):
            rows.append((sum(ls.values()), group, short))
            continue
        src = f
        if "/sketch/" in f:
            src = ROOT + "SmallTheftAuto/" + short.replace(".ino.cpp", ".ino")
        fs = functions_of(src)
        acc = {}
        for l, n in ls.items():
            ll = l
            if short.endswith(".ino.cpp"):
                ll = l      # (the sketch is copied with one line added at the top; names matter, not lines)
            name = "(outside any function)"
            for a, b, fn in fs:
                if a <= ll <= b:
                    name = fn
                    break
            acc[name] = acc.get(name, 0) + n
            lines_of.setdefault(name, []).append((ll, n, src))
        for name, n in acc.items():
            rows.append((n, group, "%s: %s" % (short, name)))
    for s, n in by_symbol.items():
        rows.append((n, "no line noted (tables, assembly, library)", s))

    if "-f" in sys.argv:
        want = sys.argv[sys.argv.index("-f") + 1]
        got = sorted(lines_of.get(want, []))
        src_lines = {}
        print("%s: %d bytes" % (want, sum(n for _, n, _ in got)))
        for l, n, src in got:
            if src not in src_lines:
                src_lines[src] = open(src, errors="replace").read().splitlines()
            print("%5d %4d  %s" % (l, n, src_lines[src][l - 1].rstrip()[:110]))
        return
    if "-l" in sys.argv:
        top = sorted(((n, f, l) for (f, l), n in by_line.items()), reverse=True)[:40]
        for n, f, l in top:
            try:
                src = open(f, errors="replace").read().splitlines()[l - 1].strip()
            except (OSError, IndexError):
                src = ""
            print("%5d  %s:%d  %s" % (n, os.path.basename(f), l, src[:90]))
        return

    print("%d bytes of program in all (%s build)\n" % (total, build))
    groups = {}
    for n, g, name in rows:
        groups[g] = groups.get(g, 0) + n
    for g, n in sorted(groups.items(), key=lambda kv: -kv[1]):
        print("%6d  %s" % (n, g))
    print()
    for n, g, name in sorted(rows, reverse=True):
        if n >= 24:
            print("%6d  %-8s %s" % (n, "" if g == "game" else "Arduino" if g == "Arduino" else "-", name))


if __name__ == "__main__":
    main()
