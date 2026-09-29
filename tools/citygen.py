#!/usr/bin/env python3
"""
Procedural city generator for Small Theft Auto.

The world is a 256 x 256 grid of 4 m cells (the same grid size GTA 1 used).
Every cell packs into ONE byte, which is all the renderer needs:

  bit 7 = 1  building : bits 6..3 height class (index into HEIGHTS), bits 2..0 wall style
  bit 7 = 0  ground   : bits 6..4 ground type, bits 3..0 detail
       ROAD : bits 3..2 travel direction (0 N, 1 E, 2 S, 3 W), bits 1..0 marking
       PAVE : bits 3..0 which neighbours are road (N, E, S, W) -> curb lines

Traffic drives on the right.
"""
import os, pickle, random, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
W = H = 256

GRASS, PAVE, ROAD, WATER, PLAZA, SAND, LOT, BUILDING = range(8)
M_NONE, M_CENTER, M_DASH, M_CROSS = range(4)
S_OFFICE, S_GLASS, S_BRICK, S_WAREHOUSE, S_HOTEL, S_SHOPS, S_TOWER, S_FLATS = range(8)
N_, E_, S_, W_ = 0, 1, 2, 3

# height classes, in floors (1 floor = 1 cell = 4 m)
HEIGHTS = (1, 2, 3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 24, 28, 32)


def height_class(floors):
    best = 0
    for i, h in enumerate(HEIGHTS):
        if h <= floors:
            best = i
    return best


def generate(seed=4):
    rnd = random.Random(seed)
    typ = [[WATER] * W for _ in range(H)]
    hgt = [[0] * W for _ in range(H)]
    sty = [[0] * W for _ in range(H)]
    dirn = [[0] * W for _ in range(H)]
    trees, lamps = [], []

    # ------------------------------------------------------------- land masses
    # west bank (main city) and east bank (docks), a river between, sea all around
    def coast(base, amp, n):
        out, v = [], float(base)
        for _ in range(n):
            v += rnd.uniform(-0.7, 0.7)
            v = max(base - amp, min(base + amp, v))
            out.append(int(round(v)))
        return out
    west_l = coast(6, 2, H)
    west_r = coast(172, 3, H)
    east_l = coast(198, 3, H)
    east_r = coast(249, 2, H)
    top = coast(6, 2, W)
    bot = coast(249, 2, W)
    for y in range(H):
        for x in range(W):
            land = (west_l[y] <= x <= west_r[y] or east_l[y] <= x <= east_r[y]) and top[x] <= y <= bot[x]
            if land:
                typ[y][x] = GRASS
    # beaches: land next to water
    for y in range(H):
        for x in range(W):
            if typ[y][x] == GRASS:
                for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2), (1, 1), (-1, -1), (1, -1), (-1, 1)):
                    xx, yy = x + dx, y + dy
                    if not (0 <= xx < W and 0 <= yy < H) or typ[yy][xx] == WATER:
                        typ[y][x] = SAND
                        break

    # ------------------------------------------------------------- road grids
    def grid(x_lo, x_hi, y_lo, y_hi, xgap, ygap, wide_every_x, wide_every_y):
        avenues, streets = [], []
        x, k = x_lo, 0
        while x < x_hi - 4:
            wide = 4 if (wide_every_x and k % wide_every_x == 1) else 2
            avenues.append((x, wide))
            x += wide + rnd.choice(xgap)
            k += 1
        y, k = y_lo, 0
        while y < y_hi - 4:
            wide = 4 if (wide_every_y and k % wide_every_y == 2) else 2
            streets.append((y, wide))
            y += wide + rnd.choice(ygap)
            k += 1
        return avenues, streets

    def road(x, y, d, mark):
        typ[y][x] = ROAD
        dirn[y][x] = d
        sty[y][x] = mark

    def lay(avenues, streets, x_through=None):
        x_end = avenues[-1][0] + avenues[-1][1]
        y_end = streets[-1][0] + streets[-1][1]
        for (ax, aw) in avenues:
            half = aw // 2
            for y in range(streets[0][0], y_end):
                for i in range(aw):
                    south = i < half
                    inner = (i == half - 1) or (i == half)
                    road(ax + i, y, S_ if south else N_, M_CENTER if inner else M_DASH)
        for (sy_, sw) in streets:
            half = sw // 2
            for x in range(avenues[0][0], x_end):
                for i in range(sw):
                    west = i < half
                    inner = (i == half - 1) or (i == half)
                    if typ[sy_ + i][x] == ROAD and any(a <= x < a + w_ for a, w_ in avenues):
                        sty[sy_ + i][x] = M_NONE
                        continue
                    road(x, sy_ + i, W_ if west else E_, M_CENTER if inner else M_DASH)
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
        return x_end, y_end

    av_w, st_w = grid(14, 166, 14, 244, (12, 14, 15), (10, 11, 13), 3, 4)
    xw_end, yw_end = lay(av_w, st_w)
    av_e, st_e = grid(204, 246, 22, 238, (14, 16), (12, 14, 15), 0, 0)
    xe_end, ye_end = lay(av_e, st_e)

    # bridges: two west-bank streets continue across the river to the east bank
    wide_streets = [s for s in st_w if s[1] == 4]
    bridges = [wide_streets[0], wide_streets[-1]] if len(wide_streets) >= 2 else wide_streets
    for (sy_, sw) in bridges:
        half = sw // 2
        for x in range(xw_end, av_e[0][0]):
            for i in range(sw):
                west = i < half
                inner = (i == half - 1) or (i == half)
                road(x, sy_ + i, W_ if west else E_, M_CENTER if inner else M_DASH)
        # the east-bank end joins the first east avenue over its full height
        ax, aw = av_e[0]
        for i in range(sw):
            for k in range(aw):
                sty[sy_ + i][ax + k] = M_NONE
                typ[sy_ + i][ax + k] = ROAD

    # ------------------------------------------------------------- sidewalks
    for y in range(H):
        for x in range(W):
            if typ[y][x] != ROAD:
                near = False
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        yy, xx = y + dy, x + dx
                        if 0 <= yy < H and 0 <= xx < W and typ[yy][xx] == ROAD:
                            near = True
                if near:
                    typ[y][x] = PAVE

    # ------------------------------------------------------------- blocks
    cx, cy = 92.0, 128.0                       # downtown centre

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
        floors, style = 0, 0
        if zone == 0:                                  # downtown
            if r < 0.06:
                kind = PLAZA
            else:
                kind = BUILDING
                floors = rnd.choice((8, 10, 12, 14, 16, 18, 20, 24, 28, 32))
                style = rnd.choice((S_GLASS, S_GLASS, S_TOWER, S_OFFICE, S_OFFICE, S_HOTEL))
        elif zone == 1:                                # midtown
            if r < 0.07:
                kind = LOT
            elif r < 0.11:
                kind = PLAZA
            else:
                kind = BUILDING
                floors = rnd.choice((2, 3, 3, 4, 5, 6, 8, 10))
                style = rnd.choice((S_OFFICE, S_BRICK, S_BRICK, S_SHOPS, S_HOTEL, S_FLATS))
        elif zone == 2:                                # residential edge
            if r < 0.20:
                kind = GRASS
            elif r < 0.28:
                kind = LOT
            else:
                kind = BUILDING
                floors = rnd.choice((1, 1, 2, 2, 3, 4))
                style = rnd.choice((S_BRICK, S_FLATS, S_FLATS, S_SHOPS))
        else:                                          # docks / industry
            if r < 0.22:
                kind = LOT
            else:
                kind = BUILDING
                floors = rnd.choice((1, 2, 2, 3))
                style = rnd.choice((S_WAREHOUSE, S_WAREHOUSE, S_WAREHOUSE, S_BRICK))
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

    def blocks(avenues, streets, zone_fn, park=None):
        for ai in range(len(avenues) - 1):
            for si in range(len(streets) - 1):
                x0 = avenues[ai][0] + avenues[ai][1] + 1
                x1 = avenues[ai + 1][0] - 1
                y0 = streets[si][0] + streets[si][1] + 1
                y1 = streets[si + 1][0] - 1
                if park and (ai, si) in park:
                    for y in range(y0, y1):
                        for x in range(x0, x1):
                            typ[y][x] = GRASS
                    for _ in range(14):
                        trees.append((rnd.uniform(x0 + 0.6, x1 - 0.6), rnd.uniform(y0 + 0.6, y1 - 0.6)))
                    px, py = (x0 + x1) // 2, (y0 + y1) // 2
                    for y in range(py - 1, py + 2):
                        for x in range(px - 2, px + 2):
                            typ[y][x] = WATER
                    continue
                lot(x0, y0, x1, y1, zone_fn((x0 + x1) * 0.5, (y0 + y1) * 0.5))

    def zone_west(mx, my):
        d = ((mx - cx) ** 2 + (my - cy) ** 2) ** 0.5
        return 0 if d < 30 else (1 if d < 62 else 2)
    park = {(len(av_w) // 2 + 1, len(st_w) // 2 - 2), (2, len(st_w) - 4)}
    blocks(av_w, st_w, zone_west, park)
    blocks(av_e, st_e, lambda mx, my: 3)

    # ------------------------------------------------------------- furniture
    def furnish(avenues, streets, x_end, y_end):
        for (ax, aw) in avenues:
            for y in range(streets[0][0] + 3, y_end - 2, 5):
                if typ[y][ax - 1] == PAVE:
                    lamps.append((ax - 0.15, y + 0.5))
                if y + 2 < H and typ[y + 2][ax + aw] == PAVE:
                    lamps.append((ax + aw + 0.15, y + 2.5))
        for (sy_, sw) in streets:
            for x in range(avenues[0][0] + 4, x_end - 2, 6):
                if typ[sy_ - 1][x] == PAVE:
                    lamps.append((x + 0.5, sy_ - 0.15))
        for (ax, aw) in avenues[::2]:
            for y in range(streets[0][0] + 5, y_end - 2, 7):
                if typ[y][ax + aw] == PAVE and typ[y][ax + aw + 1] != BUILDING:
                    trees.append((ax + aw + 0.6, y + 0.5))
    furnish(av_w, st_w, xw_end, yw_end)
    furnish(av_e, st_e, xe_end, ye_end)

    city = dict(W=W, H=H, typ=typ, hgt=hgt, sty=sty, dir=dirn, avenues=av_w, streets=st_w,
                avenues_e=av_e, streets_e=st_e, bridges=bridges, bridge=bridges[0],
                trees=trees, lamps=lamps, x_end=xw_end, y_end=yw_end)
    city["cells"] = pack_cells(city)
    return city


def pack_cells(city):
    """One byte per cell, row-major."""
    typ, hgt, sty, dirn = city["typ"], city["hgt"], city["sty"], city["dir"]
    out = bytearray(W * H)
    for y in range(H):
        for x in range(W):
            t = typ[y][x]
            if x == 0 or y == 0 or x == W - 1 or y == H - 1:
                out[y * W + x] = 0xFF          # edge of the world: rays stop here
                continue
            if t == BUILDING:
                b = 0x80 | (height_class(hgt[y][x]) << 3) | (sty[y][x] & 7)
                if b == 0xFF:
                    b = 0xFE                   # 0xFF is reserved for the edge
            elif t == ROAD:
                b = (ROAD << 4) | (dirn[y][x] << 2) | (sty[y][x] & 3)
            elif t == PAVE:
                m = 0
                for bit, (dx, dy) in enumerate(((0, -1), (1, 0), (0, 1), (-1, 0))):
                    xx, yy = x + dx, y + dy
                    if 0 <= xx < W and 0 <= yy < H and typ[yy][xx] == ROAD:
                        m |= 1 << bit
                b = (PAVE << 4) | m
            else:
                b = t << 4
            out[y * W + x] = b
    return bytes(out)


def preview(city, path, scale=3):
    cols = {GRASS: (70, 130, 60), PAVE: (170, 170, 170), ROAD: (50, 50, 55), WATER: (40, 70, 140),
            PLAZA: (200, 190, 160), SAND: (220, 200, 140), LOT: (90, 90, 100)}
    im = Image.new("RGB", (W, H))
    px = im.load()
    for y in range(H):
        for x in range(W):
            t = city["typ"][y][x]
            if t == BUILDING:
                v = min(255, 80 + city["hgt"][y][x] * 5)
                px[x, y] = (v, int(v * 0.8), int(v * 0.6))
            else:
                c = cols[t]
                if t == ROAD and city["sty"][y][x] == M_CROSS:
                    c = (230, 230, 230)
                px[x, y] = c
    for (tx, ty) in city["trees"]:
        px[int(tx), int(ty)] = (20, 80, 20)
    im.resize((W * scale, H * scale), Image.NEAREST).save(path)


if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    city = generate(seed)
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "build")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "city.pkl"), "wb") as f:
        pickle.dump(city, f)
    preview(city, os.path.join(out, "city_map.png"))
    nb = sum(1 for row in city["typ"] for t in row if t == BUILDING)
    print("west avenues", city["avenues"])
    print("west streets", city["streets"])
    print("east avenues", city["avenues_e"], "bridges", city["bridges"])
    print("building cells", nb, "trees", len(city["trees"]), "lamps", len(city["lamps"]))
