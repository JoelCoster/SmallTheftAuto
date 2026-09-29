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
        f += frustum(-1.40, 0.90, 0.82, zb1, -0.98, 0.38, 0.68, ztop, glass, body)
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


def person(shirt=0.5, frame=0, pants=0.12):
    sw = (0.0, 0.17, 0.0, -0.17)[frame % 4]
    f = []
    f += box(-0.10 + sw, 0.10 + sw, 0.03, 0.21, 0.0, 0.86, pants)
    f += box(-0.10 - sw, 0.10 - sw, -0.21, -0.03, 0.0, 0.86, pants)
    f += box(-0.13, 0.13, -0.25, 0.25, 0.86, 1.46, shirt)
    f += box(-0.08 - sw, 0.08 - sw, 0.25, 0.36, 0.84, 1.42, shirt * 0.85)
    f += box(-0.08 + sw, 0.08 + sw, -0.36, -0.25, 0.84, 1.42, shirt * 0.85)
    f += box(-0.12, 0.12, -0.12, 0.12, 1.50, 1.76, 0.88, top=0.10)
    return f


def tree():
    f = box(-0.18, 0.18, -0.18, 0.18, 0.0, 2.4, 0.10)
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
    f = box(-0.09, 0.09, -0.09, 0.09, 0.0, 6.2, 0.35)
    f += box(-0.09, 1.30, -0.07, 0.07, 6.2, 6.36, 0.35)
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

    def __init__(self, faces, yaw, elev=6.0):
        self.lum, self.alp, (self.ox, self.oy) = render(faces, yaw, elev)
        self.cache = {}

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
                if al < 110:
                    row.append(-1)
                else:
                    row.append(quantize(min(255, lp[x, y] * 255 // al)))
            rows.append(row)
        ox = self.ox * s / MASTER_PPM / 2.0
        oy = self.oy * s / MASTER_PPM
        if w >= 5 and h >= 5:
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
