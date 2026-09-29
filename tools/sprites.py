#!/usr/bin/env python3
"""
Sprite pre-renderer: tiny 3D models -> 4-level sprites at every angle and size.

This is the "Donkey Kong Country trick": the Arduboy never draws a 3D car.
Everything is rendered here, offline, then stored on the 16 MB flash chip at
every rotation and every size the game can need, so the console only copies.
"""
import math, os
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
MASTER_PPM = 40          # master render resolution, pixels per metre
LIGHT = (-0.45, 0.80, -0.40)     # (right, up, forward) in camera space
_n = math.sqrt(sum(c * c for c in LIGHT))
LIGHT = tuple(c / _n for c in LIGHT)


def box(x0, x1, y0, y1, z0, z1, alb, top=None, emit=False, bias=0.0):
    """Axis-aligned box as 5 quads (no bottom). Vertices CCW seen from outside."""
    t = alb if top is None else top
    f = []
    f.append(([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], t, emit, bias))      # top
    f.append(([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], alb, emit, bias))    # front +x
    f.append(([(x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)], alb, emit, bias))    # rear -x
    f.append(([(x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)], alb, emit, bias))    # left +y
    f.append(([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], alb, emit, bias))    # right -y
    return f


def frustum(bx0, bx1, by, bz, tx0, tx1, ty, tz, side, top, front=None, rear=None):
    """Cabin: rectangle (bx0..bx1, +-by) at height bz up to (tx0..tx1, +-ty) at tz."""
    front = side if front is None else front
    rear = side if rear is None else rear
    f = []
    f.append(([(tx0, -ty, tz), (tx1, -ty, tz), (tx1, ty, tz), (tx0, ty, tz)], top, False, 0.0))
    f.append(([(bx1, -by, bz), (bx1, by, bz), (tx1, ty, tz), (tx1, -ty, tz)], front, False, 0.0))
    f.append(([(bx0, by, bz), (bx0, -by, bz), (tx0, -ty, tz), (tx0, ty, tz)], rear, False, 0.0))
    f.append(([(bx1, by, bz), (bx0, by, bz), (tx0, ty, tz), (tx1, ty, tz)], side, False, 0.0))
    f.append(([(bx0, -by, bz), (bx1, -by, bz), (tx1, -ty, tz), (tx0, -ty, tz)], side, False, 0.0))
    return f


def quad_x(x, y0, y1, z0, z1, alb, emit=True, facing=1):
    """Decal on a face of constant x (lights, plates)."""
    if facing > 0:
        v = [(x, y0, z0), (x, y1, z0), (x, y1, z1), (x, y0, z1)]
    else:
        v = [(x, y1, z0), (x, y0, z0), (x, y0, z1), (x, y1, z1)]
    return [(v, alb, emit, 0.06)]


def quad_y(y, x0, x1, z0, z1, alb, emit=False, facing=1):
    """Decal on a face of constant y (door panels, stripes)."""
    if facing > 0:
        v = [(x1, y, z0), (x0, y, z0), (x0, y, z1), (x1, y, z1)]
    else:
        v = [(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)]
    return [(v, alb, emit, 0.06)]


def wheels(xs, y, r=0.31, w=0.24):
    """Only a wheel's outer face can sit on top of the bodywork; the rest hides under it."""
    f = []
    for xc in xs:
        for s in (-1, 1):
            y0, y1 = (y - w, y + 0.05) if s > 0 else (-y - 0.05, -y + w)
            tag = "L" if s > 0 else "R"
            faces = box(xc - r, xc + r, y0, y1, 0.0, 2 * r, 0.04)
            outer = 3 if s > 0 else 4
            for k, face in enumerate(faces):
                f.append(face + ((tag if k == outer else "U"),))
            yy = y1 if s > 0 else y0
            for face in quad_y(yy, xc - 0.13, xc + 0.13, r - 0.13, r + 0.13, 0.55, facing=s):
                f.append(face + (tag,))
    return f


def car(kind="sedan", body=0.6, frame=0):
    f = []
    if kind == "van":
        f += wheels((-1.45, 1.45), 0.92)
        f += box(-2.35, 2.35, -0.95, 0.95, 0.28, 1.05, body)
        f += frustum(-2.35, 1.55, 0.95, 1.05, -2.30, 1.05, 0.88, 1.98, body, body, front=0.10, rear=body)
        f += quad_y(0.93, 0.35, 1.25, 1.15, 1.80, 0.10, facing=1)
        f += quad_y(-0.93, 0.35, 1.25, 1.15, 1.80, 0.10, facing=-1)
        f += quad_x(-2.36, -0.80, 0.80, 0.30, 0.46, 0.15, emit=False, facing=-1)
        f += quad_x(-2.36, 0.55, 0.85, 0.70, 0.95, 1.0, facing=-1)
        f += quad_x(-2.36, -0.85, -0.55, 0.70, 0.95, 1.0, facing=-1)
        f += quad_x(2.36, 0.50, 0.85, 0.62, 0.86, 1.0, facing=1)
        f += quad_x(2.36, -0.85, -0.50, 0.62, 0.86, 1.0, facing=1)
        return f
    low = kind == "sports"
    zb0, zb1 = (0.17, 0.66) if low else (0.22, 0.80)
    ztop = 1.10 if low else 1.36
    ln = 2.20 if low else 2.15
    f += wheels((-1.32, 1.36), 0.84)
    f += box(-ln, ln, -0.88, 0.88, zb0, zb1, body)
    glass = 0.07
    if low:
        f += frustum(-1.25, 0.55, 0.80, zb1, -0.85, 0.05, 0.62, ztop, glass, body)
    else:
        # a police car is black and white: white roof, white doors
        f += frustum(-1.40, 0.90, 0.82, zb1, -0.98, 0.38, 0.68, ztop, glass, 0.97 if kind == "police" else body)
    # bumpers
    f += quad_x(-ln - 0.01, -0.86, 0.86, zb0, zb0 + 0.17, 0.12, emit=False, facing=-1)
    f += quad_x(ln + 0.01, -0.86, 0.86, zb0, zb0 + 0.17, 0.12, emit=False, facing=1)
    # tail lights / head lights
    zl = zb1 - 0.24
    f += quad_x(-ln - 0.02, 0.42, 0.84, zl, zl + 0.17, 1.0, facing=-1)
    f += quad_x(-ln - 0.02, -0.84, -0.42, zl, zl + 0.17, 1.0, facing=-1)
    f += quad_x(ln + 0.02, 0.46, 0.84, zl - 0.02, zl + 0.17, 1.0, facing=1)
    f += quad_x(ln + 0.02, -0.84, -0.46, zl - 0.02, zl + 0.17, 1.0, facing=1)
    f += quad_x(-ln - 0.03, -0.22, 0.22, zb0 + 0.20, zb0 + 0.34, 0.75, emit=False, facing=-1)
    if kind == "police":
        for s in (1, -1):
            f += quad_y(0.885 * s, -0.95, 0.75, zb0 + 0.06, zb1 - 0.03, 0.97, facing=s)
        a, b = (1.0, 0.10) if frame == 0 else (0.10, 1.0)
        f += box(-0.50, -0.22, 0.04, 0.56, ztop, ztop + 0.15, a, emit=True)
        f += box(-0.50, -0.22, -0.56, -0.04, ztop, ztop + 0.15, b, emit=True)
    if kind == "taxi":
        f += box(-0.45, -0.10, -0.26, 0.26, ztop, ztop + 0.17, 1.0, emit=True)
        for s in (1, -1):
            f += quad_y(0.885 * s, -1.9, 1.9, zb0 + 0.22, zb0 + 0.33, 0.08, facing=s)
    return f


def limb(x_top, x_low, y0, y1, z_low, z_top, alb, half=0.09):
    """A leg or an arm: a box whose lower end may be further ahead (+x) or
    further back than its upper end."""
    a0, a1 = x_low - half, x_low + half
    b0, b1 = x_top - half, x_top + half
    f = []
    f.append(([(b0, y0, z_top), (b1, y0, z_top), (b1, y1, z_top), (b0, y1, z_top)], alb, False, 0.0))   # top
    f.append(([(a1, y0, z_low), (a1, y1, z_low), (b1, y1, z_top), (b1, y0, z_top)], alb, False, 0.0))   # front
    f.append(([(a0, y1, z_low), (a0, y0, z_low), (b0, y0, z_top), (b0, y1, z_top)], alb, False, 0.0))   # rear
    f.append(([(a1, y1, z_low), (a0, y1, z_low), (b0, y1, z_top), (b1, y1, z_top)], alb, False, 0.0))   # left
    f.append(([(a0, y0, z_low), (a1, y0, z_low), (b1, y0, z_top), (b0, y0, z_top)], alb, False, 0.0))   # right
    return f


# The walk, four frames: a foot set down ahead, the other leg swinging past,
# the other foot set down ahead, the first leg swinging past. Bigger than
# life, all of it: at a dozen dots to the metre nothing else shows. And made
# to show from behind, which is how the player sees their own figure: a leg
# that swings forward is a leg that gets shorter, the body goes up and down a
# row, and the arms end higher or lower.
STRIDE = 0.32            # how far ahead of the hip a foot is set down, and how far behind it leaves
LIFT = 0.24              # how far the swinging foot comes off the ground
KNEE = (0.24, 0.50)      # the knee of the swinging leg: ahead of the hip, above the ground
DIP = 0.08               # how much lower the body is with both feet down
DOWN, BACK, PAST = (STRIDE, 0.0, None), (-STRIDE, 0.05, None), (0.02, LIFT, KNEE)
UNDER = (0.0, 0.0, None)
#        left foot, right foot (ahead, up, knee); left hand, right hand (ahead, up); body
WALK = ((DOWN, BACK, (-0.22, 0.10), (0.26, 0.18), -DIP),
        (UNDER, PAST, (0.0, 0.0), (0.0, 0.0), 0.0),
        (BACK, DOWN, (0.26, 0.18), (-0.22, 0.10), -DIP),
        (PAST, UNDER, (0.0, 0.0), (0.0, 0.0), 0.0))
STAND = (UNDER, UNDER, (0.0, 0.0), (0.0, 0.0), 0.0)


def leg(foot, y0, y1, hip, alb):
    ahead, up, knee = foot
    if knee is None:
        return limb(0.0, ahead, y0, y1, up, hip, alb)
    return limb(0.0, knee[0], y0, y1, knee[1], hip, alb) + limb(knee[0], ahead, y0, y1, up, knee[1], alb)


def person(shirt=0.5, frame=None, pants=0.12, hair=0.10, gun=None, hand=1, cap=False):
    """Walks towards +x; the left side is +y. The back of the head is hair, so
    front and back differ. frame: 0..3 of the walk, None for standing still.
    gun: None, "aim" (arm stretched out with a pistol) or "fire" (the same with
    the flash at the muzzle); hand: 1 for the right hand, -1 for the left;
    cap: a police officer's, white."""
    left, right, left_hand, right_hand, up = STAND if frame is None else WALK[frame % 4]
    hip = 0.86 + up
    # Two legs, from wherever they are seen: a column apart at the player's
    # size, with the dark between them that there is between legs, and one
    # leg a shade lighter than the other.
    other = pants + 0.40 if pants < 0.5 else pants - 0.30
    f = []
    f += leg(left, 0.09, 0.26, hip, pants)
    f += leg(right, -0.26, -0.09, hip, other)
    f += box(-0.03, 0.03, -0.09, 0.09, max(left[1], right[1]), hip, 0.0)
    f += box(-0.13, 0.13, -0.25, 0.25, hip, hip + 0.60, shirt)
    arms = [(left_hand, 0.25, 0.37), (right_hand, -0.37, -0.25)]
    if gun:
        def side(x0, x1, y0, y1, z0, z1, alb, **kw):
            # y0..y1 is given for the right hand (negative y)
            if hand > 0:
                return box(x0, x1, y0, y1, z0, z1, alb, **kw)
            return box(x0, x1, -y1, -y0, z0, z1, alb, **kw)
        del arms[1 if hand > 0 else 0]
        # held well away from the body, so that it shows from behind too
        f += side(-0.06, 0.74, -0.50, -0.35, 1.24, 1.42, shirt * 0.85)
        f += side(0.70, 1.06, -0.49, -0.36, 1.30, 1.52, 0.05)
        if gun == "fire":
            # the flash: a star, big enough to show but not to hide what is shot at
            f += side(1.10, 1.40, -0.76, -0.10, 1.32, 1.52, 1.0, emit=True)
            f += side(1.10, 1.40, -0.53, -0.33, 1.08, 1.76, 1.0, emit=True)
            f += side(1.06, 1.50, -0.61, -0.25, 1.24, 1.60, 1.0, emit=True)
    for (ahead, raised), y0, y1 in arms:
        f += limb(0.0, ahead, y0, y1, hip - 0.02 + raised, hip + 0.56, shirt * 0.85, half=0.08)
    head = box(-0.12, 0.12, -0.12, 0.12, hip + 0.64, hip + 0.90, 0.88, top=hair)
    head[2] = (head[2][0], hair) + head[2][2:]        # rear face
    f += head
    if cap:
        f += box(-0.17, 0.26, -0.18, 0.18, hip + 0.82, hip + 0.94, 0.95)
        f += box(-0.15, 0.15, -0.16, 0.16, hip + 0.94, hip + 1.08, 0.95)
    return f


def person_down(shirt=0.5, pants=0.12, cap=False):
    """Someone lying flat on the ground, head towards +x."""
    f = []
    f += box(-0.90, -0.04, 0.03, 0.21, 0.0, 0.20, pants)
    f += box(-0.90, -0.04, -0.21, -0.03, 0.0, 0.20, pants)
    f += box(-0.04, 0.56, -0.25, 0.25, 0.0, 0.26, shirt)
    f += box(0.00, 0.54, 0.25, 0.36, 0.0, 0.16, shirt * 0.85)
    f += box(0.00, 0.54, -0.36, -0.25, 0.0, 0.16, shirt * 0.85)
    f += box(0.60, 0.86, -0.12, 0.12, 0.0, 0.24, 0.88)
    if cap:
        f += box(0.95, 1.25, -0.16, 0.16, 0.0, 0.14, 0.95)       # the cap has come off
    return f


LETTERS = {
    "W": ["#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"],
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
    "D": ["####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."],
    "B": ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
    "U": ["#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "M": ["#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"],
    "I": [".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "O": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "N": ["#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"],
    "P": ["####.", "#...#", "#...#", "####.", "#....", "#....", "#...."],
    "F": ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
    "L": ["#....", "#....", "#....", "#....", "#....", "#....", "#####"],
}


def lettering(text, small=()):
    """A word across the picture, white on a black board: levels per dot of
    the 3D view (whose dots are twice as wide as high), -1 for nothing.
    Returns (rows, width, height). With more than one word, one goes under
    the other, each in the middle of the board. small: the lines (by their
    number) whose letters are half as high."""
    lines = text.split()
    wide = max(len(t) for t in lines) * 6 - 1 + 4
    tall = [1 if k in small else 2 for k in range(len(lines))]
    high = sum(7 * t for t in tall) + 3 * (len(lines) - 1) + 6
    rows = [[0] * wide for _ in range(high)]
    top = 3
    for t, word in zip(tall, lines):
        left = (wide - (len(word) * 6 - 1)) // 2
        for i, ch in enumerate(word):
            for r, line in enumerate(LETTERS[ch]):
                for c, dot in enumerate(line):
                    if dot == "#":
                        for k in range(t):
                            rows[top + t * r + k][left + i * 6 + c] = 3
        top += 7 * t + 3
    return rows, wide, high


def spark():
    """Where a bullet strikes: a bright cross at chest height, facing the camera.
    Bigger than life: it has to show from far away."""
    f = box(-0.05, 0.05, -0.80, 0.80, 0.95, 1.45, 1.0, emit=True)
    f += box(-0.05, 0.05, -0.25, 0.25, 0.40, 2.00, 1.0, emit=True)
    return f


def tracer():
    """A piece of the bullet's trail, at the height of the pistol."""
    return box(-0.20, 0.20, -0.20, 0.20, 1.22, 1.50, 1.0, emit=True)


def sign(rows, dot, z0):
    """Letters and signs that hang in the air, facing the camera: one bright
    box per dot. rows: text lines, '#' for a dot; dot: its size in metres;
    z0: how high the lowest row hangs."""
    f = []
    wide = len(rows[0])
    for r, row in enumerate(rows):
        z = z0 + (len(rows) - 1 - r) * dot
        c = 0
        while c < wide:
            if row[c] != "#":
                c += 1
                continue
            e = c
            while e < wide and row[e] == "#":
                e += 1
            # the camera's right is the model's -y
            y0 = (wide / 2.0 - e) * dot
            y1 = (wide / 2.0 - c) * dot
            f += box(-0.04, 0.04, y0, y1, z, z + dot, 1.0, emit=True)
            c = e
    return f


def cash(lift=0.0):
    """What somebody who went down was carrying: a dollar sign in the air over
    them, above head height so that the player's own figure does not hide it.
    Bigger than life, like everything that has to be found from across the
    street."""
    return sign(["...##..",
                 ".######",
                 "##.##..",
                 "##.##..",
                 ".#####.",
                 "..##.##",
                 "..##.##",
                 "######.",
                 "..##..."], 0.20, 1.50 + lift)


def mark(lift=0.0):
    """What a mission is about has this hanging over it: an arrow that points
    down, to the telephone that rings, to the place to go to, to whoever it
    is about. High enough to clear a telephone box."""
    return sign(["#######",
                 "#######",
                 ".#####.",
                 ".#####.",
                 "..###..",
                 "..###..",
                 "...#..."], 0.24, 2.85 + lift)


def phone():
    """A telephone box: light, so that it shows against a wall, with dark
    glass all round and a lit sign along the top."""
    f = box(-0.46, 0.46, -0.46, 0.46, 0.0, 2.10, 0.80, emit=True)
    for s in (1, -1):
        f += quad_y(0.47 * s, -0.32, 0.32, 0.62, 1.88, 0.05, facing=s)
        f += quad_x(0.47 * s, -0.32, 0.32, 0.62, 1.88, 0.05, emit=False, facing=s)
    f += box(-0.54, 0.54, -0.54, 0.54, 2.10, 2.20, 0.05)
    f += box(-0.54, 0.54, -0.54, 0.54, 2.20, 2.55, 1.0, top=0.40, emit=True)
    return f


def tree():
    f = box(-0.28, 0.28, -0.28, 0.28, 0.0, 2.4, 0.10)
    rings = ((2.0, 0.9), (2.9, 1.9), (4.0, 2.2), (5.1, 1.8), (6.0, 1.0), (6.5, 0.3))
    n = 8
    for (z0, r0), (z1, r1) in zip(rings, rings[1:]):
        for k in range(n):
            a0 = 2 * math.pi * k / n
            a1 = 2 * math.pi * (k + 1) / n
            v = [(r0 * math.cos(a0), r0 * math.sin(a0), z0), (r0 * math.cos(a1), r0 * math.sin(a1), z0),
                 (r1 * math.cos(a1), r1 * math.sin(a1), z1), (r1 * math.cos(a0), r1 * math.sin(a0), z1)]
            f.append((v, 0.30, False, 0.0))
    return f


def lamp(lit=True):
    f = box(-0.13, 0.13, -0.13, 0.13, 0.0, 6.2, 0.35)
    f += box(-0.13, 1.30, -0.09, 0.09, 6.2, 6.40, 0.35)
    f += box(0.75, 1.45, -0.20, 0.20, 5.98, 6.20, 1.0 if lit else 0.6, emit=lit)
    return f


def render(faces, yaw, elev_deg=6.0, ppm=MASTER_PPM, ss=3):
    """Painter's-algorithm render. Returns (lum 'L' image, alpha 'L' image, (ox, oy))
    where (ox, oy) is the pixel position of the model origin on the ground."""
    cy, sy = math.cos(yaw), math.sin(yaw)
    el = math.radians(elev_deg)
    ce, se = math.cos(el), math.sin(el)
    out = []
    minx = miny = 1e9
    maxx = maxy = -1e9
    near = "L" if sy > 0 else "R"
    for face in faces:
        verts, alb, emit, bias = face[:4]
        tag = face[4] if len(face) > 4 else None
        if tag is not None:
            # far-side wheels go under the body, near-side wheels on top of it
            bias = bias + (4.0 if (tag == near and abs(sy) > 0.25) else -4.0)
        cam = []
        for (x, y, z) in verts:
            fx = x * cy - y * sy          # forward (into screen)
            rx = -(x * sy + y * cy)       # right
            cam.append((rx, fx * se + z * ce, fx * ce - z * se))   # right, up, depth
        ax, ay, az = (cam[1][k] - cam[0][k] for k in range(3))
        bx, by, bz = (cam[2][k] - cam[0][k] for k in range(3))
        nx, ny, nz = ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx
        ln = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        nx, ny, nz = nx / ln, ny / ln, nz / ln
        # right-handed (right, up, depth-into-screen) is left-handed on screen, so flip
        nx, ny, nz = -nx, -ny, -nz
        if nz >= -1e-6:                   # facing away from the viewer
            continue
        if emit:
            lum = alb
        else:
            d = nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2]
            lum = alb * (0.50 + 0.62 * max(0.0, d))
        depth = sum(c[2] for c in cam) / len(cam) - bias
        out.append((depth, [(c[0], c[1]) for c in cam], min(1.0, lum)))
        for c in cam:
            minx, maxx = min(minx, c[0]), max(maxx, c[0])
            miny, maxy = min(miny, c[1]), max(maxy, c[1])
    out.sort(key=lambda t: -t[0])
    pad = 0.05
    minx -= pad
    maxx += pad
    maxy += pad
    miny = min(miny, 0.0) - pad
    wpx = int(math.ceil((maxx - minx) * ppm))
    hpx = int(math.ceil((maxy - miny) * ppm))
    lum = Image.new("L", (wpx * ss, hpx * ss), 0)
    alp = Image.new("L", (wpx * ss, hpx * ss), 0)
    dl, da = ImageDraw.Draw(lum), ImageDraw.Draw(alp)
    for depth, pts, l in out:
        p = [((x - minx) * ppm * ss, (maxy - y) * ppm * ss) for (x, y) in pts]
        dl.polygon(p, fill=int(l * 255))
        da.polygon(p, fill=255)
    lum = lum.resize((wpx, hpx), Image.BOX)
    alp = alp.resize((wpx, hpx), Image.BOX)
    return lum, alp, ((0.0 - minx) * ppm, (maxy - 0.0) * ppm)


def quantize(v):
    """Luminance 0..255 -> display level 0..3."""
    return 0 if v < 44 else (1 if v < 112 else (2 if v < 196 else 3))


class Sprite:
    """One master render plus a cache of pre-scaled 4-level versions."""

    def __init__(self, faces, yaw, elev=6.0, outline=None):
        self.lum, self.alp, (self.ox, self.oy) = render(faces, yaw, elev)
        self.cache = {}
        if outline:
            self.outline = outline

    # a dark keyline goes around sprites at least this many columns and rows big
    outline = (5, 5)

    def scaled(self, ppm_y):
        """ppm_y: display pixels per metre vertically. Columns are 2 px wide."""
        key = int(round(math.log(max(0.5, ppm_y)) / math.log(2.0) * 6.0))     # 6 sizes per octave
        if key in self.cache:
            return self.cache[key]
        s = 2.0 ** (key / 6.0)
        w = max(1, int(round(self.lum.width * s / MASTER_PPM / 2.0)))
        h = max(1, int(round(self.lum.height * s / MASTER_PPM)))
        # premultiplied area average, so edges do not darken
        pre = Image.composite(self.lum, Image.new("L", self.lum.size, 0), self.alp)
        l = pre.resize((w, h), Image.BOX)
        a = self.alp.resize((w, h), Image.BOX)
        lp, ap = l.load(), a.load()
        rows = []
        for y in range(h):
            row = []
            for x in range(w):
                al = ap[x, y]
                if al < 64:
                    row.append(-1)
                else:
                    row.append(quantize(min(255, lp[x, y] * 255 // al)))
            rows.append(row)
        ox = self.ox * s / MASTER_PPM / 2.0
        oy = self.oy * s / MASTER_PPM
        if w >= self.outline[0] and h >= self.outline[1]:
            # dark keyline around the silhouette so sprites read on any background
            big = [[-1] * (w + 2) for _ in range(h + 2)]
            for y in range(h):
                for x in range(w):
                    big[y + 1][x + 1] = rows[y][x]
            out = [r[:] for r in big]
            for y in range(h + 2):
                for x in range(w + 2):
                    if big[y][x] >= 0:
                        continue
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        xx, yy = x + dx, y + dy
                        if 0 <= xx < w + 2 and 0 <= yy < h + 2 and big[yy][xx] >= 0:
                            out[y][x] = 0
                            break
            rows, w, h, ox, oy = out, w + 2, h + 2, ox + 1, oy + 1
        self.cache[key] = (rows, w, h, ox, oy)
        return self.cache[key]


class SpriteBank:
    ANGLES = 32

    def __init__(self):
        self.sets = {}

    def add(self, name, faces, elev=6.0, angles=None):
        n = self.ANGLES if angles is None else angles
        self.sets[name] = [Sprite(faces, 2 * math.pi * k / n, elev) for k in range(n)]

    def get(self, name, rel_yaw):
        s = self.sets[name]
        n = len(s)
        k = int(round(rel_yaw / (2 * math.pi) * n)) % n
        return s[k]


def build_bank():
    b = SpriteBank()
    b.add("sedan_l", car("sedan", 0.92))
    b.add("sedan_m", car("sedan", 0.50))
    b.add("sedan_d", car("sedan", 0.17))
    b.add("sports", car("sports", 0.95))
    b.add("taxi", car("taxi", 0.80))
    b.add("van", car("van", 0.62))
    b.add("police0", car("police", 0.13, 0))
    b.add("police1", car("police", 0.13, 1))
    for shirt, nm in ((0.95, "ped_a"), (0.45, "ped_b"), (0.15, "ped_c")):
        for fr in range(4):
            b.add("%s%d" % (nm, fr), person(shirt, fr), angles=8)
    b.add("tree", tree(), angles=1)
    b.add("lamp", lamp(True), angles=8)
    # the player's own car, seen from the chase camera (steeper angle)
    b.add("hero", car("sports", 0.95), elev=13.0, angles=64)
    return b


if __name__ == "__main__":
    bank = build_bank()
    sheet = Image.new("RGB", (1560, 760), (60, 60, 90))
    pal = [(0, 0, 0), (156, 156, 156), (215, 215, 215), (255, 255, 255)]

    def blit(spr, ppm, x0, y0, zoom=3):
        rows, w, h, ox, oy = spr.scaled(ppm)
        for y in range(h):
            for x in range(w):
                v = rows[y][x]
                if v >= 0:
                    for dy in range(zoom):
                        for dx in range(zoom * 2):
                            px_, py_ = x0 + x * zoom * 2 + dx, y0 + y * zoom + dy
                            if px_ < sheet.width and py_ < sheet.height:
                                sheet.putpixel((px_, py_), pal[v])
        return w * zoom * 2, h * zoom

    y = 10
    for name in ("sedan_l", "sedan_d", "sports", "taxi", "van", "police0"):
        x = 10
        for k in range(0, 32, 4):
            w, h = blit(bank.sets[name][k], 14.0, x, y)
            x += 192
        y += 80
    x = 10
    for k in range(8):
        blit(bank.sets["ped_a%d" % (k % 4)][k], 14.0, x, y)
        blit(bank.sets["ped_c%d" % (k % 4)][(k + 2) % 8], 14.0, x + 50, y)
        x += 110
    blit(bank.sets["tree"][0], 9.0, 900, y - 60)
    blit(bank.sets["lamp"][2], 9.0, 1080, y - 60)
    y += 100
    x = 10
    for k in (0, 2, 4, 62, 60):
        blit(bank.sets["hero"][k], 15.0, x, y)
        x += 170
    x = 10
    y += 80
    for ppm in (16, 11, 8, 5.6, 4, 2.8, 2):
        w, h = blit(bank.sets["police0"][5], ppm, x, y)
        x += w + 20
    sheet.save(os.path.join(HERE, "sprite_sheet.png"))
    print("sprite sets:", len(bank.sets))
