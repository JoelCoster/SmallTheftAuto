#!/usr/bin/env python3
"""What do the compiler's options do to the size of the program? Builds the
program as it is, then once for every option (in build/exp, the real build is
not touched), and says how large it came out.

  python3 tools/lab/size_flags.py                       every option of the list below, one at a time
  python3 tools/lab/size_flags.py "-mrelax -mcall-prologues"   these together
  DEFINES=-DDIAG python3 tools/lab/size_flags.py ...    the same for the test build
"""
import os, re, subprocess, sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")) + "/"
CLI = ROOT + ".toolchain/bin/arduino-cli"

OPTIONS = [
    "-mrelax",
    "-mcall-prologues",
    "-fno-inline-small-functions",
    "-fno-tree-scev-cprop",
    "-fno-split-wide-types",
    "-fno-move-loop-invariants",
    "-fno-tree-loop-optimize",
    "-fno-jump-tables",
    "-fno-caller-saves",
    "-mstrict-X",
    "-fno-optimize-sibling-calls",
    "-fno-tree-switch-conversion",
    "-fno-ipa-cp",
    "-fno-ipa-sra",
    "-fno-partial-inlining",
    "-fno-tree-sra",
    "-fno-ivopts",
    "-fno-reorder-blocks",
    "-fno-tree-ter",
    "-fno-guess-branch-probability",
    "-ffreestanding",
]


def build(flags="", out="exp"):
    """(program bytes, memory bytes), or None and the compiler's complaint"""
    defines = os.environ.get("DEFINES", "")
    both = (defines + " " + flags).strip()
    cmd = [CLI, "--config-file", ROOT + ".toolchain/arduino-cli.yaml", "compile",
           "--fqbn", "arduino:avr:leonardo",
           "--build-property", "upload.maximum_size=29696",
           "--build-property", "compiler.cpp.extra_flags=" + both,
           "--build-property", "compiler.c.extra_flags=" + flags,
           "--build-property", "compiler.S.extra_flags=" + defines,
           "--build-property", "compiler.c.elf.extra_flags=" + flags,
           "--build-path", ROOT + "build/%s-obj" % out,
           "--output-dir", ROOT + "build/" + out,
           "SmallTheftAuto"]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    text = r.stdout + r.stderr
    m = re.search(r"Sketch uses (\d+) bytes", text)
    g = re.search(r"Global variables use (\d+) bytes", text)
    if not m:
        return None, text[-1200:]
    return (int(m.group(1)), int(g.group(1)) if g else 0), ""


def main():
    picks = sys.argv[1:] or OPTIONS
    base, why = build()
    if not base:
        sys.exit(why)
    print("as it is: %d bytes of program, %d of memory" % base, flush=True)
    for flags in picks:
        got, why = build(flags)
        if not got:
            print("%-32s did not build: %s" % (flags, why.strip().splitlines()[-1][:80]), flush=True)
            continue
        print("%-32s %d bytes (%+d), memory %+d" % (flags, got[0], got[0] - base[0], got[1] - base[1]), flush=True)


if __name__ == "__main__":
    main()
