#!/usr/bin/env python3
"""Does the game still do what it did? Builds the desktop build from the
sources as they are, plays a list of scenes with it, and writes down a
fingerprint of every scene's pictures and of what it printed. Two runs with
the same fingerprints showed the same pictures, frame by frame.

  python3 tools/lab/regress.py save before     play, and keep the fingerprints as build/regress/before.txt
  python3 tools/lab/regress.py check before    play, and say which scenes differ from those

The game data is taken from build/game (tools/build.sh makes it), or from
what DATA says (DATA=build/dev/fxdata.bin).
"""
import hashlib, os, subprocess, sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")) + "/"
OUT = ROOT + "build/regress/"

# name, frames, what is set for it
SCENES = [
    ("tour", 1100, {}),
    ("pages", 420, {"SCENE": "pages"}),
    ("nav", 700, {"SCENE": "nav"}),
    ("shoot", 500, {"SCENE": "shoot", "SEED": "3"}),
    ("car", 400, {"SCENE": "car", "SEED": "5"}),
    ("people", 300, {"SCENE": "people"}),
    ("jack", 400, {"SCENE": "jack", "SEED": "2"}),
    ("busted", 900, {"SCENE": "busted", "SEED": "7"}),
    ("wasted", 900, {"SCENE": "wasted", "SEED": "8"}),
    ("chase", 900, {"SCENE": "chase", "SEED": "9"}),
    ("flee", 900, {"SCENE": "flee", "STARS": "2", "SEED": "11"}),
    ("walk", 300, {"SCENE": "walk"}),
    # missions, played by a list of orders (host/host_main.cpp, PLAY)
    ("job-drive", 900, {"PLAY": "walk:91.4,154.6;down;wait:30;b;wait:40;car;drive:93,153.5;drive:110,153.5;"
                                "drive:112.5,151;drive:112.5,116;drive:114.5,113.5;drive:119,113.5;stop;wait:150"}),
    ("job-taxi", 800, {"DONE": "100", "PLAY": "walk:91.2,154.6;down;wait:20;b;car;kind:0;drive:93,153.5;drive:96.5,153.5;"
                                              "drive:98.5,151;drive:98.5,127;drive:100,125.5;drive:104,125.5;stop;wait:40;"
                                              "kind:3;wait:40;at:56.5,206.5;wait:120"}),
    ("job-hit", 900, {"DONE": "200", "PLAY": "walk:91.2,154.6;down;wait:20;b;walk:84.5,154.5;walk:84.5,149.6;hunt;flee;wait:120"}),
    ("job-frenzy", 800, {"DONE": "300", "SEED": "5", "PLAY": "walk:91.2,154.6;down;wait:20;b;spree;wait:120"}),
    ("job-late", 1700, {"DONE": "300", "PLAY": "walk:91.2,154.6;down;wait:20;b;wait:1500"}),
    ("job-dead", 700, {"DONE": "300", "SEED": "3", "PLAY": "walk:91.2,154.6;down;wait:20;b;stars:3;health:2;wait:600"}),
    ("job-getaway", 600, {"DONE": "440", "PLAY": "at:209.2,205.5;wait:30;down;wait:20;b;wait:20;at:93,124.5;wait:10;car;wait:10;"
                                                 "at:92.5,124.5;wait:40;stars:0;wait:40;at:223,203.5;wait:120"}),
    ("job-cops", 1000, {"DONE": "441", "SEED": "4", "PLAY": "at:209.2,205.5;wait:30;down;wait:20;b;wait:20;at:91,154.6;spree;flee;wait:100"}),
    ("job-no", 400, {"PLAY": "walk:91.4,154.6;down;wait:30;a;wait:30;map;wait:20;hold:80,50;wait:20;map;wait:30"}),
    ("job-over", 500, {"CASH": "250", "DONE": "210", "PLAY": "walk:91.4,154.6;down;wait:20;b;wait:30;map;wait:10;a;wait:20;"
                                                             "hold:10,3;wait:10;hold:10,3;wait:20;b;wait:30;b;wait:30;a;wait:30;b;wait:60"}),
]


def build():
    os.makedirs(OUT, exist_ok=True)
    r = subprocess.run(["clang++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Wno-unused-function",
                        "-Wno-ignored-attributes", "-DHOST", "-o", OUT + "host_sim", ROOT + "host/host_main.cpp"],
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stderr[-3000:])
    if r.stderr.strip():
        print(r.stderr.strip()[-2000:])


def play():
    prints = {}
    for name, frames, env in SCENES:
        e = dict(os.environ)
        for k in ("SCENE", "SEED", "STARS", "FOOT", "STILL", "TRACE", "NAV_TO", "HERO_AT", "SETTINGS", "RANGE", "LIST",
                  "PLAY", "CASH"):
            e.pop(k, None)
        # DONE is left as it is for the scenes that do not say: DONE=444 plays
        # the old scenes with no telephone ringing
        e.update(env)
        raw = OUT + name + ".raw"
        r = subprocess.run([OUT + "host_sim", ROOT + os.environ.get("DATA", "build/game/fxdata.bin"), raw, str(frames), "7"],
                           capture_output=True, text=True, env=e)
        if r.returncode:
            sys.exit("%s: %s" % (name, r.stderr[-2000:]))
        with open(raw, "rb") as f:
            pictures = hashlib.sha256(f.read()).hexdigest()[:16]
        os.remove(raw)
        with open(OUT + name + ".log", "w") as f:
            f.write(r.stdout)
        prints[name] = (pictures, hashlib.sha256(r.stdout.encode()).hexdigest()[:16])
    return prints


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("save", "check"):
        sys.exit(__doc__)
    build()
    prints = play()
    path = OUT + sys.argv[2] + ".txt"
    if sys.argv[1] == "save":
        with open(path, "w") as f:
            for name, (p, t) in prints.items():
                f.write("%s %s %s\n" % (name, p, t))
        # what was printed, to compare with later
        for name in prints:
            os.replace(OUT + name + ".log", OUT + sys.argv[2] + "-" + name + ".log")
        print("kept: %s (%d scenes)" % (path, len(prints)))
        return
    before = {}
    with open(path) as f:
        for line in f:
            name, p, t = line.split()
            before[name] = (p, t)
    bad = 0
    for name, (p, t) in prints.items():
        if name not in before:
            print("%-8s new" % name)
            continue
        same_p, same_t = before[name][0] == p, before[name][1] == t
        if same_p and same_t:
            print("%-8s the same" % name)
        else:
            bad += 1
            print("%-8s DIFFERS: %s%s   (what it printed: build/regress/%s.log, before: %s-%s.log)"
                  % (name, "" if same_p else "pictures ", "" if same_t else "what it printed", name, sys.argv[2], name))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
