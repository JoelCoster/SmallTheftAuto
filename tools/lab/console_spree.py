#!/usr/bin/env python3
"""On the console (test build): shoot at whoever is nearest, for so many
seconds or until a mission that is on has ended, steering by what the
console says about where everybody is. Says what the mission counts.

  python3 tools/lab/console_spree.py [seconds] [picture.png]

The game must be on, the player on foot.
"""
import math, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import diag

UP, DOWN, LEFT, RIGHT, A, B = 0x80, 0x10, 0x20, 0x40, 0x08, 0x04
limit = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
picture = sys.argv[2] if len(sys.argv) > 2 else None

with diag.Console() as c:
    t0 = time.monotonic()
    held = -1
    said = ""
    had_job = False
    low = 9999
    while time.monotonic() - t0 < limit:
        s = c.state()
        now = time.monotonic() - t0
        note = "stars %d, health %d, $%d" % (s["wanted"], s["health"], s["cash"])
        if s["job"] != 255:
            had_job = True
            note += "; mission %d step %d: %d to go, %d s left" % (s["job"], s["job_at"], s["job_left"], s["job_clock"] // 156)
        elif had_job:
            note += "; the mission is over, missions done %s" % "".join(str(v) for v in s["done"])
        if s["note"]:
            note += "; lettering in the picture"
            if picture:
                c.picture().resize((512, 256), 0).save(picture)
                picture = None
        if s["over"]:
            note += "; WASTED or BUSTED"
        if note != said:
            print("%6.1f  %s" % (now, note), flush=True)
            said = note
        if had_job and s["job"] == 255 and not s["note"]:
            break
        b = 0
        best = None
        for p in s.get("peds", ()):
            if p["state"] not in (1, 2):
                continue
            d = math.hypot(p["x"] - s["x"], p["y"] - s["y"])
            if best is None or d < best[0]:
                best = (d, p)
        if best and not s["over"]:
            d, p = best
            want = math.atan2(p["x"] - s["x"], -(p["y"] - s["y"]))
            have = s["hd"] / 65536.0 * 2 * math.pi
            off = (want - have + math.pi) % (2 * math.pi) - math.pi
            if off > 0.06:
                b |= RIGHT
            elif off < -0.06:
                b |= LEFT
            if d > 9:
                if abs(off) < 0.5:
                    b |= UP | A
            elif abs(off) < 0.1:
                b |= B
        if b != held:
            c.buttons(b)
            held = b
        low = min(low, c.stack_free())
    c.buttons(0)
    print("        stack: %d bytes never used" % c.stack_free())
