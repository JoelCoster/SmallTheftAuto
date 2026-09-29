#!/usr/bin/env python3
"""
Small Theft Auto asset pipeline.

Generates everything the console needs that is not code:

  SmallTheftAuto/tables.h   small lookup tables compiled into the program (PROGMEM)
  SmallTheftAuto/fxdata.h   addresses of everything stored on the FX flash chip
  build/game/fxdata.bin the flash chip image (city map, props, sprites, the
                        pictures of title and map, the arrows that show the way)

Usage:  python3 tools/build_assets.py [seed]

With OUT set, the flash chip image goes to build/<OUT> instead of build/game
(what is in build/game is what the list of games on the console is made
from: it is kept for builds that are meant to go there).
"""
import math, os, struct, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import citygen as cg
import sprites as sp
import sound as snd
import arrows
import missions

SKETCH = os.path.join(ROOT, "SmallTheftAuto")
OUT = os.path.join(ROOT, "build", os.environ.get("OUT") or "game")

# ---------------------------------------------------------------- view constants
COLS, ROWS = 64, 56
HORIZON = 19
TANHALF = 0.82
FY = 64.0 / TANHALF                 # display pixels per unit of height/depth
CAM_H_M = 2.35                      # camera height, metres
CAM_BACK_M = 6.2                    # chase camera distance, metres
CELL_M = 4.0
CAM_H = int(round(CAM_H_M / CELL_M * 256))          # 8.8 cells
CAM_BACK = int(round(CAM_BACK_M / CELL_M * 256))
MAXD_CELLS = 40
SPRITE_MAXD_CELLS = 24
N_SIZES = 24
PPM0 = 16.0                          # largest pre-scaled sprite size, px per metre
# The way to go, at the top of the picture: an arrow and, next to it, how far
# it is. Where they are, in columns of the 3D view; both are in single dots,
# which is up to the display routine (display.S).
NAV_C0 = 26                          # the arrow: 6 columns from here, 16 rows
NAV_BOX_C0 = 33                      # the distance: 9 columns from here, 8 rows
NAV_BOX_COLS = 9
SAVE_BYTES = 4096                    # what the game may write to on the flash chip
# the lettering, in the order of its signs: texts on the flash chip are
# written as places in this list
FONT_ORDER = " 0123456789$ABCDEFGHIJKLMNOPQRSTUVWXYZ.-:!/>,'?+"


def c_array(name, ctype, values, per_line=12, fmt="%d"):
    out = ["extern const %s %s[%d] PROGMEM __attribute__((used));" % (ctype, name, len(values)),
           "const %s %s[%d] PROGMEM = {" % (ctype, name, len(values))]
    for i in range(0, len(values), per_line):
        out.append("  " + ", ".join(fmt % v for v in values[i:i + per_line]) + ",")
    out.append("};")
    return "\n".join(out)


# ---------------------------------------------------------------- textures
WALLS = {
    cg.S_OFFICE:    ["........", "........", ".WW..WW.", ".WW..WW.", ".WW..WW.", ".WW..WW.", "........", "........"],
    cg.S_GLASS:     ["LLLLLLLL", "WWW.WWW.", "WWW.WWW.", "WWW.WWW.", "WWW.WWW.", "WWW.WWW.", "WWW.WWW.", "........"],
    cg.S_BRICK:     ["........", "........", "..WWW...", "..WWW...", "..WWW...", ".LLLLL..", "........", "........"],
    cg.S_WAREHOUSE: ["........", "LLLLLLLL", "........", "........", "........", "........", "........", "........"],
    cg.S_HOTEL:     ["........", ".WW.WW..", ".WW.WW..", ".WW.WW..", "LLLLLLL.", "........", "........", "........"],
    cg.S_SHOPS:     ["........", "..WW....", "..WW....", "..WW....", "........", "........", "........", "........"],
    cg.S_TOWER:     ["W.WW.WW.", "W.WW.WW.", "W.WW.WW.", "W.WW.WW.", "W.WW.WW.", "W.WW.WW.", "W.WW.WW.", "........"],
    cg.S_FLATS:     ["........", ".WW.....", ".WW..WW.", ".WW..WW.", "........", "LLLLLLLL", "........", "........"],
}
GROUND_FLOOR = [
    ["LLLLLLLL", "LDLDLDLD", ".WWWWWW.", ".WWWWWW.", ".WWWWWW.", ".WWWWWW.", "........", "........"],   # 1 shop
    ["........", "..LLLL..", "..DDDD..", "..DDDD..", "..DDDD..", "..DDDD..", "..DDDD..", "..DDDD.."],   # 2 door
    ["........", "LLLLLLLL", ".DDDDDD.", ".DDDDDD.", ".DDDDDD.", ".DDDDDD.", ".DDDDDD.", ".DDDDDD."],   # 3 gate
]
CODE = {".": 0, "W": 1, "L": 2, "D": 3, "M": 0}
# which ground-floor texture a wall cell gets, by style and a 2-bit position hash (0 = same as upper floors)
GROUND_SEL = {
    cg.S_OFFICE: (0, 2, 0, 0), cg.S_GLASS: (0, 2, 0, 0), cg.S_BRICK: (1, 0, 2, 0), cg.S_WAREHOUSE: (3, 3, 0, 0),
    cg.S_HOTEL: (1, 1, 2, 1), cg.S_SHOPS: (1, 1, 1, 1), cg.S_TOWER: (0, 2, 0, 0), cg.S_FLATS: (2, 0, 0, 1),
}
# level for texel codes (wall, window, ledge, dark), for the bright (E/W) and dim (N/S) faces
WALL_PAL = {
    cg.S_OFFICE: ((2, 0, 3, 0), (1, 0, 2, 0)), cg.S_GLASS: ((1, 0, 3, 0), (0, 1, 2, 0)),
    cg.S_BRICK: ((1, 0, 2, 0), (0, 1, 1, 0)), cg.S_WAREHOUSE: ((2, 0, 1, 0), (1, 0, 0, 0)),
    cg.S_HOTEL: ((3, 0, 2, 0), (2, 0, 1, 0)), cg.S_SHOPS: ((2, 0, 3, 0), (1, 0, 2, 0)),
    cg.S_TOWER: ((3, 0, 2, 0), (2, 0, 1, 0)), cg.S_FLATS: ((2, 0, 1, 0), (1, 0, 0, 0)),
}


def tex_columns(rows):
    """8x8 character texture -> 4 bytes per texel column; each byte holds two texel rows as
    nibbles (row 2j in the low nibble, row 2j+1 in the high nibble), row 0 = top."""
    out = []
    for u in range(8):
        for j in range(4):
            out.append(CODE[rows[2 * j][u]] | (CODE[rows[2 * j + 1][u]] << 4))
    return out


# ---------------------------------------------------------------- ground tiles
ROAD_LV, MARK_LV, PAVE_LV, CURB_LV = 1, 3, 2, 0


def ground_tile(cellbyte):
    """8x8 levels for a ground cell byte (dash parity is handled by the engine)."""
    t = cellbyte >> 4
    d = cellbyte & 15
    px = [[0] * 8 for _ in range(8)]
    for v in range(8):
        for u in range(8):
            if t == cg.ROAD:
                lv = ROAD_LV
                dr, mk = d >> 2, d & 3
                if dr == cg.N_:
                    uc, vc = u, v
                elif dr == cg.S_:
                    uc, vc = 7 - u, v
                elif dr == cg.E_:
                    uc, vc = v, u
                else:
                    uc, vc = 7 - v, u
                if mk in (cg.M_CENTER, cg.M_DASH):
                    if uc == 0:
                        lv = MARK_LV
                elif mk == cg.M_CROSS:
                    if 1 <= vc <= 6 and (uc & 1) == 0:
                        lv = MARK_LV
            elif t == cg.PAVE:
                lv = PAVE_LV
                if (d & 1 and v == 0) or (d & 4 and v == 7) or (d & 2 and u == 7) or (d & 8 and u == 0):
                    lv = CURB_LV
            elif t == cg.GRASS:
                lv = 0 if (u * 5 + v * 3) % 11 == 0 else 1
            elif t == cg.WATER:
                lv = 2 if (v in (2, 6) and (u + v) % 5 < 2) else 0
            elif t == cg.PLAZA:
                lv = 3 if ((u >> 2) + (v >> 2)) & 1 else 2
            elif t == cg.LOT:
                lv = 3 if (u == 0 and 1 <= v <= 6) else 1
            elif t == cg.SAND:
                lv = 3 if (u * 3 + v * 7) % 13 == 0 else 2
            else:
                lv = 1
            px[v][u] = lv
    return px


def tile_bytes(px):
    """8x8 levels -> 16 bytes: for each texel row v, a hi-bit byte and a lo-bit byte (bit u = column u)."""
    out = []
    for v in range(8):
        hi = lo = 0
        for u in range(8):
            if px[v][u] & 2:
                hi |= 1 << u
            if px[v][u] & 1:
                lo |= 1 << u
        out += [hi, lo]
    return out


# ---------------------------------------------------------------- sky
def make_sky(pw=64, ph=24):
    import random
    rnd = random.Random(5)

    def noise(px_, py_):
        lat = [[rnd.random() for _ in range(px_)] for _ in range(py_ + 1)]
        out = []
        for v in range(ph):
            fy = v / ph * py_
            y0 = int(fy)
            ty = fy - y0
            ty = ty * ty * (3 - 2 * ty)
            row = []
            for u in range(pw):
                fx = u / pw * px_
                x0 = int(fx)
                tx = fx - x0
                tx = tx * tx * (3 - 2 * tx)
                x1 = (x0 + 1) % px_
                a = lat[y0][x0] + (lat[y0][x1] - lat[y0][x0]) * tx
                b = lat[y0 + 1][x0] + (lat[y0 + 1][x1] - lat[y0 + 1][x0]) * tx
                row.append(a + (b - a) * ty)
            out.append(row)
        return out
    n1, n2 = noise(3, 3), noise(7, 6)
    sky = []
    for v in range(ph):                       # v rows above the horizon
        row = []
        for u in range(pw):
            n = 0.6 * n1[v][u] + 0.4 * n2[v][u]
            base = 3 if v < 4 else 2
            if v >= 5 and n > 0.56:
                base = 3
            if v >= 12 and n < 0.40:
                base = 1
            row.append(base)
        sky.append(row)
    return sky


def pack_sky(sky):
    """Per panorama column: 3 hi-plane bytes then 3 lo-plane bytes, bit = screen row."""
    out = bytearray()
    pw = len(sky[0])
    for u in range(pw):
        hi = [0, 0, 0]
        lo = [0, 0, 0]
        for r in range(24):
            v = HORIZON - 1 - r
            v = 0 if v < 0 else min(len(sky) - 1, v)
            lv = sky[v][u]
            if lv & 2:
                hi[r >> 3] |= 1 << (r & 7)
            if lv & 1:
                lo[r >> 3] |= 1 << (r & 7)
        out += bytes(hi + lo)
    return bytes(out)


# ---------------------------------------------------------------- props
PROP_TREE, PROP_LAMP, PROP_PHONE = 0, 1, 2


def pack_props(city, phones=()):
    """16x16 chunks of 16x16 cells. Chunk table: 3-byte offset + 1-byte count. Prop = 3 bytes.
    phones: where the telephone boxes stand."""
    chunks = [[] for _ in range(256)]
    for kind, lst in ((PROP_TREE, city["trees"]), (PROP_LAMP, city["lamps"]), (PROP_PHONE, phones)):
        for (x, y) in lst:
            cx, cy = int(x), int(y)
            if not (0 <= cx < 256 and 0 <= cy < 256):
                continue
            sx = int((x - cx) * 4) & 3
            sy = int((y - cy) * 4) & 3
            chunks[(cy >> 4) * 16 + (cx >> 4)].append(bytes([(kind << 4) | (sx << 2) | sy, cx, cy]))
    table = bytearray()
    data = bytearray()
    most = 0
    for ch in chunks:
        ch = ch[:48]
        most = max(most, len(ch))
        table += struct.pack("<I", len(data))[:3] + bytes([len(ch)])
        for p in ch:
            data += p
    return bytes(table), bytes(data), most


# ---------------------------------------------------------------- pages
def pack_page(lit, rows):
    """A picture in black and white, 128 dots wide, the way the game's pages
    want it: column after column, (rows / 8) bytes each, the top row in bit 0
    of the first. lit(x, y) says whether a dot is on."""
    out = bytearray()
    for x in range(128):
        for b in range(rows // 8):
            v = 0
            for k in range(8):
                if lit(x, b * 8 + k):
                    v |= 1 << k
            out.append(v)
    return bytes(out)


def title_page():
    """The title picture as the game shows it, 56 rows (tools/title.py draws it,
    and next to it the one for the console's game menu, 64 rows)."""
    from PIL import Image
    img = Image.open(os.path.join(ROOT, "assets", "title_game.png")).convert("L")
    assert img.size == (128, 56), img.size
    px = img.load()
    return pack_page(lambda x, y: px[x, y] > 127, 56)


def map_page(city, preview=None):
    """The whole city, two cells to the dot: 128 x 128. Streets are lit,
    houses dark, green has a dot here and there, water a few waves."""
    cells = city["cells"]

    def kind(b):
        return cg.BUILDING if b & 0x80 else (b >> 4)

    def lit(mx, my):
        ks = [kind(cells[(2 * my + dy) * 256 + 2 * mx + dx]) for dy in (0, 1) for dx in (0, 1)]
        if ks.count(cg.ROAD) >= 2:
            return True
        if ks.count(cg.WATER) >= 3:
            return my % 4 == 1 and (mx + (my // 4) * 3) % 8 < 2
        if ks.count(cg.GRASS) + ks.count(cg.SAND) >= 2:
            return mx % 2 == 0 and my % 2 == 0
        return False
    if preview:
        from PIL import Image
        img = Image.new("L", (128, 128), 0)
        px = img.load()
        for y in range(128):
            for x in range(128):
                px[x, y] = 255 if lit(x, y) else 0
        img.resize((512, 512), Image.NEAREST).save(preview)
    return pack_page(lit, 128)


# ---------------------------------------------------------------- sprites
def pack_sprite(rows, w, h, ox, oy):
    """Column-major. Header w,h,ox,oy then per column: mask bytes, hi bytes, lo bytes (bit = row)."""
    hb = (h + 7) >> 3
    out = bytearray([w, h, int(round(ox)) & 255, int(round(oy)) & 255])
    for x in range(w):
        m = [0] * hb
        hi = [0] * hb
        lo = [0] * hb
        for y in range(h):
            v = rows[y][x]
            if v < 0:
                continue
            m[y >> 3] |= 1 << (y & 7)
            if v & 2:
                hi[y >> 3] |= 1 << (y & 7)
            if v & 1:
                lo[y >> 3] |= 1 << (y & 7)
        out += bytes(m + hi + lo)
    return bytes(out)


# car kinds, in the order the game numbers them: name, model, body brightness
CAR_KINDS = (("sedan_l", "sedan", 0.92), ("sedan_m", "sedan", 0.50), ("sedan_d", "sedan", 0.17),
             ("taxi", "taxi", 0.80), ("van", "van", 0.62), ("sports", "sports", 0.95),
             ("police", "police", 0.13))
# the last kind is the police officer
PED_KINDS = ((0.95, "ped_a"), (0.45, "ped_b"), (0.15, "ped_c"), (0.13, "cop"))


def size_ppm(k):
    return PPM0 * 2.0 ** (-k / 6.0)


def build_sprites():
    t0 = time.time()
    sets = []        # (name, angles, sizes, [sprite bytes ...] in angle-major order)

    def add(name, faces, angles, sizes, elev=6.0, outline=None, square=False):
        """square: seen from almost behind (and almost in front) is drawn as
        seen from exactly there. That is how the camera over the shoulder sees
        the player most of the time, and a figure five dots wide only comes
        out clean when it stands square to the dots."""
        blobs = []
        for a in range(angles):
            turn = a
            if square:
                for full in (0, angles // 2):
                    if (a - full) % angles in (1, angles - 1):
                        turn = full
            s = sp.Sprite(faces, 2 * math.pi * turn / angles, elev, outline)
            row = []
            for ppm in sizes:
                rows, w, h, ox, oy = s.scaled(ppm)
                # anything taller than the screen is never needed: reuse the next size down
                row.append(None if (w > 96 or h > 64) else pack_sprite(rows, w, h, ox, oy))
            for i in range(len(row) - 1, -1, -1):
                if row[i] is None:
                    if i + 1 >= len(row) or row[i + 1] is None:
                        raise SystemExit("sprite %s does not fit at any size" % name)
                    row[i] = row[i + 1]
            blobs += row
        sets.append((name, angles, len(sizes), blobs))

    world = [size_ppm(k) for k in range(N_SIZES)]
    hero_ppm = FY / CAM_BACK_M
    # what the player is, seen from the chase camera: any car, or on foot
    for name, kind, body in CAR_KINDS:
        add("hero_" + name, sp.car(kind, body), 64, [hero_ppm], elev=13.0)
    # people are narrow: they get their keyline by height, from 12 rows up
    people = (1, 12)
    add("stand", sp.person(1.40, None, pants=0.42), 32, [hero_ppm], elev=13.0, outline=people, square=True)
    for fr in range(4):
        add("walk%d" % fr, sp.person(1.40, fr, pants=0.42), 32, [hero_ppm], elev=13.0, outline=people,
            square=True)
    # with the pistol: in the hand on the camera's side, so nothing hides the shot
    for hand, tag in ((1, ""), (-1, "_left")):
        for gun in ("aim", "fire"):
            add(gun + tag, sp.person(1.40, None, pants=0.42, gun=gun, hand=hand), 32, [hero_ppm], elev=13.0,
                outline=people, square=True)
    # everything else in the world, at every distance
    for name, kind, body in CAR_KINDS:
        add(name, sp.car(kind, body), 32, world)
    add("police_b", sp.car("police", 0.13, 1), 32, world)
    # an officer: dark jacket, light trousers, white cap. Nobody else wears
    # light trousers, and they show against a dark wall.
    def pants(nm):
        return 0.70 if nm == "cop" else 0.12
    for shirt, nm in PED_KINDS:
        for fr in range(4):
            add("%s%d" % (nm, fr), sp.person(shirt, fr, pants=pants(nm), cap=nm == "cop"), 8, world, outline=people)
    for shirt, nm in PED_KINDS:
        add("%s_down" % nm, sp.person_down(shirt, pants=pants(nm), cap=nm == "cop"), 8, world)
    for gun in ("aim", "fire"):
        add("cop_" + gun, sp.person(PED_KINDS[-1][0], None, pants=pants("cop"), gun=gun, cap=True), 8, world,
            outline=people)
    for word in ("wasted", "busted"):
        rows, w, h = sp.lettering(word.upper())
        sets.append((word, 1, 1, [pack_sprite(rows, w, h, w // 2, h // 2)]))
    for word in ("passed", "failed"):
        rows, w, h = sp.lettering("MISSION " + word.upper(), small=(0,))
        sets.append((word, 1, 1, [pack_sprite(rows, w, h, w // 2, h // 2)]))
    # what stands about, in the order of its kinds (PROP_*)
    add("tree", sp.tree(), 1, world)
    add("lamp", sp.lamp(True), 4, world)
    add("phone", sp.phone(), 8, world)
    add("mark", sp.mark(), 1, world, outline=(2, 3))
    add("mark_up", sp.mark(0.25), 1, world, outline=(2, 3))
    add("spark", sp.spark(), 1, world, outline=(3, 3))
    add("tracer", sp.tracer(), 1, world, outline=(2, 2))
    add("cash", sp.cash(), 1, world, outline=(2, 3))
    add("cash_up", sp.cash(0.25), 1, world, outline=(2, 3))

    table = bytearray()
    index = bytearray()
    data = bytearray()
    entry = 0
    for name, angles, nsizes, blobs in sets:
        table += bytes([angles, nsizes]) + struct.pack("<H", entry)
        prev, prev_off = None, 0
        for b in blobs:
            # index entry: 3-byte address of the column data, then w, h, ox, oy
            if b is not prev:                  # otherwise shared with the previous size
                prev, prev_off = b, len(data)
                data += b[4:]
            index += struct.pack("<I", prev_off)[:3] + b[:4]
            entry += 1
    print("sprites: %d sets, %d images, %.0f KB, %.1fs" % (len(sets), entry, len(data) / 1024.0, time.time() - t0))
    return [s[0] for s in sets], bytes(table), bytes(index), bytes(data)


# ---------------------------------------------------------------- main
def main():
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    os.makedirs(OUT, exist_ok=True)
    city = cg.generate(seed)
    cg.preview(city, os.path.join(OUT, "city_map.png"))
    import pickle
    with open(os.path.join(OUT, "city.pkl"), "wb") as f:
        pickle.dump(city, f)

    # ------------------------------------------------------------ tables.h
    T = []
    T.append("// Generated by tools/build_assets.py - do not edit by hand.")
    T.append("#pragma once")
    T.append("#include <stdint.h>")
    T.append("")
    C = ["// Generated by tools/build_assets.py - do not edit by hand.",
         "// Plain numbers only: this file is included from assembly as well as C++.",
         "#ifndef STA_CONSTS_H", "#define STA_CONSTS_H"]
    for k, v in (("COLS", COLS), ("ROWS", ROWS), ("COLBYTES", ROWS // 8), ("HORIZON", HORIZON),
                 ("CAM_H", CAM_H), ("CAM_BACK", CAM_BACK), ("MAXD", MAXD_CELLS * 256),
                 ("MAXD_CELLS", MAXD_CELLS),
                 ("SPRITE_MAXD", SPRITE_MAXD_CELLS * 256), ("N_SIZES", N_SIZES),
                 ("CELL_EDGE", 0xFF),
                 ("NAV_C0", NAV_C0), ("NAV_ARROW_COLS", arrows.WINDOW_COLS // 2),
                 ("NAV_BOX_C0", NAV_BOX_C0), ("NAV_BOX_COLS", NAV_BOX_COLS),
                 ("NAV_ARROW_BYTES", len(arrows.pack(0)))):
        C.append("#define %s %d" % (k, v))
    T.append('#include "consts.h"')
    T.append("// FY = %.4f display px per unit of height/depth" % FY)
    T.append("#define FY_K16 %d   // FY/1024 as 0.16 fixed: recip mantissa -> px per cell (10.6)" % int(round(FY * 64 * 256 / 2.0 ** 24 * 65536)))
    zk = 256.0 / FY                       # texture step: cells per pixel = t/FY ; zstep_q16 = t_q8 * 256/FY
    T.append("#define ZSTEP_INT %d" % int(zk))
    T.append("#define ZSTEP_FRAC %d  // zstep(0.16 cells per px) = t*ZSTEP_INT + hi16(t*ZSTEP_FRAC)" % int(round((zk - int(zk)) * 65536)))
    T.append("")
    T.append(c_array("SIN_Q14", "int16_t", [int(round(math.sin(i * math.pi / 512.0) * 16384)) for i in range(257)]))
    tanc = [((c + 0.5) - COLS / 2) / (COLS / 2) * TANHALF for c in range(COLS)]
    # The direction of every column's ray (how far to the side for one ahead,
    # Q14) goes up in even steps from the middle, so the program works it out
    # instead of looking it up: for column c of the right half, m = 2c - 63,
    # it is m * A - ((m * B + C) >> 8); the left half is the same with the
    # other sign. Which A, B and C give exactly the values a table would hold
    # is found here.
    want = [int(round(t * 16384)) for t in tanc]
    assert all(want[COLS - 1 - c] == -want[c] for c in range(COLS))
    half = {2 * c - (COLS - 1): want[c] for c in range(COLS // 2, COLS)}
    fit = [(a, b, c) for a in range(1, 1040) for b in range(0, 256) for c in range(0, 257)
           if abs(a - half[1]) <= 1 and all(m * a - ((m * b + c) >> 8) == v for m, v in half.items())]
    if not fit:
        raise SystemExit("no way found to work out the directions of the rays: a table is needed again")
    T.append("// direction of the ray of column c, Q14: m * TANC_A - ((m * TANC_B + TANC_C) >> 8) for m = 2c - %d" % (COLS - 1))
    T.append("#define TANC_A %d\n#define TANC_B %d\n#define TANC_C %d" % fit[0])
    T.append("#ifdef SELFTEST")
    T.append("// what it has to come to: the build that checks itself compares")
    T.append(c_array("TANC_Q14", "int16_t", want))
    T.append("#endif")
    T.append(c_array("SKYOFF", "int8_t", [int(round(math.atan(t) / (2 * math.pi) * 256)) for t in tanc], 16))
    gt = []
    for y in range(HORIZON + 1, ROWS):
        t = (CAM_H_M / CELL_M) * FY / (y + 0.5 - HORIZON)
        gt.append(min(65535, int(round(t * 256))))
    T.append(c_array("BITMASK", "uint8_t", [1, 2, 4, 8, 16, 32, 64, 128], 8))
    T.append("// depth of the ground seen in screen row HORIZON+1+i, in 1/1024 cells (6.10)")
    T.append(c_array("GROUND_T4", "uint16_t", [min(65535, v * 4) for v in gt]))
    T.append("// reciprocal mantissas: RECIP[i] ~ 2^23 / (128.5 + i)")
    T.append(c_array("RECIP", "uint16_t", [min(65535, int(round(2.0 ** 23 / (128.5 + i)))) for i in range(128)]))
    T.append(c_array("HEIGHT_FLOORS", "uint8_t", list(cg.HEIGHTS), 16))
    wt = []
    for s in range(8):
        wt += tex_columns(WALLS[s])
    T.append("// wall textures: [style][texel column][4] -> two texel rows per byte, top row first")
    T.append(c_array("WALLTEX8", "uint8_t", wt, 16, "0x%02X"))
    gf = []
    for g in GROUND_FLOOR:
        gf += tex_columns(g)
    T.append(c_array("GFTEX8", "uint8_t", gf, 16, "0x%02X"))
    T.append(c_array("GROUNDSEL", "uint8_t", [GROUND_SEL[s][k] for s in range(8) for k in range(4)], 4))
    pal = []
    for s in range(8):
        for side in range(2):
            p = WALL_PAL[s][side]
            pal.append(p[0] | (p[1] << 2) | (p[2] << 4) | (p[3] << 6))
    T.append("// wall palettes: [style*2+side], 2 bits per texel code (wall, window, ledge, dark)")
    T.append(c_array("WALLPAL", "uint8_t", pal, 8, "0x%02X"))
    fog = [(0, 1, 2, 3), (1, 1, 2, 3), (1, 2, 2, 3), (2, 2, 2, 3), (2, 2, 2, 2)]
    T.append("// distance haze: [band] -> remap of levels 0..3, 2 bits each")
    T.append(c_array("FOGMAP", "uint8_t", [f[0] | (f[1] << 2) | (f[2] << 4) | (f[3] << 6) for f in fog], 8, "0x%02X"))
    T.append("#define FOG_T0 20\n#define FOG_T1 25\n#define FOG_T2 34\n#define FOG_T3 42")
    # ground tiles: unique tiles + lookup by cell byte
    tiles, lut, seen = [], [], {}
    for b in range(128):
        tb = tuple(tile_bytes(ground_tile(b)))
        if tb not in seen:
            seen[tb] = len(tiles)
            tiles.append(tb)
        lut.append(seen[tb])
    plain_road = seen[tuple(tile_bytes(ground_tile((cg.ROAD << 4) | 0)))]
    C.append("#define TILE_PLAIN_ROAD %d" % plain_road)
    C.append("#endif")
    with open(os.path.join(SKETCH, "consts.h"), "w") as f:
        f.write("\n".join(C) + "\n")
    T.append("// ground tiles: 16 bytes each = 8 texel rows x (hi bits, lo bits)")
    T.append(c_array("GTILES", "uint8_t", [v for t in tiles for v in t], 16, "0x%02X"))
    T.append(c_array("GTILE_LUT", "uint8_t", lut, 16))
    font = {
        ",": "000000000010100", "'": "010010000000000", "?": "110001010000010", "+": "000010111010000",
        "0": "111101101101111", "1": "010110010010111", "2": "111001111100111", "3": "111001111001111",
        "4": "101101111001001", "5": "111100111001111", "6": "111100111101111", "7": "111001010010010",
        "8": "111101111101111", "9": "111101111001111", " ": "000000000000000",
        # the dollar sign is an S with a stroke through it, which takes two rows more
        "$": "010" "011100010001110" "010",
        "A": "010101111101101", "B": "110101110101110", "C": "011100100100011", "D": "110101101101110",
        "E": "111100110100111", "F": "111100110100100", "G": "011100101101011", "H": "101101111101101",
        "I": "111010010010111", "J": "001001001101010", "K": "101101110101101", "L": "100100100100111",
        "M": "101111111101101", "N": "110101101101101", "O": "010101101101010", "P": "110101110100100",
        "Q": "010101101111011", "R": "110101110101101", "S": "011100010001110", "T": "111010010010010",
        "U": "101101101101111", "V": "101101101101010", "W": "101101111111101", "X": "101101010101101",
        "Y": "101101010010010", "Z": "111001010100111", ".": "000000000000010", "-": "000000111000000",
        ":": "000010000010000", "!": "010010010000010", "/": "001001010100100",
        ">": "100110111110100",
    }
    order = FONT_ORDER
    fb = []
    for ch in order:
        g = font[ch]
        rows = len(g) // 3
        top = 1 - (rows - 5) // 2
        for c in range(3):
            col = 0
            for r in range(rows):
                if g[r * 3 + c] == "1":
                    col |= 1 << (r + top)
            fb.append(col)
    T.append("// 3x5 font, 3 column bytes per glyph, already shifted to rows 1..5 of the HUD strip")
    T.append("// (its bottom row, the last of the screen, never lights up: the display waits there)")
    T.append('#define FONT_CHARS "%s"' % order.replace("\\", "\\\\"))
    T.append("// where some of them are in it")
    for name, ch in (("0", "0"), ("K", "K"), ("M", "M"), ("DOT", ".")):
        T.append("#define FONT_%s %d" % (name, order.index(ch)))
    T.append(c_array("FONT", "uint8_t", fb, 12, "0x%02X"))

    def icon(rows):
        out = []
        for c in range(len(rows[0])):
            col = 0
            for r, line in enumerate(rows):
                if line[c] == "1":
                    col |= 1 << (r + 1)
            out.append(col)
        return out
    T.append(c_array("ICON_HEART", "uint8_t", icon(["01010", "11111", "11111", "01110", "00100"]), 12, "0x%02X"))
    T.append(c_array("ICON_STAR", "uint8_t", icon(["00100", "01110", "11111", "01110", "01010"]), 12, "0x%02X"))
    T.append(c_array("ICON_GUN", "uint8_t", icon(["1111111", "1111110", "0110000", "0110000", "0110000"]), 12, "0x%02X"))
    T.append("// sounds (tools/sound.py): steps of planes, shortest period, chance mask, pulse width; 0 ends")
    for i, name in enumerate(snd.ORDER):
        T.append("#define SOUND_%s %d" % (name.upper(), i))
        T.append(c_array("SOUND_%s_STEPS" % name.upper(), "uint8_t", snd.table(name), 4))
    T.append("#define SOUND_LIST " + ", ".join("SOUND_%s_STEPS" % n.upper() for n in snd.ORDER))
    T.append("// sky: 64 panorama columns (one quarter turn, repeated), 3 hi-plane + 3 lo-plane bytes each")
    T.append(c_array("SKY", "uint8_t", list(pack_sky(make_sky())), 12, "0x%02X"))
    # size index from depth: k = round(6*log2(t_cells) + 6*log2(4*PPM0/FY))
    koff = 6.0 * math.log2(CELL_M * PPM0 / FY)
    T.append("// sprite size index k = 6*exponent + LOG6[mantissa] + SIZE_K0  (depth in 8.8 cells)")
    T.append(c_array("LOG6", "uint8_t", [int(round(6.0 * math.log2(1.0 + (i + 0.5) / 16.0))) for i in range(16)], 16))
    T.append("#define SIZE_KOFF_X16 %d   // 16 * offset, offset = %.3f" % (int(round(koff * 16)), koff))
    with open(os.path.join(SKETCH, "tables.h"), "w") as f:
        f.write("\n".join(T) + "\n")

    # ------------------------------------------------------------ flash image
    names, stable, sindex, sdata = build_sprites()
    jobs, phones, job_first, said = missions.build(city, FONT_ORDER)
    with open(os.path.join(OUT, "missions.txt"), "w") as f:
        f.write("\n".join(said) + "\n")
    ptable, pdata, most = pack_props(city, phones)
    blob = bytearray()
    offs = {}

    def put(name, data):
        while len(blob) % 16:
            blob.append(0xFF)
        offs[name] = len(blob)
        blob.extend(data)
    put("FX_HEADER", b"SMALLTHEFT\x00\x01" + bytes(4))
    put("FX_MAP", city["cells"])
    put("FX_PROP_TABLE", ptable)
    put("FX_PROP_DATA", pdata)
    put("FX_SPRITE_INDEX", sindex)
    put("FX_SPRITE_DATA", sdata)
    put("FX_TITLE", title_page())
    put("FX_MAP_PICTURE", map_page(city, os.path.join(OUT, "map_page.png")))
    put("FX_ARROWS", arrows.pack_all())
    put("FX_JOBS", jobs)
    while len(blob) % 256:
        blob.append(0xFF)
    with open(os.path.join(OUT, "fxdata.bin"), "wb") as f:
        f.write(blob)
    # what the game may write to: 4 KB, all 0xFF until it does
    with open(os.path.join(OUT, "fxsave.bin"), "wb") as f:
        f.write(b"\xff" * SAVE_BYTES)
    page = (0x1000000 - SAVE_BYTES - len(blob)) >> 8
    X = ["// Generated by tools/build_assets.py - do not edit by hand.", "#pragma once", "#include <stdint.h>", "",
         "// development places: the data sits at the end of the 16 MB chip, in front",
         "// of the 4 KB the game may write to (the way the ArduboyFX tools have it)",
         "#define FX_DATA_PAGE 0x%04X" % page,
         "#define FX_SAVE_PAGE 0x%04X" % ((0x1000000 - SAVE_BYTES) >> 8),
         "#define FX_DATA_BYTES %dUL" % len(blob), ""]
    for k, v in offs.items():
        X.append("#define %s 0x%06XUL" % (k, v))
    X.append("")
    for i, n in enumerate(names):
        X.append("#define SPR_%s %d" % (n.upper(), i))
    X.append("// groups: first set of each; the members follow in order")
    X.append("#define SPR_HERO_CAR SPR_HERO_%s   // + car kind" % CAR_KINDS[0][0].upper())
    X.append("#define SPR_HERO_STAND SPR_STAND     // standing still; + 1 + step of the walk, 0..3")
    X.append("#define SPR_HERO_AIM SPR_AIM         // pistol up; + 1 with the flash, + 2 in the left hand")
    X.append("#define SPR_CAR SPR_%s         // + car kind" % CAR_KINDS[0][0].upper())
    X.append("#define SPR_PED SPR_PED_A0           // + 4 * kind + step")
    X.append("#define SPR_PED_DOWN SPR_PED_A_DOWN  // + kind")
    X.append("#define N_CAR_KINDS %d" % len(CAR_KINDS))
    X.append("#define N_PED_KINDS %d" % len(PED_KINDS))
    for i, (n, _, _) in enumerate(CAR_KINDS):
        X.append("#define CAR_%s %d" % (n.upper(), i))
    X.append("// sprite sets: angles, sizes, first index entry (16 bit)")
    X.append("const uint8_t SPRITE_SETS[%d] PROGMEM = {%s};" % (len(stable), ", ".join(str(v) for v in stable)))
    X.append("#define PROP_TREE %d\n#define PROP_LAMP %d\n#define PROP_PHONE %d" % (PROP_TREE, PROP_LAMP, PROP_PHONE))
    assert names.index("lamp") == names.index("tree") + PROP_LAMP and names.index("phone") == names.index("tree") + PROP_PHONE
    X.append("// missions (tools/missions.py): so many, %d bytes each on the flash chip" % missions.JOB_BYTES)
    X.append("#define N_JOBS %d" % (len(jobs) // missions.JOB_BYTES))
    X.append("#define JOB_TEXT %d        // %d lines of %d signs, as places in the lettering" % (missions.JOB_TEXT, missions.LINES, missions.LINE))
    X.append("#define JOB_LINES %d\n#define JOB_LINE %d" % (missions.LINES, missions.LINE))
    X.append("#define JOB_STEPS %d      // steps of %d bytes: what is asked for, then two hints of %d signs" % (missions.JOB_STEPS, missions.STEP_BYTES, missions.HINT))
    X.append("#define JOB_HINT %d\n#define JOB_PAY_UNIT %d" % (missions.HINT, missions.PAY_UNIT))
    for n in ("STEP_END", "STEP_GO", "STEP_KILL", "STEP_LOSE"):
        X.append("#define %s %d" % (n, getattr(missions, n)))
    for n in ("STEP_COUNT", "STEP_CAR", "STEP_STOP", "STEP_MARK", "STEP_COPS"):
        X.append("#define %s 0x%02X" % (n, getattr(missions, n)))
    X.append("#define STEP_ANY_CAR %d" % missions.CARS["any"])
    X.append("// the telephones that offer them. The first mission of every one (they are its")
    X.append("// own up to the first one of the next)")
    X.append("const uint8_t JOB_FIRST[%d] PROGMEM = {%s};" % (len(job_first), ", ".join(str(v) for v in job_first)))
    X.append("// the first letter of whoever is on the line (its")
    X.append("// place in the lettering), for the map")
    X.append("const uint8_t PHONE_SIGNS[%d] PROGMEM = {%s};" % (len(phones), ", ".join(
        str(FONT_ORDER.index(who.replace("THE ", "")[0])) for who, _ in missions.PHONES)))
    X.append("// and where they stand (8.8 cells)")
    X.append("#define N_PHONES %d" % len(phones))
    X.append("const uint16_t PHONES[%d] PROGMEM = {%s};" % (2 * len(phones), ", ".join(
        "0x%04X, 0x%04X" % (int(x * 256), int(y * 256)) for x, y in phones)))
    X.append("#define PROP_CHUNK_MAX %d" % most)
    with open(os.path.join(SKETCH, "fxdata.h"), "w") as f:
        f.write("\n".join(X) + "\n")
    print("fxdata.bin: %d bytes (%.2f MB), data page 0x%04X" % (len(blob), len(blob) / 1048576.0, page))
    print("ground tiles: %d unique, most props in one chunk: %d" % (len(tiles), most))
    for k, v in offs.items():
        print("  %-16s 0x%06X" % (k, v))


if __name__ == "__main__":
    main()
