#!/usr/bin/env python3
"""
Small Theft Auto missions.

The missions are not in the program: they are data on the flash chip, next to
the city. The program holds what it takes to play one (SmallTheftAuto/game.h,
"missions"): it reads a step, waits until what the step asks for has happened,
and reads the next. A new mission is a new entry in the list below, and costs
no program space.

A mission is offered by one of the telephones in the city, which rings when
the player comes by. It has a name, what it pays, a few lines of text, and
steps:

    go(place, ...)        be there. car="taxi": in a taxi ("any": in any car);
                          stop=True: standing still
    kill(n, ...)          so many people, whoever they are. cops=True: officers
    hit(place, shirt)     one person, who walks about at that place and has a
                          sign over them. shirt: "white", "grey", "dark"
    lose()                no stars left

    Every step takes: secs=90 (the clock is set to that when the step begins;
    when it runs out the mission has failed), stars=3 (the player gets that
    many when it begins), hint="TO THE DOCKS" (what the bottom line of the
    screen says), and for steps that need a car need="GET A TAXI" (what it
    says as long as the player is not in one).

Places are given roughly, in cells of the city, and put on the nearest street
(or, for people and telephones, the nearest pavement) by place().

Run by itself it lists the missions as they come out, with how far it is
from one step to the next:

    python3 tools/missions.py
"""
import os, pickle, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))

JOB_BYTES = 512                      # one mission on the flash chip
JOB_TEXT = 16                        # where its text begins: 6 lines
LINE = 30                            # glyphs to the line
LINES = 6
JOB_STEPS = 224                      # where its steps begin
STEP_BYTES = 32                      # what a step asks for (8 bytes), and its two hints
HINT = 12                            # glyphs to the hint
MAX_STEPS = (JOB_BYTES - JOB_STEPS) // STEP_BYTES - 1      # and the end after them
PAY_UNIT = 50                        # dollars

STEP_END, STEP_GO, STEP_KILL, STEP_LOSE = 0, 1, 2, 3
STEP_COUNT = 0x08                    # the bottom line of the screen says how many people are still to go
STEP_CAR, STEP_STOP, STEP_MARK, STEP_COPS = 0x10, 0x20, 0x40, 0x80
CLOCK = 256 / 156.0                  # seconds to a step of the clock (256 ticks)
CARS = {"sedan": 0, "taxi": 3, "van": 4, "sports": 5, "police": 6, "any": 7}
SHIRTS = {"white": 0, "grey": 1, "dark": 2}

# ---------------------------------------------------------------- the telephones
# (name of whoever is on the line, roughly where)
PHONES = [
    ("VINNIE", (91, 154)),           # downtown, a few steps from where the game begins
    ("LOLA", (119, 99)),             # at the park in the north-east
    ("THE CAPTAIN", (209, 202)),     # at the docks, where the south bridge comes in
]

# ---------------------------------------------------------------- places
PLACES = {
    "garage at the park": ("street", (119, 112)),
    "hotel": ("street", (104, 124)),
    "south park": ("street", (55, 205)),
    "plaza": ("walk", (84, 145)),
    "stop one": ("street", (131, 120)),
    "stop two": ("street", (112, 152)),
    "stop three": ("street", (88, 112)),
    "north docks": ("street", (212, 38)),
    "docks": ("street", (222, 203)),
    "park": ("walk", (119, 111)),
    "downtown": ("walk", (96, 129)),
    "bank": ("street", (92, 124)),
    "north plaza": ("street", (132, 95)),
    "judge": ("walk", (132, 93)),
}


def go(to, car=None, stop=False, **kw):
    return dict(op=STEP_GO | (STEP_CAR if car else 0) | (STEP_STOP if stop else 0), to=to,
                n=CARS[car] if car else 0, **kw)


def kill(n, cops=False, **kw):
    return dict(op=STEP_KILL | STEP_COUNT | (STEP_COPS if cops else 0), n=n, **kw)


def hit(at, shirt, **kw):
    return dict(op=STEP_KILL | STEP_MARK, to=at, n=1, who=SHIRTS[shirt], **kw)


def lose(**kw):
    return dict(op=STEP_LOSE, **kw)


# ---------------------------------------------------------------- the missions
# In the order in which a telephone offers them: the first one of its own
# that has not been done yet.
MISSIONS = [
    dict(name="WARM UP", phone=0, pay=100,
         text="VINNIE HERE. YOU THE NEW GUY? GET A CAR, ANY CAR, AND BRING IT TO MY GARAGE "
              "AT THE PARK. STOP THERE AND IT IS MINE.",
         steps=[go("garage at the park", car="any", stop=True, secs=180,
                   hint="STOP THERE", need="GET A CAR")]),
    dict(name="TAXI DRIVER", phone=0, pay=200,
         text="MY COUSIN NEEDS A RIDE, AND HE HATES WAITING. GET A TAXI, PICK HIM UP AT THE HOTEL "
              "AND DROP HIM AT THE SOUTH PARK.",
         steps=[go("hotel", car="taxi", stop=True, secs=150, hint="PICK HIM UP", need="GET A TAXI"),
                go("south park", car="taxi", stop=True, secs=90, hint="DROP HIM OFF", need="GET A TAXI")]),
    dict(name="LOUDMOUTH", phone=0, pay=400,
         text="A GUY IN A WHITE SHIRT TALKS TOO MUCH. HE WALKS HIS ROUNDS AT THE PLAZA. "
              "SHUT HIM UP, THEN LOSE THE POLICE.",
         steps=[hit("plaza", "white", secs=150, hint="SHUT HIM UP"),
                lose(secs=150, hint="LOSE THEM")]),
    dict(name="FRENZY", phone=0, pay=500,
         text="SOME DAYS I JUST HATE THIS TOWN. TAKE OUT 10 PEOPLE IN 60 SECONDS, ANY WAY YOU LIKE. "
              "CALL IT ADVERTISING.",
         steps=[kill(10, secs=60, hint="TO GO:")]),

    dict(name="SPEED DATE", phone=1, pay=300,
         text="LOLA. I FIX CARS, AND I LIKE THEM FAST. SHOW ME YOU CAN DRIVE: THREE STOPS ROUND "
              "TOWN, AND NO TIME TO LOSE.",
         steps=[go("stop one", car="any", secs=50, hint="STOP 1 OF 3", need="GET A CAR"),
                go("stop two", car="any", secs=26, hint="STOP 2 OF 3", need="GET A CAR"),
                go("stop three", car="any", secs=34, hint="STOP 3 OF 3", need="GET A CAR")]),
    dict(name="VAN ORDER", phone=1, pay=400,
         text="I HAVE A BUYER FOR A VAN. HE WAITS AT THE DOCKS, ACROSS THE NORTH BRIDGE. FIND ONE "
              "AND TAKE IT THERE.",
         steps=[go("north docks", car="van", stop=True, secs=240, hint="TO THE DOCKS", need="GET A VAN")]),
    dict(name="BLACK AND WHITE", phone=1, pay=800,
         text="THIS ONE PAYS: A POLICE CAR. THEY ONLY COME WHEN THERE IS TROUBLE, SO MAKE SOME. "
              "BRING IT TO THE DOCKS.",
         steps=[go("docks", car="police", stop=True, secs=300, hint="TO THE DOCKS", need="A POLICE CAR")]),
    dict(name="TWO BIRDS", phone=1, pay=700,
         text="TWO OF MY DRIVERS SOLD ME OUT. ONE HANGS ABOUT AT THE PARK, ONE DOWNTOWN. "
              "THEY KNOW YOUR FACE, SO BE QUICK.",
         steps=[hit("park", "grey", secs=90, hint="THE FIRST"),
                hit("downtown", "dark", secs=120, hint="THE SECOND"),
                lose(secs=150, hint="LOSE THEM")]),

    dict(name="GETAWAY", phone=2, pay=1000,
         text="THE CAPTAIN HERE. MY BOYS ARE DONE AT THE BANK DOWNTOWN. PICK THEM UP, LOSE THE "
              "POLICE, BRING THEM TO THE DOCKS.",
         steps=[go("bank", car="any", stop=True, secs=180, hint="TO THE BANK", need="GET A CAR"),
                lose(secs=180, stars=2, hint="LOSE THEM"),
                go("docks", car="any", stop=True, secs=180, hint="TO THE DOCKS", need="GET A CAR")]),
    dict(name="COP OUT", phone=2, pay=1200,
         text="THE POLICE HAS BEEN ASKING QUESTIONS ON MY DOCKS. THREE OFFICERS SHOULD NOT ASK ANY "
              "MORE. THEN GET LOST.",
         steps=[kill(3, cops=True, secs=240, hint="OFFICERS:"),
                lose(secs=240, hint="LOSE THEM")]),
    dict(name="RUSH HOUR", phone=2, pay=1500,
         text="20 PEOPLE IN 90 SECONDS. DO NOT ASK WHY. IF YOU ARE SMART YOU USE A CAR.",
         steps=[kill(20, secs=90, hint="TO GO:")]),
    dict(name="THE BIG ONE", phone=2, pay=3000,
         text="ONE LAST JOB, THEN I RETIRE. TAKE A SPORTS CAR TO THE NORTH PLAZA, HIT THE JUDGE, "
              "LOSE THE POLICE AND COME HOME.",
         steps=[go("north plaza", car="sports", secs=240, hint="TO THE PLAZA", need="SPORTS CAR!"),
                hit("judge", "dark", secs=120, hint="THE JUDGE"),
                lose(secs=240, stars=3, hint="LOSE THEM"),
                go("docks", secs=240, hint="COME HOME")]),
]

# ---------------------------------------------------------------- the city
GRASS, PAVE, ROAD, WATER, PLAZA, SAND, LOT = range(7)


def spot_hash(cx, cy):
    """The program's own (game.h): which cells hold a parked car."""
    h = (cx * 0x9E37 + cy * 0x79B9) & 0xFFFF
    h ^= h >> 7
    h = (h * 0x2545) & 0xFFFF
    h ^= h >> 9
    return h & 0xFF


class City:
    def __init__(self, city):
        self.cells = city["cells"]
        self.taken = set((int(x), int(y)) for x, y in city["trees"] + city["lamps"])

    def at(self, x, y):
        return self.cells[y * 256 + x] if 0 <= x < 256 and 0 <= y < 256 else 0xFF

    def kind(self, x, y):
        b = self.at(x, y)
        return -1 if b & 0x80 else b >> 4

    def lane(self, x, y):
        """a street, but not where two of them cross"""
        b = self.at(x, y)
        return self.kind(x, y) == ROAD and (b & 3) not in (0, 3)

    def parked(self, x, y):
        """does the city park a car in this cell? (game.h, parked_here)"""
        k = self.kind(x, y)
        h = spot_hash(x, y)
        if k == LOT:
            return (h & 3) == 0
        if k != PAVE:
            return False
        return (h & 3) == 0 and ((x ^ y) & 1) == 0 and (self.at(x, y) & 15) in (1, 2, 4, 8)

    def quiet(self, x, y):
        """pavement along one street, with a wall behind it, and with no tree,
        no lamp and no parked car on it or next to it: a place for a
        telephone box"""
        if self.kind(x, y) != PAVE or (self.at(x, y) & 15) not in (1, 2, 4, 8):
            return False
        around = [(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
        return not any(c in self.taken or self.parked(*c) for c in around)

    def box(self, x, y):
        """where in its cell a telephone box stands: on the side away from the
        street, in quarters of a cell (0 to 3)"""
        streets = self.at(x, y) & 15
        return (3 if streets & 8 else 0 if streets & 2 else 2,
                3 if streets & 1 else 0 if streets & 4 else 2)

    def walk(self, x, y):
        return self.kind(x, y) in (PAVE, PLAZA) and (x, y) not in self.taken

    def near(self, want, fits):
        x0, y0 = want
        best = None
        for y in range(max(2, y0 - 12), min(254, y0 + 13)):
            for x in range(max(2, x0 - 12), min(254, x0 + 13)):
                if fits(x, y):
                    d = abs(x - x0) + abs(y - y0)
                    if best is None or d < best[0]:
                        best = (d, x, y)
        if best is None:
            raise SystemExit("missions: nothing fits near %d, %d" % want)
        return best[1], best[2]

    def place(self, name):
        how, want = PLACES[name]
        return self.near(want, self.lane if how == "street" else self.walk)

    def way(self, a, b):
        """how many cells it is from a to b for somebody who keeps to streets
        and pavements (bridges and all)"""
        def open_(x, y):
            return self.kind(x, y) in (ROAD, PAVE, PLAZA, LOT)
        seen = {a: 0}
        edge = [a]
        while edge:
            nxt = []
            for x, y in edge:
                if abs(x - b[0]) + abs(y - b[1]) <= 1:
                    return seen[(x, y)] + 1
                for c in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if c not in seen and open_(*c):
                        seen[c] = seen[(x, y)] + 1
                        nxt.append(c)
            edge = nxt
        return -1


# ---------------------------------------------------------------- packing
def glyphs(text, order, n, what):
    if len(text) > n:
        raise SystemExit("missions: %s is %d signs long, %d fit: %r" % (what, len(text), n, text))
    out = bytearray()
    for ch in text.ljust(n):
        if ch not in order:
            raise SystemExit("missions: the lettering has no %r (%s: %r)" % (ch, what, text))
        out.append(order.index(ch))
    return bytes(out)


def wrap(text, n, lines, what):
    out, line = [], ""
    for word in text.split():
        if len(word) > n:
            raise SystemExit("missions: %r is longer than a line (%s)" % (word, what))
        if len(line) + (1 if line else 0) + len(word) > n:
            out.append(line)
            line = word
        else:
            line = (line + " " + word) if line else word
    if line:
        out.append(line)
    if len(out) > lines:
        raise SystemExit("missions: the text of %s takes %d lines, %d fit:\n  %s" % (what, len(out), lines, "\n  ".join(out)))
    return out + [""] * (lines - len(out))


def build(city, order):
    """-> (what goes on the flash chip, where the telephones are, a list of
    lines that say how the missions came out)"""
    town = City(city)
    phones = []
    said = []
    for who, want in PHONES:
        x, y = town.near(want, town.quiet)
        sx, sy = town.box(x, y)
        # (the middle of a quarter of a cell: where the program puts what stands about)
        phones.append((x + (sx + 0.5) / 4.0, y + (sy + 0.5) / 4.0))
        said.append("telephone %-12s at %.3f, %.3f" % (who, phones[-1][0], phones[-1][1]))
    blob = bytearray()
    # every telephone offers its own missions in the order of the list, and
    # what is kept is how many of them are done: they have to stand together
    whose = [m["phone"] for m in MISSIONS]
    assert whose == sorted(whose), "the missions of a telephone have to stand together, in the order of the telephones"
    first = [whose.index(p) if p in whose else len(whose) for p in range(len(PHONES))] + [len(whose)]
    for p in range(len(PHONES)):
        if p not in whose:
            first[p] = first[p + 1]
    for k, m in enumerate(MISSIONS):
        rec = bytearray(JOB_BYTES)
        assert m["pay"] % PAY_UNIT == 0 and m["pay"] // PAY_UNIT < 256
        rec[0] = m["phone"]
        rec[1] = m["pay"] // PAY_UNIT
        head = m["name"]
        pay = "$%d" % m["pay"]
        # (four lines of text: the fifth would stand right on top of what the buttons do)
        lines = [head + " " * (LINE - len(head) - len(pay)) + pay] + wrap(m["text"], LINE, LINES - 2, m["name"]) + [""]
        for i, text in enumerate(lines):
            rec[JOB_TEXT + i * LINE:JOB_TEXT + (i + 1) * LINE] = glyphs(text, order, LINE, m["name"])
        steps = m["steps"]
        if len(steps) > MAX_STEPS:
            raise SystemExit("missions: %s has %d steps, %d fit" % (m["name"], len(steps), MAX_STEPS))
        if not steps[0].get("secs"):
            raise SystemExit("missions: %s has no clock: it would never end" % m["name"])
        said.append("%2d %-16s $%-5d %s" % (k, m["name"], m["pay"], PHONES[m["phone"]][0]))
        here = tuple(int(v) for v in phones[m["phone"]])
        for i, s in enumerate(steps):
            at = JOB_STEPS + i * STEP_BYTES
            x = y = 0
            if "to" in s:
                x, y = town.place(s["to"])
            secs = s.get("secs", 0)
            clock = int(round(secs / CLOCK))
            assert clock < 256, "the clock goes up to %d seconds" % int(255 * CLOCK)
            stars = s.get("stars", 0)
            record = ((1 << stars) - 1) << 3           # what it takes for so many (game.h, stars_update)
            rec[at:at + 8] = bytes([s["op"], x, y, s.get("n", 0), clock, record, s.get("who", 0), 0])
            hint = s.get("hint", "")
            if s["op"] & STEP_COUNT:
                # the program writes how many are still to go into the last two places
                hint = glyphs(hint, order, HINT - 3, m["name"]) and hint.rjust(HINT - 3)
            rec[at + 8:at + 8 + HINT] = glyphs(hint, order, HINT, m["name"])
            rec[at + 8 + HINT:at + 8 + 2 * HINT] = glyphs(s.get("need", s.get("hint", "")), order, HINT, m["name"])
            what = {STEP_GO: "go", STEP_KILL: "kill", STEP_LOSE: "lose the police"}[s["op"] & 3]
            line = "     %d. %-16s" % (i + 1, what + (" %d" % s["n"] if (s["op"] & 3) == STEP_KILL else ""))
            if "to" in s:
                far = town.way(here, (x, y))
                line += " %-20s %3d, %3d  %3d cells by the streets" % (s["to"], x, y, far)
                if secs:
                    line += ", %.1f a second" % (far / float(secs))
                here = (x, y)
            if secs:
                line += "  %d s" % secs
            said.append(line)
        blob += rec
    return bytes(blob), phones, first, said


def main():
    sys.path.insert(0, HERE)
    import build_assets
    with open(os.path.join(ROOT, "build", os.environ.get("OUT") or "game", "city.pkl"), "rb") as f:
        city = pickle.load(f)
    blob, phones, first, said = build(city, build_assets.FONT_ORDER)
    print("\n".join(said))
    print("%d missions, %d bytes on the flash chip" % (len(MISSIONS), len(blob)))


if __name__ == "__main__":
    main()
