#!/usr/bin/env python3
"""Getting away (scene flee): of the runs in which the police came and saw the
player, how many got away, and how long did it take?

  python3 tools/lab/police_count.py <host_sim> <fxdata.bin> <label> [runs] [car|foot ...]
"""
import os, re, subprocess, sys

sim, data, label = sys.argv[1:4]
runs = int(sys.argv[4]) if len(sys.argv) > 4 else 24
hows = sys.argv[5:] or ["car", "foot"]
HERE = os.path.dirname(os.path.abspath(__file__))
TPF = 7
for how in hows:
    for stars in (1, 2, 3, 4):
        nobody = away = caught = still = 0
        times = []
        for seed in range(1, runs + 1):
            env = dict(os.environ, SCENE="flee", STARS=str(stars), SEED=str(seed))
            env.pop("FOOT", None)
            if how == "foot":
                env["FOOT"] = "1"
            out = subprocess.run([sim, data, os.path.join(HERE, "count_%d.raw" % os.getpid()), "3000", str(TPF)],
                                 env=env, capture_output=True, text=True).stdout
            m = re.search(r"the police is there \((\d) stars, (\d) out\)", out)
            if not m or m.group(2) == "0" or int(m.group(1)) < stars:
                nobody += 1
                continue
            m = re.search(r"(got rid of the stars|caught) after \d+ frames \((\d+) s\)", out)
            if not m:
                still += 1
            elif m.group(1) == "caught":
                caught += 1
            else:
                away += 1
                times.append(int(m.group(2)))
        came = away + caught + still
        times.sort()
        print("%s, by %s, %d stars: the police came in %d of %d; got away %d of %d%s%s%s" % (
            label, how, stars, came, runs, away, came,
            " in %d to %d s (middle %d)" % (times[0], times[-1], times[len(times) // 2]) if times else "",
            ", caught %d" % caught if caught else "", ", still wanted at the end %d" % still if still else ""),
            flush=True)
try:
    os.remove(os.path.join(HERE, "count_%d.raw" % os.getpid()))
except OSError:
    pass
