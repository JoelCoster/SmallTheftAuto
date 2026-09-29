#!/usr/bin/env python3
"""What does a piece of the program cost? Builds the program with pieces
left out (one at a time) and says how much smaller it gets. The sources are
put back as they were.

  python3 size_try.py
"""
import os, re, shutil, subprocess, sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")) + "/"
SRC = ROOT + "SmallTheftAuto/"
KEEP = {}


def build(flags=""):
    env = dict(os.environ, OUT="exp")
    if flags:
        env["EXTRA_FLAGS"] = flags
    out = subprocess.run([ROOT + "tools/build.sh"], env=env, capture_output=True, text=True, cwd=ROOT)
    m = re.search(r"Sketch uses (\d+) bytes", out.stdout + out.stderr)
    if not m:
        print((out.stdout + out.stderr)[-1500:])
        return None
    return int(m.group(1))


def swap(name, old, new):
    p = SRC + name
    src = open(p).read()
    KEEP.setdefault(name, src)
    assert src.count(old) == 1, (name, old[:60], src.count(old))
    open(p, "w").write(src.replace(old, new))


def restore():
    for name, src in KEEP.items():
        open(SRC + name, "w").write(src)
    KEEP.clear()


TRIES = {
    "nav_step": [("game.h", "static void nav_step() {\n  if (nav_x) {", "static void nav_step() {\n  if (0) {")],
    "label_column": [("engine.h", "  if (label_show) label_column(c);\n", "")],
    "road snap": [("pages.h", "  for (uint8_t far = 0; far < 32; far++) {", "  for (uint8_t far = 0; far < 0; far++) {")],
    "cross": [("pages.h", "static void map_cross() {\n", "static void map_cross() {\n  return;\n")],
    "cursor": [("pages.h", "      if (go && ((fresh & go) || (uint8_t)(tick - map_tick) >= map_wait)) {",
                "      if (0) {")],
    "ring": [("pages.h", "      if (nav_x) {\n        page_mark(", "      if (0) {\n        page_mark(")],
    "put away": [("pages.h", "      if ((btn & (BTN_LEFT | BTN_RIGHT)) == (BTN_LEFT | BTN_RIGHT)) {", "      if (0) {")],
}

if __name__ == "__main__":
    picks = sys.argv[1:] or list(TRIES)
    base = build()
    print("as it is: %d bytes" % base, flush=True)
    for name in picks:
        try:
            for f, old, new in TRIES[name]:
                swap(f, old, new)
            n = build()
        finally:
            restore()
        print("without %-14s %s" % (name + ":", "%d bytes (%d less)" % (n, base - n) if n else "did not build"), flush=True)
