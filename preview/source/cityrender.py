#!/usr/bin/env python3
"""
Look-dev reference renderer for a 3D open-world city on the Arduboy FX.

NOT the game: a Python model of the renderer the console would run, held to the
console's limits so the pictures are an honest preview.

  * 128x64 panel: 3D view is 64 double-wide columns x 56 rows + 8-row HUD strip
  * 4 brightness levels, no dithering in the 3D view
  * world = grid of 4 m cells, 2 bytes each, fetched cell by cell along each ray
  * cars / people / props are pre-rendered sprites, only copied at run time
  * work per frame is counted and printed (cell fetches, pixels, sprite columns)
"""
import math, os, pickle, random, sys
from PIL import Image, ImageDraw
import citygen as cg
from sprites import build_bank

HERE = os.path.dirname(os.path.abspath(__file__))

COLS, ROWS = 64, 56
TANHALF = 0.82
FY = 64.0 / TANHALF              # display px per unit of (height / depth)
CELL = 4.0
FLOOR = 4.0
MAXD = 190.0                     # view distance, metres
HORIZON = 19.0
CAM_H = 2.35
CAM_BACK = 6.2
LEVEL_RGB = (0, 156, 215, 255)

LOOKS = {
    "day": dict(fog=2.45, fog0=50.0, fogp=1.0, wall=(2, 1), win=(0, 0), lit=0.0,
                road=1, mark=3, pave=2, curb=0, grass=1, grass2=0, water=0, plaza=3, lot=1, sand=2),
    "night": dict(fog=0.0, fog0=60.0, fogp=1.4, wall=(1, 0), win=(0, 0), lit=0.34,
                  road=0, mark=2, pave=1, curb=0, grass=0, grass2=1, water=0, plaza=1, lot=0, sand=1),
}


def h3(a, b, c=0):
    v = (a * 73856093) ^ (b * 19349663) ^ (c * 83492791)
    v ^= v >> 13
    v = (v * 1274126177) & 0xFFFFFFFF
    return (v >> 8) & 0xFFFF


# --- wall textures: 8x8 texels per 4 m bay and per floor ---------------------
# '.' wall  'W' window  'L' light ledge  'D' dark (door, vent)  'M' mullion
WALLS = {
    cg.S_OFFICE: ["........", "........", ".WW..WW.", ".WW..WW.", ".WW..WW.", ".WW..WW.", "........", "........"],
    cg.S_GLASS: ["LLLLLLLL", "WWWMWWWM", "WWWMWWWM", "WWWMWWWM", "WWWMWWWM", "WWWMWWWM", "WWWMWWWM", "........"],
    cg.S_BRICK: ["........", "........", "..WWW...", "..WWW...", "..WWW...", ".LLLLL..", "........", "........"],
    cg.S_WAREHOUSE: ["........", "LLLLLLLL", "........", "........", "........", "........", "........", "........"],
    cg.S_HOTEL: ["........", ".WW.WW..", ".WW.WW..", ".WW.WW..", "LLLLLLL.", "........", "........", "........"],
    cg.S_SHOPS: ["........", "..WW....", "..WW....", "..WW....", "........", "........", "........", "........"],
}
GROUND_FLOOR = {
    "shop": ["LLLLLLLL", "LDLDLDLD", ".WWWWWW.", ".WWWWWW.", ".WWWWWW.", ".WWWWWW.", "........", "........"],
    "door": ["........", "..LLLL..", "..DDDD..", "..DDDD..", "..DDDD..", "..DDDD..", "..DDDD..", "..DDDD.."],
    "gate": ["........", "LLLLLLLL", ".DDDDDD.", ".DDDDDD.", ".DDDDDD.", ".DDDDDD.", ".DDDDDD.", ".DDDDDD."],
}


class City:
    def __init__(self):
        with open(os.path.join(HERE, "city.pkl"), "rb") as f:
            c = pickle.load(f)
        self.__dict__.update(c)
        self.dirn = c["dir"]
        # curb codes for pavement: bit0 N, bit1 E, bit2 S, bit3 W neighbour is road
        self.curb = [[0] * self.W for _ in range(self.H)]
        for y in range(self.H):
            for x in range(self.W):
                if self.typ[y][x] == cg.PAVE:
                    m = 0
                    for bit, (dx, dy) in enumerate(((0, -1), (1, 0), (0, 1), (-1, 0))):
                        xx, yy = x + dx, y + dy
                        if 0 <= xx < self.W and 0 <= yy < self.H and self.typ[yy][xx] == cg.ROAD:
                            m |= 1 << bit
                    self.curb[y][x] = m
        self.lampgrid = {}
        for (lx, ly) in self.lamps:
            self.lampgrid.setdefault((int(lx), int(ly)), []).append((lx, ly))

    def cell(self, ix, iy):
        if 0 <= ix < self.W and 0 <= iy < self.H:
            return self.typ[iy][ix], self.hgt[iy][ix], self.sty[iy][ix]
        return cg.GRASS, 0, 0

    def lamp_light(self, wx, wy):
        """0..1 light from the nearest street lamp (would be a baked light tile)."""
        cx, cy = int(wx), int(wy)
        best = 9.0
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                for (lx, ly) in self.lampgrid.get((cx + dx, cy + dy), ()):
                    d = (lx - wx) ** 2 + (ly - wy) ** 2
                    if d < best:
                        best = d
        return best            # squared distance in cells


class Renderer:
    def __init__(self, city, bank, look):
        self.city = city
        self.bank = bank
        self.lookname = look
        self.L = LOOKS[look]
        self.stat = dict(cells=0, wall=0, ground=0, sprite=0, frames=0)
        self.sky = self.make_sky(look)

    # ------------------------------------------------------------------ sky
    def make_sky(self, look, pw=512, ph=40):
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
        n1, n2 = noise(9, 4), noise(22, 9)
        sky = []
        for v in range(ph):                       # v rows above the horizon
            row = []
            for u in range(pw):
                n = 0.6 * n1[v][u] + 0.4 * n2[v][u]
                if look == "day":
                    base = 3 if v < 5 else 2
                    if v >= 6 and n > 0.56:
                        base = 3
                    if v >= 14 and n < 0.40:
                        base = 1
                else:
                    base = 2 if v < 3 else (1 if v < 9 else 0)
                    if v > 11 and rnd.random() < 0.012:
                        base = 3 if rnd.random() < 0.5 else 2
                row.append(base)
            sky.append(row)
        if look == "night":
            mu, mv, mr = 96, 27, 4.4
            for v in range(ph):
                for u in range(pw):
                    dx, dy = (u - mu) * 0.55, v - mv
                    if dx * dx + dy * dy <= mr * mr:
                        shade = (dx + 2.4) ** 2 + (dy - 1.2) ** 2 > (mr * 0.98) ** 2
                        sky[v][u] = 3 if shade else 1
        return sky

    # --------------------------------------------------------------- ground
    def ground(self, typ, sty, ix, iy, wx, wy, t, hero):
        """Level 0..3 of one ground pixel. wx, wy in cell units."""
        L = self.L
        u = wx - ix
        v = wy - iy
        c = self.city
        if typ == cg.ROAD:
            lv = L["road"]
            d = c.dirn[iy][ix]
            if d == cg.N_:
                uc, along = u, wy
            elif d == cg.S_:
                uc, along = 1.0 - u, wy
            elif d == cg.E_:
                uc, along = v, wx
            else:
                uc, along = 1.0 - v, wx
            if sty == cg.M_CENTER:
                if uc < 0.125:
                    lv = L["mark"]
            elif sty == cg.M_DASH:
                if uc < 0.125 and (int(along * 2.0) & 3) < 2:
                    lv = L["mark"]
            elif sty == cg.M_CROSS:
                vc = v if d in (cg.N_, cg.S_) else u
                if 0.15 < vc < 0.85 and (int(uc * 8.0) & 1) == 0:
                    lv = L["mark"]
        elif typ == cg.PAVE:
            lv = L["pave"]
            m = c.curb[iy][ix]
            if (m & 1 and v < 0.125) or (m & 4 and v > 0.875) or (m & 2 and u > 0.875) or (m & 8 and u < 0.125):
                lv = L["curb"]
            elif t < 26.0 and ((int(u * 8.0) & 3) == 0 or (int(v * 8.0) & 3) == 0) and L["pave"] > 1:
                lv = L["pave"] - 1 if (int(u * 8.0) + int(v * 8.0)) & 1 else L["pave"]
        elif typ == cg.GRASS:
            lv = L["grass2"] if (h3(int(wx * 4.0), int(wy * 4.0)) & 7) == 0 else L["grass"]
        elif typ == cg.WATER:
            lv = L["water"]
            if (h3(int(wx * 2.0 + self.stat["frames"] * 0.15), int(wy * 8.0)) & 31) == 0:
                lv = 2
        elif typ == cg.PLAZA:
            lv = L["plaza"] if (int(u * 2.0) + int(v * 2.0)) & 1 else max(0, L["plaza"] - 1)
        elif typ == cg.LOT:
            lv = L["lot"]
            if (int(u * 8.0) % 5) == 0 and 0.1 < v < 0.9:
                lv = L["mark"]
        else:
            lv = L["sand"]
        if L["lit"] > 0.0:                         # night: lamps and headlights add light
            add = 0
            d2 = c.lamp_light(wx, wy)
            if d2 < 1.5:
                add = 1
            if hero is not None:
                fw, lat = hero
                if 3.0 < fw < 30.0 and abs(lat) < 0.9 + fw * 0.17:
                    add += 1
            lv = min(3, lv + add) if add else lv
        return lv

    # ---------------------------------------------------------------- walls
    def wall(self, style, floors, ix, iy, side, u, z, t):
        L = self.L
        fl = int(z / FLOOR)
        vz = z / FLOOR - fl
        tv = 7 - int(vz * 8.0)
        tu = int(u * 8.0) & 7
        base = L["wall"][side]
        if style in (cg.S_BRICK, cg.S_WAREHOUSE) and self.lookname == "day":
            base = max(0, base - 1) if side == 0 else base
        if fl == 0:
            k = h3(ix, iy, 7 + side) & 3
            if style in (cg.S_SHOPS, cg.S_HOTEL) or (style == cg.S_BRICK and k == 0):
                tex = GROUND_FLOOR["shop"]
            elif style == cg.S_WAREHOUSE:
                tex = GROUND_FLOOR["gate"] if k < 2 else WALLS[style]
            else:
                tex = GROUND_FLOOR["door"] if k == 1 else WALLS[style]
            shop = tex is GROUND_FLOOR["shop"]
        else:
            tex = WALLS[style]
            shop = False
        ch = tex[tv][tu]
        if fl == floors - 1 and tv == 0:
            ch = "L"
        if ch == ".":
            return base
        if ch == "L":
            return min(3, base + 1) if self.lookname == "day" else base
        if ch == "D":
            return 0
        if ch == "M":
            return base
        # window
        if L["lit"] > 0.0:
            if shop:
                return 2 if (tu + tv) & 1 or t > 40.0 else 3
            wi = tu >> 2 if style != cg.S_GLASS else 0
            lit = (h3(ix * 4 + wi, iy * 4 + side, fl) & 255) < int(L["lit"] * 255)
            return (3 if t < 120.0 else 2) if lit else 0
        if base == 0:
            return 1
        return 0

    # ---------------------------------------------------------------- frame
    def render(self, cam, sprites, hero_pose=None):
        camx, camy, yaw = cam
        L = self.L
        city = self.city
        st = self.stat
        Fx, Fy = math.sin(yaw), -math.cos(yaw)
        Rx, Ry = math.cos(yaw), math.sin(yaw)
        fb = [[0] * COLS for _ in range(ROWS)]
        zbuf = [1e9] * COLS
        px, py = camx / CELL, camy / CELL
        fogduty, fog0, fogp = L["fog"], L["fog0"], L["fogp"]
        night = L["lit"] > 0.0
        skyw = len(self.sky[0])
        skyh = len(self.sky)
        for i in range(COLS):
            tn = ((i + 0.5) - COLS / 2) / (COLS / 2) * TANHALF
            rx = Fx + Rx * tn                       # world metres per metre of depth
            ry = Fy + Ry * tn
            ix, iy = int(math.floor(px)), int(math.floor(py))
            sx = 1 if rx > 0 else -1
            sy = 1 if ry > 0 else -1
            tdx = CELL / abs(rx) if rx != 0 else 1e9
            tdy = CELL / abs(ry) if ry != 0 else 1e9
            tmx = ((ix + (1 if rx > 0 else 0)) * CELL - camx) / rx if rx != 0 else 1e9
            tmy = ((iy + (1 if ry > 0 else 0)) * CELL - camy) / ry if ry != 0 else 1e9
            typ, hg, sty = city.cell(ix, iy)
            hp = hg * FLOOR
            ytop = ROWS
            t = 0.0
            while True:
                if tmx < tmy:
                    tn_ = tmx
                    tmx += tdx
                    nix, niy, side = ix + sx, iy, 0
                else:
                    tn_ = tmy
                    tmy += tdy
                    nix, niy, side = ix, iy + sy, 1
                t = tn_
                st["cells"] += 1
                # 1. floor of the cell we are leaving
                if hp < CAM_H and ytop > 0:
                    yfar = HORIZON + (CAM_H - hp) * FY / t
                    y0 = int(math.ceil(yfar))
                    if y0 < 0:
                        y0 = 0
                    if y0 < ytop:
                        for r in range(y0, ytop):
                            d = (CAM_H - hp) * FY / (r + 0.5 - HORIZON)
                            wx = px + rx * d / CELL
                            wy = py + ry * d / CELL
                            hero = None
                            if night and hero_pose is not None:
                                hero = (d - CAM_BACK, d * tn)
                            lv = self.ground(typ, sty, ix, iy, wx, wy, d, hero)
                            if d > fog0:
                                f = ((d - fog0) / (MAXD - fog0)) ** fogp
                                lv = lv + (fogduty - lv) * min(1.0, f)
                            fb[r][i] = lv
                        st["ground"] += ytop - y0
                        ytop = y0
                # 2. wall of the cell we are entering
                ntyp, nhg, nsty = city.cell(nix, niy)
                hn = nhg * FLOOR
                if hn > hp:
                    if zbuf[i] > 1e8:
                        zbuf[i] = t
                    yw = HORIZON - (hn - CAM_H) * FY / t
                    y0 = int(math.ceil(yw))
                    if y0 < 0:
                        y0 = 0
                    if y0 < ytop:
                        if side == 0:
                            u = (camy + ry * t) / CELL
                        else:
                            u = (camx + rx * t) / CELL
                        u -= math.floor(u)
                        f = 0.0
                        if t > fog0:
                            f = min(1.0, ((t - fog0) / (MAXD - fog0)) ** fogp)
                        for r in range(y0, ytop):
                            z = CAM_H - (r + 0.5 - HORIZON) * t / FY
                            if z < 0.0:
                                z = 0.0
                            lv = self.wall(nsty, nhg, nix, niy, side, u, z, t)
                            if f > 0.0 and not (night and lv == 3):
                                lv = lv + (fogduty - lv) * f
                            fb[r][i] = lv
                        st["wall"] += ytop - y0
                        ytop = y0
                ix, iy, typ, sty, hp = nix, niy, ntyp, nsty, hn
                if ytop <= 0 or t >= MAXD:
                    break
            # haze between the last ground row and the horizon, then sky
            hz = int(math.ceil(HORIZON))
            if ytop > hz:
                for r in range(hz, ytop):
                    fb[r][i] = fogduty
                ytop = hz
            ang = yaw + math.atan(tn)
            uu = int(ang / (2 * math.pi) * skyw) % skyw
            for r in range(0, ytop):
                v = int(HORIZON) - r
                fb[r][i] = self.sky[min(skyh - 1, max(0, v))][uu]
        # ---- sprites, far to near ----
        order = []
        for s in sprites:
            qx, qy = s["x"] - camx, s["y"] - camy
            t = qx * Fx + qy * Fy
            if t < 1.2 or t > MAXD:
                continue
            lat = qx * Rx + qy * Ry
            if abs(lat) > t * TANHALF + 6.0:
                continue
            order.append((t, lat, s))
        order.sort(key=lambda o: -o[0])
        for t, lat, s in order:
            self.draw_sprite(fb, zbuf, s, t, lat, yaw)
        st["frames"] += 1
        return fb

    def draw_sprite(self, fb, zbuf, s, t, lat, yaw, hero=False):
        L = self.L
        night = L["lit"] > 0.0
        view = math.atan2(s["x"] - self._cam[0], -(s["y"] - self._cam[1])) if not hero else yaw
        rel = view - s.get("hd", 0.0)
        spr = self.bank.get(s["set"], rel)
        rows, w, h, ox, oy = spr.scaled(FY / t)
        colc = COLS / 2 + lat / t / TANHALF * (COLS / 2)
        base = HORIZON + CAM_H * FY / t
        c0 = int(round(colc - ox))
        r0 = int(round(base - oy))
        f = 0.0
        if t > L["fog0"]:
            f = min(1.0, ((t - L["fog0"]) / (MAXD - L["fog0"])) ** L["fogp"])
        dim = night and not s.get("glow", False)
        for x in range(w):
            c = c0 + x
            if c < 0 or c >= COLS or t >= zbuf[c]:
                continue
            self.stat["sprite"] += 1
            for y in range(h):
                v = rows[y][x]
                if v < 0:
                    continue
                r = r0 + y
                if 0 <= r < ROWS:
                    if night and not hero:
                        # unlit bodywork goes one step darker at night, lamps stay bright
                        if v < 3:
                            v = max(0, v - 1)
                    if f > 0.0 and not (night and v == 3):
                        v = v + (L["fog"] - v) * f
                    fb[r][c] = v


def quant(fb):
    return [[min(3, max(0, int(v + 0.5))) for v in row] for row in fb]


# ------------------------------------------------------------------ HUD
FONT = {
    "0": "111101101101111", "1": "010110010010111", "2": "111001111100111",
    "3": "111001111001111", "4": "101101111001001", "5": "111100111001111",
    "6": "111100111101111", "7": "111001010010010", "8": "111101111101111",
    "9": "111101111001111", "$": "011110010011110", " ": "000000000000000",
    "M": "101111111101101", "K": "101101110101101", "H": "101101111101101",
}
HEART = ["01010", "11111", "11111", "01110", "00100"]
STAR = ["00100", "01110", "11111", "01110", "01010"]
GUN = ["1111111", "1111110", "0110000", "0110000", "0110000"]


def text(img, x, y, s, level=3):
    for ch in s:
        g = FONT.get(ch, FONT[" "])
        for r in range(5):
            for c in range(3):
                if g[r * 3 + c] == "1" and 0 <= x + c < 128 and 0 <= y + r < 64:
                    img[y + r][x + c] = level
        x += 4
    return x


def icon(img, x, y, rows, level=3):
    for r, line in enumerate(rows):
        for c, ch in enumerate(line):
            if ch == "1" and 0 <= x + c < 128 and 0 <= y + r < 64:
                img[y + r][x + c] = level


def arrow(img, cx, cy, ang):
    """Objective arrow (Crazy Taxi style), pre-rendered in the real thing."""
    im = Image.new("L", (44, 44), 0)
    d = ImageDraw.Draw(im)
    pts = [(0, -5.0), (3.6, 0.6), (1.3, 0.6), (1.3, 4.6), (-1.3, 4.6), (-1.3, 0.6), (-3.6, 0.6)]
    ca, sa = math.cos(ang), math.sin(ang)
    p = [(22 + (x * ca - y * sa) * 4, 22 + (x * sa + y * ca) * 4) for x, y in pts]
    d.polygon(p, fill=255)
    sm = im.resize((11, 11), Image.BOX)
    px = sm.load()
    on = [[px[x, y] > 110 for x in range(11)] for y in range(11)]
    for y in range(11):
        for x in range(11):
            if on[y][x]:
                continue
            near = any(0 <= x + dx < 11 and 0 <= y + dy < 11 and on[y + dy][x + dx]
                       for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            if near:
                X, Y = cx - 5 + x, cy - 5 + y
                if 0 <= X < 128 and 0 <= Y < 56:
                    img[Y][X] = 0
    for y in range(11):
        for x in range(11):
            if on[y][x]:
                X, Y = cx - 5 + x, cy - 5 + y
                if 0 <= X < 128 and 0 <= Y < 56:
                    img[Y][X] = 3


def compose(levels, hud):
    img = [[0] * 128 for _ in range(64)]
    for r in range(ROWS):
        src, dst = levels[r], img[r]
        for i in range(COLS):
            dst[2 * i] = dst[2 * i + 1] = src[i]
    arrow(img, 58, 7, hud["arrow"])
    for yy in range(3, 10):
        for xx in range(66, 84):
            img[yy][xx] = 0
    text(img, 68, 4, "%03dM" % hud["dist"], 3)
    # strip
    for x in range(128):
        img[ROWS][x] = 1
    icon(img, 1, ROWS + 2, HEART)
    for x in range(8, 8 + 22):
        img[ROWS + 3][x] = 1
        img[ROWS + 4][x] = 1
        img[ROWS + 5][x] = 1
    for x in range(8, 8 + int(22 * hud["health"])):
        img[ROWS + 3][x] = 3
        img[ROWS + 4][x] = 3
        img[ROWS + 5][x] = 3
    icon(img, 34, ROWS + 2, GUN)
    text(img, 43, ROWS + 2, "%02d" % hud["ammo"])
    for k in range(5):
        on = k < hud["wanted"]
        if on and hud["blink"]:
            icon(img, 55 + k * 6, ROWS + 2, STAR, 3)
        elif on:
            icon(img, 55 + k * 6, ROWS + 2, STAR, 2)
        else:
            img[ROWS + 4][57 + k * 6] = 1
    text(img, 92, ROWS + 2, "$%07d" % hud["cash"])
    return img


def to_image(img, scale=5):
    im = Image.new("P", (128, 64))
    pal = []
    for v in LEVEL_RGB:
        pal += [v, v, v]
    im.putpalette(pal + [0] * (768 - len(pal)))
    im.putdata([v for row in img for v in row])
    return im.resize((128 * scale, 64 * scale), Image.NEAREST)


# --------------------------------------------------------------- the drive
def lane_x(av, i):
    return (av[0] + i + 0.5) * CELL


def lane_y(st, i):
    return (st[0] + i + 0.5) * CELL


def build_path(pts, radius=9.0, step=0.25):
    """Polyline with rounded corners -> dense list of (x, y)."""
    out = []
    n = len(pts)
    prev = pts[0]
    for k in range(1, n - 1):
        a, b, c = pts[k - 1], pts[k], pts[k + 1]
        d1 = math.hypot(b[0] - a[0], b[1] - a[1])
        d2 = math.hypot(c[0] - b[0], c[1] - b[1])
        u1 = ((b[0] - a[0]) / d1, (b[1] - a[1]) / d1)
        u2 = ((c[0] - b[0]) / d2, (c[1] - b[1]) / d2)
        p1 = (b[0] - u1[0] * radius, b[1] - u1[1] * radius)
        p2 = (b[0] + u2[0] * radius, b[1] + u2[1] * radius)
        L1 = math.hypot(p1[0] - prev[0], p1[1] - prev[1])
        m = max(1, int(L1 / step))
        for j in range(m):
            out.append((prev[0] + (p1[0] - prev[0]) * j / m, prev[1] + (p1[1] - prev[1]) * j / m))
        m = max(2, int(radius * 1.6 / step))
        for j in range(m):
            s = j / m
            # quadratic bezier through the corner
            x = (1 - s) ** 2 * p1[0] + 2 * (1 - s) * s * b[0] + s * s * p2[0]
            y = (1 - s) ** 2 * p1[1] + 2 * (1 - s) * s * b[1] + s * s * p2[1]
            out.append((x, y))
        prev = p2
    L1 = math.hypot(pts[-1][0] - prev[0], pts[-1][1] - prev[1])
    m = max(1, int(L1 / step))
    for j in range(m + 1):
        out.append((prev[0] + (pts[-1][0] - prev[0]) * j / m, prev[1] + (pts[-1][1] - prev[1]) * j / m))
    return out


class Traffic:
    def __init__(self, city, seed=9):
        rnd = random.Random(seed)
        self.city = city
        self.cars = []
        kinds = ["sedan_l", "sedan_m", "sedan_d", "sedan_m", "taxi", "taxi", "van", "sports", "sedan_d"]
        y0, y1 = city.streets[0][0] * CELL, city.y_end * CELL
        x0, x1 = city.avenues[0][0] * CELL, city.x_end * CELL
        for av in city.avenues:
            for i in range(av[1]):
                south = i < av[1] // 2
                n = 9 if av[1] == 4 else 7
                for k in range(n):
                    self.cars.append(dict(axis="y", x=lane_x(av, i), y=rnd.uniform(y0, y1), v=(1 if south else -1) * rnd.uniform(7, 12),
                                          hd=math.pi if south else 0.0, set=rnd.choice(kinds), lo=y0, hi=y1))
        for stt in city.streets:
            for i in range(stt[1]):
                west = i < stt[1] // 2
                for k in range(7):
                    self.cars.append(dict(axis="x", y=lane_y(stt, i), x=rnd.uniform(x0, x1), v=(-1 if west else 1) * rnd.uniform(7, 12),
                                          hd=-math.pi / 2 if west else math.pi / 2, set=rnd.choice(kinds), lo=x0, hi=x1))
        self.peds = []
        cells = [(x, y) for y in range(city.H) for x in range(city.W) if city.typ[y][x] == cg.PAVE]
        for k in range(1100):
            cx, cy = rnd.choice(cells)
            horiz = rnd.random() < 0.5
            sgn = rnd.choice((-1, 1))
            self.peds.append(dict(x=(cx + rnd.uniform(0.25, 0.75)) * CELL, y=(cy + rnd.uniform(0.25, 0.75)) * CELL,
                                  dx=sgn if horiz else 0, dy=0 if horiz else sgn, kind=rnd.choice("abc"),
                                  ph=rnd.uniform(0, 4), v=rnd.uniform(1.1, 1.7)))
        self.cops = []

    def step(self, dt, n):
        for c in self.cars:
            if c["axis"] == "y":
                c["y"] += c["v"] * dt
                if c["y"] > c["hi"]:
                    c["y"] = c["lo"]
                if c["y"] < c["lo"]:
                    c["y"] = c["hi"]
            else:
                c["x"] += c["v"] * dt
                if c["x"] > c["hi"]:
                    c["x"] = c["lo"]
                if c["x"] < c["lo"]:
                    c["x"] = c["hi"]
        for p in self.peds:
            nx = p["x"] + p["dx"] * p["v"] * dt
            ny = p["y"] + p["dy"] * p["v"] * dt
            if self.city.cell(int(nx / CELL), int(ny / CELL))[0] != cg.PAVE:
                p["dx"], p["dy"] = -p["dx"], -p["dy"]
            else:
                p["x"], p["y"] = nx, ny
            p["ph"] += dt * 6.0

    def sprites(self, n):
        out = []
        for c in self.cars:
            out.append(dict(x=c["x"], y=c["y"], hd=c["hd"], set=c["set"]))
        for c in self.cops:
            out.append(dict(x=c["x"], y=c["y"], hd=c["hd"], set="police%d" % ((n // 3) & 1)))
        for p in self.peds:
            hd = math.atan2(p["dx"], -p["dy"])
            out.append(dict(x=p["x"], y=p["y"], hd=hd, set="ped_%s%d" % (p["kind"], int(p["ph"]) & 3)))
        for (tx, ty) in self.city.trees:
            out.append(dict(x=tx * CELL, y=ty * CELL, set="tree"))
        for (lx, ly) in self.city.lamps:
            out.append(dict(x=lx * CELL, y=ly * CELL, set="lamp", hd=0.0, glow=True))
        return out


def main():
    look = sys.argv[1] if len(sys.argv) > 1 else "day"
    frames = int(sys.argv[2]) if len(sys.argv) > 2 else 240
    speed = float(sys.argv[3]) if len(sys.argv) > 3 else 19.0          # m/s
    city = City()
    bank = build_bank()
    R = Renderer(city, bank, look)
    tr = Traffic(city)
    av = city.avenues[4]            # a 4-lane avenue through downtown
    stt = city.bridge               # the 4-lane street that leads to the bridge
    av2 = city.avenues[6]
    x_n = lane_x(av, 2)             # inner northbound lane
    y_e = lane_y(stt, 2)            # inner eastbound lane
    x_n2 = lane_x(av2, 1)           # northbound lane of a 2-lane avenue
    route = [(x_n, 128 * CELL), (x_n, y_e), (x_n2, y_e), (x_n2, 40 * CELL)]
    path = build_path(route)
    # two police cars: one oncoming on the avenue, one waiting on the cross street
    tr.cops.append(dict(x=lane_x(av, 3), y=121 * CELL, hd=0.0, vy=-11.0, vx=0.0))
    tr.cops.append(dict(x=lane_x(av2, 0), y=44 * CELL, hd=math.pi, vy=13.0, vx=0.0))
    target = (x_n2, 40 * CELL)
    dt = 1.0 / 20.0
    ims = []
    pos = 0.0
    camyaw = None
    for n in range(frames):
        k = min(len(path) - 2, int(pos / 0.25))
        x, y = path[k]
        k2 = min(len(path) - 1, k + 8)
        hd = math.atan2(path[k2][0] - x, -(path[k2][1] - y))
        if camyaw is None:
            camyaw = hd
        dy = (hd - camyaw + math.pi) % (2 * math.pi) - math.pi
        camyaw += dy * 0.16
        camx = x - math.sin(camyaw) * CAM_BACK
        camy = y + math.cos(camyaw) * CAM_BACK
        tr.step(dt, n)
        for c in tr.cops:
            c["y"] += c["vy"] * dt
        sprites = tr.sprites(n)
        # keep traffic out of the player's bumper
        sprites = [s for s in sprites if not (s["set"][:3] not in ("ped", "tre", "lam")
                                                and math.hypot(s["x"] - x, s["y"] - y) < 5.0)]
        R._cam = (camx, camy)
        fb = R.render((camx, camy, camyaw), sprites, hero_pose=(x, y, hd))
        # the player's car, always in front of the camera
        hero = dict(x=x, y=y, hd=hd, set="hero", glow=True)
        zb = [1e9] * COLS
        R.draw_sprite(fb, zb, hero, CAM_BACK, 0.0, camyaw, hero=True)
        ta = math.atan2(target[0] - x, -(target[1] - y)) - camyaw
        hud = dict(arrow=ta, dist=min(999, int(math.hypot(target[0] - x, target[1] - y))), health=0.8,
                   ammo=17, wanted=2, blink=(n // 4) & 1, cash=12500 + (n // 20) * 50)
        ims.append(to_image(compose(quant(fb), hud)))
        pos += speed * dt
    tag = "city_" + look
    ims[0].save(os.path.join(HERE, tag + ".gif"), save_all=True, append_images=ims[1:],
                duration=50, loop=0, optimize=False, disposal=1)
    sheet = Image.new("RGB", (3 * 645 + 5, 3 * 325 + 5), (40, 40, 60))
    for k in range(9):
        im = ims[min(frames - 1, int(k * (frames - 1) / 8))].convert("RGB")
        sheet.paste(im, (5 + (k % 3) * 645, 5 + (k // 3) * 325))
    sheet = sheet.resize((sheet.width * 2 // 3, sheet.height * 2 // 3), Image.LANCZOS)
    sheet.save(os.path.join(HERE, tag + "_sheet.png"))
    f = R.stat["frames"]
    print("%s: per frame -> cell fetches %.0f, wall px %.0f, ground px %.0f, sprite columns %.0f" % (
        tag, R.stat["cells"] / f, R.stat["wall"] / f, R.stat["ground"] / f, R.stat["sprite"] / f))
    print("gif bytes", os.path.getsize(os.path.join(HERE, tag + ".gif")))


if __name__ == "__main__":
    main()
