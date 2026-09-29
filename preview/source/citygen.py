#!/usr/bin/env python3
"""
Procedural city for the look-dev preview (later: the real asset pipeline).

The world is a grid of 4 m cells, GTA 1/2 style. Every cell has
  typ  : ground type (or BUILDING)
  hgt  : building height in floors (1 floor = 4 m), 0 for open ground
  sty  : building wall style, or road marking code for road cells
  dirn : traffic direction for road cells (0=N 1=E 2=S 3=W), travel on the right
That is 2 bytes per cell once packed, which is what the flash chip would hold.
"""
import os, pickle, random, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
W = H = 176

GRASS, PAVE, ROAD, WATER, PLAZA, SAND, LOT, BUILDING = range(8)
# road markings
M_NONE, M_CENTER, M_DASH, M_CROSS = range(4)
# wall styles
S_OFFICE, S_GLASS, S_BRICK, S_WAREHOUSE, S_HOTEL, S_SHOPS = range(6)

N_, E_, S_, W_ = 0, 1, 2, 3


def generate(seed=4):
    rnd = random.Random(seed)
    typ = [[GRASS] * W for _ in range(H)]
    hgt = [[0] * W for _ in range(H)]
    sty = [[0] * W for _ in range(H)]
    dirn = [[0] * W for _ in range(H)]

    # --- river along the east side, with a wobbly bank ---------------------
    bank = []
    b = W - 30.0
    for y in range(H):
        b += rnd.uniform(-0.6, 0.6)
        b = max(W - 34.0, min(W - 26.0, b))
        bank.append(int(b))
    for y in range(H):
        for x in range(bank[y], min(W, bank[y] + 22)):
            typ[y][x] = WATER
        for x in range(bank[y] - 2, bank[y]):
            typ[y][x] = SAND
    land_w = min(bank) - 3

    # --- road grid ----------------------------------------------------------
    avenues, streets = [], []
    x = 5
    k = 0
    while x < land_w - 6:
        wide = 4 if k % 3 == 1 else 2
        avenues.append((x, wide))
        x += wide + rnd.choice((12, 14, 15))
        k += 1
    y = 5
    k = 0
    while y < H - 8:
        wide = 4 if k % 4 == 2 else 2
        streets.append((y, wide))
        y += wide + rnd.choice((10, 11, 13))
        k += 1
    x_end = avenues[-1][0] + avenues[-1][1]
    y_end = streets[-1][0] + streets[-1][1]
    bridge = streets[len(streets) // 2]

    def road(x, y, d, mark):
        typ[y][x] = ROAD
        dirn[y][x] = d
        sty[y][x] = mark

    for (ax, aw) in avenues:
        half = aw // 2
        for y in range(streets[0][0], y_end):
            for i in range(aw):
                south = i < half                      # west half drives south
                inner = (i == half - 1) or (i == half)
                road(ax + i, y, S_ if south else N_, M_CENTER if inner else M_DASH)
    for (sy_, sw) in streets:
        half = sw // 2
        xe = W if (sy_, sw) == bridge else x_end
        for x in range(avenues[0][0], xe):
            for i in range(sw):
                west = i < half                       # north half drives west
                inner = (i == half - 1) or (i == half)
                if typ[sy_ + i][x] == ROAD and x < x_end and any(a <= x < a + w_ for a, w_ in avenues):
                    sty[sy_ + i][x] = M_NONE          # intersection: bare asphalt
                    continue
                road(x, sy_ + i, W_ if west else E_, M_CENTER if inner else M_DASH)
    # crosswalks on the approaches
    for (ax, aw) in avenues:
        for (sy_, sw) in streets:
            for i in range(aw):
                for yy in (sy_ - 1, sy_ + sw):
                    if 0 <= yy < H and typ[yy][ax + i] == ROAD:
                        sty[yy][ax + i] = M_CROSS
            for i in range(sw):
                for xx in (ax - 1, ax + aw):
                    if 0 <= xx < W and typ[sy_ + i][xx] == ROAD:
                        sty[sy_ + i][xx] = M_CROSS

    # --- sidewalks ----------------------------------------------------------
    for y in range(H):
        for x in range(W):
            if typ[y][x] in (GRASS, SAND, WATER):
                near = False
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        yy, xx = y + dy, x + dx
                        if 0 <= yy < H and 0 <= xx < W and typ[yy][xx] == ROAD:
                            near = True
                if near:
                    typ[y][x] = PAVE

    # --- blocks -> lots -> buildings ----------------------------------------
    cx, cy = land_w * 0.52, H * 0.5
    park_block = (len(avenues) // 2 - 1, len(streets) // 2 + 1)
    trees, lamps = [], []

    def lot(x0, y0, x1, y1, zone):
        w_, h_ = x1 - x0, y1 - y0
        if w_ <= 0 or h_ <= 0:
            return
        if (w_ > 6 or h_ > 6) and (w_ > 3 or h_ > 3):
            if w_ >= h_:
                m = x0 + rnd.randint(max(2, w_ // 3), max(2, w_ - w_ // 3))
                lot(x0, y0, m, y1, zone)
                lot(m, y0, x1, y1, zone)
            else:
                m = y0 + rnd.randint(max(2, h_ // 3), max(2, h_ - h_ // 3))
                lot(x0, y0, x1, m, zone)
                lot(x0, m, x1, y1, zone)
            return
        r = rnd.random()
        if zone == 0:                                  # downtown
            if r < 0.06:
                kind = PLAZA
            else:
                kind = BUILDING
                floors = rnd.choice((6, 8, 10, 12, 14, 18, 22, 26))
                style = rnd.choice((S_GLASS, S_GLASS, S_OFFICE, S_OFFICE, S_HOTEL))
        elif zone == 1:                                # midtown
            if r < 0.08:
                kind = LOT
            elif r < 0.12:
                kind = PLAZA
            else:
                kind = BUILDING
                floors = rnd.choice((2, 3, 3, 4, 5, 6, 8))
                style = rnd.choice((S_OFFICE, S_BRICK, S_BRICK, S_SHOPS, S_HOTEL))
        else:                                          # edge of town
            if r < 0.18:
                kind = GRASS
            elif r < 0.30:
                kind = LOT
            else:
                kind = BUILDING
                floors = rnd.choice((1, 1, 2, 2, 3))
                style = rnd.choice((S_BRICK, S_WAREHOUSE, S_WAREHOUSE, S_SHOPS))
        for y in range(y0, y1):
            for x in range(x0, x1):
                if kind == BUILDING:
                    typ[y][x] = BUILDING
                    hgt[y][x] = floors
                    sty[y][x] = style
                else:
                    typ[y][x] = kind
        if kind == GRASS and w_ > 1 and h_ > 1:
            for _ in range(2):
                trees.append((rnd.uniform(x0 + 0.5, x1 - 0.5), rnd.uniform(y0 + 0.5, y1 - 0.5)))

    for ai in range(len(avenues) - 1):
        for si in range(len(streets) - 1):
            x0 = avenues[ai][0] + avenues[ai][1] + 1
            x1 = avenues[ai + 1][0] - 1
            y0 = streets[si][0] + streets[si][1] + 1
            y1 = streets[si + 1][0] - 1
            mx, my = (x0 + x1) * 0.5, (y0 + y1) * 0.5
            d = ((mx - cx) ** 2 + (my - cy) ** 2) ** 0.5
            zone = 0 if d < 26 else (1 if d < 52 else 2)
            if (ai, si) == park_block:
                for y in range(y0, y1):
                    for x in range(x0, x1):
                        typ[y][x] = GRASS
                for _ in range(16):
                    trees.append((rnd.uniform(x0 + 0.6, x1 - 0.6), rnd.uniform(y0 + 0.6, y1 - 0.6)))
                px, py = (x0 + x1) // 2, (y0 + y1) // 2
                for y in range(py - 1, py + 2):
                    for x in range(px - 2, px + 2):
                        typ[y][x] = WATER
                continue
            lot(x0, y0, x1, y1, zone)

    # --- street furniture -----------------------------------------------------
    for (ax, aw) in avenues:
        for y in range(streets[0][0] + 3, y_end - 2, 5):
            if typ[y][ax - 1] == PAVE:
                lamps.append((ax - 0.15, y + 0.5))
            if typ[y + 2][ax + aw] == PAVE:
                lamps.append((ax + aw + 0.15, y + 2.5))
    for (sy_, sw) in streets:
        for x in range(avenues[0][0] + 4, x_end - 2, 6):
            if typ[sy_ - 1][x] == PAVE:
                lamps.append((x + 0.5, sy_ - 0.15))
    for (ax, aw) in avenues[::2]:
        for y in range(streets[0][0] + 5, y_end - 2, 7):
            if typ[y][ax + aw] == PAVE and typ[y][ax + aw + 1] != BUILDING:
                trees.append((ax + aw + 0.6, y + 0.5))

    return dict(W=W, H=H, typ=typ, hgt=hgt, sty=sty, dir=dirn, avenues=avenues, streets=streets,
                bridge=bridge, trees=trees, lamps=lamps, x_end=x_end, y_end=y_end)


def preview(city, path):
    cols = {GRASS: (70, 130, 60), PAVE: (170, 170, 170), ROAD: (50, 50, 55), WATER: (40, 70, 140),
            PLAZA: (200, 190, 160), SAND: (220, 200, 140), LOT: (90, 90, 100)}
    im = Image.new("RGB", (W, H))
    px = im.load()
    for y in range(H):
        for x in range(W):
            t = city["typ"][y][x]
            if t == BUILDING:
                v = min(255, 90 + city["hgt"][y][x] * 6)
                px[x, y] = (v, int(v * 0.8), int(v * 0.6))
            else:
                c = cols[t]
                if t == ROAD and city["sty"][y][x] == M_CROSS:
                    c = (230, 230, 230)
                px[x, y] = c
    for (tx, ty) in city["trees"]:
        px[int(tx), int(ty)] = (20, 80, 20)
    for (lx, ly) in city["lamps"]:
        px[min(W - 1, int(lx)), min(H - 1, int(ly))] = (255, 255, 0)
    im.resize((W * 4, H * 4), Image.NEAREST).save(path)


if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    city = generate(seed)
    with open(os.path.join(HERE, "city.pkl"), "wb") as f:
        pickle.dump(city, f)
    preview(city, os.path.join(HERE, "city_map.png"))
    nb = sum(1 for row in city["typ"] for t in row if t == BUILDING)
    print("avenues", city["avenues"])
    print("streets", city["streets"])
    print("bridge", city["bridge"], "buildings cells", nb, "trees", len(city["trees"]), "lamps", len(city["lamps"]))
    print("packed size at 2 bytes/cell: %d bytes" % (W * H * 2))
