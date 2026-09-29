#!/usr/bin/env python3
"""A rampage (scene shoot: shoots whoever comes along, picks up the money,
never gets out of the way): from the first star, how long until the police
is there, and how long until it is over?

  python3 tools/lab/police_rampage.py <host_sim> <fxdata.bin> <label> [seeds]
"""
import os, re, subprocess, sys

sim, data, label = sys.argv[1:4]
nseeds = int(sys.argv[4]) if len(sys.argv) > 4 else 16
HERE = os.path.dirname(os.path.abspath(__file__))
TPF = 7
rows = []
for seed in range(nseeds):
    env = dict(os.environ, SCENE="shoot", SEED=str(seed + 1))
    out = subprocess.run([sim, data, os.path.join(HERE, "rampage.raw"), "4000", str(TPF)], env=env,
                         capture_output=True, text=True).stdout
    star = police = end = None
    what = "going on"
    most = 0
    for line in out.splitlines():
        m = re.match(r"frame (\d+): (.*)", line)
        if not m:
            continue
        f, text = int(m.group(1)), m.group(2)
        m2 = re.match(r"(\d) stars", text)
        if star is None:
            if m2 and m2.group(1) != "0":
                star = f
                most = int(m2.group(1))
            continue
        if m2:
            most = max(most, int(m2.group(1)))
        if police is None and (text.startswith("a police car is on its way") or text.startswith("an officer is out")):
            police = f
        if text.startswith("BUSTED") or text.startswith("WASTED"):
            end, what = f, text.split()[0]
            break
    if star is None:
        continue
    sec = lambda f: (f - star) * TPF / 156.0
    rows.append((sec(police) if police is not None else None, sec(end) if end is not None else None, what, most))
got = [r for r in rows if r[1] is not None]
pol = sorted(r[0] for r in rows if r[0] is not None)
dur = sorted(r[1] for r in got)
def med(v):
    return v[len(v) // 2] if v else float("nan")
print("%s: %d runs with a star; police there after %.0f to %.0f s (middle %.0f); over after %.0f to %.0f s (middle %.0f), "
      "BUSTED %d, WASTED %d, not over %d; stars at most: %s" % (
          label, len(rows), pol[0] if pol else -1, pol[-1] if pol else -1, med(pol),
          dur[0] if dur else -1, dur[-1] if dur else -1, med(dur),
          sum(r[2] == "BUSTED" for r in rows), sum(r[2] == "WASTED" for r in rows),
          sum(r[1] is None for r in rows), " ".join(str(r[3]) for r in rows)))
try:
    os.remove(os.path.join(HERE, "rampage.raw"))
except OSError:
    pass
