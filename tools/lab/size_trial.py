#!/usr/bin/env python3
"""What does a change to the sources do to the size of the program? Tries
changes one at a time, each on top of the ones before that were worth it, in
build/exp; the sources are put back as they were unless KEEP=1.

  DEFINES=-DNO_USB FLAGS="-mrelax -mcall-prologues -mstrict-X" python3 tools/lab/size_trial.py trials.py

trials.py holds TRIALS = [(name, [(file, old, new), ...]), ...]
"""
import os, sys, runpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import size_flags

SRC = size_flags.ROOT + "SmallTheftAuto/"


def main():
    trials = runpy.run_path(sys.argv[1])["TRIALS"]
    flags = os.environ.get("FLAGS", "")
    before = {}
    base, why = size_flags.build(flags)
    if not base:
        sys.exit(why)
    print("as it is: %d bytes of program, %d of memory" % base, flush=True)
    now = base
    try:
        for name, swaps in trials:
            undo = {}
            for f, old, new in swaps:
                p = SRC + f
                src = open(p).read()
                before.setdefault(f, src)
                undo.setdefault(f, src)
                if src.count(old) != 1:
                    print("%-40s (the place was found %d times in %s: left out)" % (name, src.count(old), f))
                    for g, s in undo.items():
                        open(SRC + g, "w").write(s)
                    undo = None
                    break
                open(p, "w").write(src.replace(old, new))
            if undo is None:
                continue
            got, why = size_flags.build(flags)
            if not got:
                print("%-40s did not build: %s" % (name, why.strip()[-400:]), flush=True)
                for g, s in undo.items():
                    open(SRC + g, "w").write(s)
                continue
            d = got[0] - now[0]
            keep = d < 0
            print("%-40s %d bytes (%+d), memory %+d%s" % (name, got[0], d, got[1] - now[1], "" if keep else "   not kept"), flush=True)
            if keep:
                now = got
            else:
                for g, s in undo.items():
                    open(SRC + g, "w").write(s)
    finally:
        if not os.environ.get("KEEP"):
            for f, s in before.items():
                open(SRC + f, "w").write(s)
    print("all that were kept: %d bytes (%+d), memory %+d" % (now[0], now[0] - base[0], now[1] - base[1]))


if __name__ == "__main__":
    main()
