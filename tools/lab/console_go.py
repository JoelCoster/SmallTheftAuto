#!/usr/bin/env python3
"""On the console (test build): go along a list of places, steering by what
the console says about where the player is, and say what the arrow and the
label show on the way, and what they should show.

  python3 tools/lab/console_go.py [to:x,y] [run] [picture:prefix] x,y x,y ...     (cells, as on the map)

  to:x,y     the place the arrow is to lead to (put straight into memory)
  run        run (A held) instead of walking
The game must be on (not the title).
"""
import math, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import diag

UP, DOWN, LEFT, RIGHT, A, B = 0x80, 0x10, 0x20, 0x40, 0x08, 0x04
way, to, run, pictures = [], None, False, None
for a in sys.argv[1:]:
    if a.startswith("to:"):
        to = tuple(int(v) for v in a[3:].split(","))
    elif a == "run":
        run = True
    elif a.startswith("picture:"):
        pictures = a[8:]
    else:
        way.append(tuple(float(v) for v in a.split(",")))
limit = float(os.environ.get("SECONDS", "90"))

with diag.Console() as c:
    t0 = time.monotonic()
    if to:
        c.poke("nav_way", 255)
        c.poke("nav_y", to[1])
        c.poke("nav_x", to[0])
    held = -1
    at = 0
    said = ""
    shots = 0
    checked = wrong = far_wrong = 0
    was_going = False
    next_picture = 0.0
    while True:
        now = time.monotonic() - t0
        if now > limit:
            print("%6.1f  time is up" % now)
            break
        s = c.state()
        x, y = s["x"], s["y"]
        going = bool(s["nav_x"]) and s["label_show"] == 2
        note = "stars %d health %d" % (s["wanted"], s["health"])
        if going:
            dx = (s["nav_x"] * 4 + 2) - s["x_raw"] / 64.0
            dy = (s["nav_y"] * 4 + 2) - s["y_raw"] / 64.0
            far = math.hypot(dx, dy)
            turn = math.atan2(dx, -dy) - s["cam_yaw"] / 65536.0 * 2 * math.pi
            should = round(turn / (2 * math.pi) * 32) & 31
            off = (s["nav_way"] - should) & 31
            label = s["label"]
            try:
                says = int(label[0]) * 1000 + int(label[2]) * 100 if label[3] == "K" else int(label[:3])
            except ValueError:
                says = -1
            ok_far = abs(says - far) < (55 if label[3] == "K" else 4)
            ok_way = off in (0, 1, 31)
            checked += 1
            wrong += not ok_way
            far_wrong += not ok_far
            note += "; arrow %d (should be %d)%s, label %s (it is %.0f m)%s" % (
                s["nav_way"], should, "" if ok_way else " WRONG", label, far, "" if ok_far else " WRONG")
            was_going = True
        elif was_going and not s["nav_x"]:
            print("%6.1f  at %.1f,%.1f  there: the arrow is gone (display %d, label %d), sound playing: %s" % (
                now, x, y, s["disp_nav"], s["label_show"], s["playing"]))
            print("        checked %d times on the way: the arrow was wrong %d times, the distance %d times" % (
                checked, wrong, far_wrong))
            c.buttons(0)
            break
        if note != said and (now - shots > 1.0 or "WRONG" in note):
            print("%6.1f  at %.1f,%.1f heading %.0f  %s" % (now, x, y, s["heading"], note), flush=True)
            said = note
            shots = now
        if pictures and going and now >= next_picture:
            c.picture().resize((512, 256), 0).save("%s%02d.png" % (pictures, int(now)))
            next_picture = now + 4.0
        if at >= len(way):
            if held:
                c.buttons(0)
                held = 0
            time.sleep(0.1)
            continue
        tx, ty = way[at]
        if math.hypot(tx - x, ty - y) < 0.6:
            at += 1
            continue
        want = math.atan2(tx - x, -(ty - y))
        have = s["hd"] / 65536.0 * 2 * math.pi
        d = (want - have + math.pi) % (2 * math.pi) - math.pi
        b = 0
        if d > 0.12:
            b |= RIGHT
        elif d < -0.12:
            b |= LEFT
        if abs(d) < 0.6:
            b |= UP | (A if run else 0)
        if b != held:
            c.buttons(b)
            held = b
    c.buttons(0)
    print("        stack: %d bytes never used" % c.stack_free())
