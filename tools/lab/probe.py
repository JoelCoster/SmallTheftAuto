#!/usr/bin/env python3
"""Try a build out on the console that cannot be asked over USB how it is
doing. The build (made with -DPROBE, see SmallTheftAuto/probe.h) plays by
itself for 14 seconds, writes down how it went and goes back to the console's
menu; this loads it, waits, and reads what it wrote.

  python3 tools/lab/probe.py exp [times [picture.png]]    the build in build/exp, so many times

The console's game list is not touched. What is written is in the last 4 KB
of the flash chip, which belong to test builds.
"""
import os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import diag
from arduboycart import device

PAGE = 0xFFF0


def once(build):
    diag.cmd_load([build])
    time.sleep(19.5)
    with diag.connect(wait=20.0) as loader:
        r = loader.read_flash(PAGE, 6)
    if r[:4] != b"PRB\x01":
        return None
    frames = r[4] | (r[5] << 8)
    took = r[6] | (r[7] << 8)
    n = diag.COLS * diag.COLBYTES
    hud, hi, lo = r[256:384], r[384:384 + n], r[384 + n:384 + 2 * n]
    return dict(frames=frames, ticks=took, fps=frames * 156.0 / took if took else 0.0,
                unused=r[8] | (r[9] << 8), fails=r[10], last=r[11],
                picture=diag.picture_from(hud, hi, lo))


def main():
    build = sys.argv[1] if len(sys.argv) > 1 else "exp"
    times = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    out = sys.argv[3] if len(sys.argv) > 3 else None
    for k in range(times):
        r = once(build)
        if not r:
            print("%s: nothing was written: the build did not get to the end" % build, flush=True)
            continue
        print("%s: %d pictures in %.2f s: %.2f a second; stack: %d bytes never used; "
              "the flash chip answered at the %s try"
              % (build, r["frames"], r["ticks"] / 156.0, r["fps"], r["unused"],
                 "first" if not r["fails"] else "%dth" % (r["fails"] + 1)), flush=True)
        if out:
            r["picture"].resize((512, 256), 0).save(out)
            print("the picture at the end:", out)


if __name__ == "__main__":
    main()
