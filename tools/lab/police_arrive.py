#!/usr/bin/env python3
"""How often does the police turn up after the first star, when the player
just stands there (scene busted)? And with a rampage (scene shoot)?

  python3 tools/lab/police_arrive.py <host_sim> <fxdata.bin> <label> [scene] [seeds]
"""
import os, re, subprocess, sys

sim, data, label = sys.argv[1:4]
scene = sys.argv[4] if len(sys.argv) > 4 else "busted"
nseeds = int(sys.argv[5]) if len(sys.argv) > 5 else 24
HERE = os.path.dirname(os.path.abspath(__file__))
TPF = 7
came = busted = wasted = forgot = 0
lines = []
for seed in range(nseeds):
    env = dict(os.environ, SCENE=scene, SEED=str(seed + 1))
    out = subprocess.run([sim, data, os.path.join(HERE, "arrive.raw"), "2600", str(TPF)], env=env,
                         capture_output=True, text=True).stdout
    star = police = end = None
    what = "still wanted"
    most = 0
    for line in out.splitlines():
        m = re.match(r"frame (\d+): (.*)", line)
        if not m:
            continue
        f, text = int(m.group(1)), m.group(2)
        if star is None:
            if re.match(r"1 stars", text):
                star = f
            continue
        m2 = re.match(r"(\d) stars", text)
        if m2:
            most = max(most, int(m2.group(1)))
            if m2.group(1) == "0":
                end, what = f, "forgotten"
                break
        if police is None and (text.startswith("a police car is on its way") or text.startswith("an officer is out")):
            police = f
        if text.startswith("BUSTED") or text.startswith("WASTED"):
            end, what = f, text.split()[0]
            break
    if star is None:
        lines.append("seed %2d: no star" % seed)
        continue
    sec = lambda f: (f - star) * TPF / 156.0
    if police is not None:
        came += 1
    busted += what == "BUSTED"
    wasted += what == "WASTED"
    forgot += what == "forgotten"
    lines.append("seed %2d: police %s, %s%s, most stars %d" % (
        seed, "after %4.1f s" % sec(police) if police is not None else "never       ",
        what, " after %4.1f s" % sec(end) if end is not None else "", max(most, 1)))
print("%s, %s: police came %d of %d; BUSTED %d, WASTED %d, stars forgotten %d" % (
    label, scene, came, nseeds, busted, wasted, forgot))
if os.environ.get("LINES"):
    print("\n".join("   " + l for l in lines))
try:
    os.remove(os.path.join(HERE, "arrive.raw"))
except OSError:
    pass
