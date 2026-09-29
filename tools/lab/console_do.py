#!/usr/bin/env python3
"""On the console (test build): one thing after the other.

  python3 tools/lab/console_do.py press:60:0.3 wait:0.5 state picture:map.png stars:2 poke:health:3 stack

  press:XX:seconds   hold buttons (hex) for so long
  wait:seconds
  state              one line of what the game is doing
  picture:file       the picture as it is on the screen
  stars:N            put so many stars on the record
  poke:name:value    a number into a variable
  stack              how much memory the stack has never touched
  watch:seconds      the state whenever it changes, for so long
"""
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import diag

with diag.Console() as c:
    t0 = time.monotonic()
    for a in sys.argv[1:]:
        p = a.split(":")
        now = time.monotonic() - t0
        if p[0] == "press":
            c.buttons(int(p[1], 16))
            time.sleep(float(p[2]) if len(p) > 2 else 0.3)
            c.buttons(0)
            time.sleep(0.15)
        elif p[0] == "wait":
            time.sleep(float(p[1]))
        elif p[0] == "state":
            print("%6.2f  %s" % (now, diag.say(c.state())), flush=True)
        elif p[0] == "picture":
            c.picture().resize((512, 256), 0).save(p[1])
            print("%6.2f  picture: %s" % (now, p[1]), flush=True)
        elif p[0] == "stars":
            c.stars(int(p[1]))
        elif p[0] == "poke":
            c.poke(p[1], int(p[2], 0))
        elif p[0] == "stack":
            print("%6.2f  stack: %d bytes never used" % (now, c.stack_free()), flush=True)
        elif p[0] == "watch":
            end = time.monotonic() + float(p[1])
            last = ""
            while time.monotonic() < end:
                text = diag.say(c.state())
                if text != last:
                    print("%6.2f  %s" % (time.monotonic() - t0, text), flush=True)
                    last = text
                time.sleep(0.15)
        else:
            sys.exit("what is %s?" % a)
