#!/usr/bin/env python3
"""
Small Theft Auto: the arrow that shows the way.

It is the arrow of the concept clip (preview/city_day.gif): white, with a
black line round it, 11 x 11 single dots, in 32 directions. The 3D view has
dots twice as wide, so the arrow is not part of the picture the game draws:
the display routine lays it over the view while sending it (display.S). For
that it wants, for every column of dots, what to keep of the view and what to
light up; pack() puts an arrow into that form.

    python3 tools/arrows.py sheet.png      all 32, enlarged, to look at
"""
import math, sys

N = 11                      # dots each way, the black line included
DIRECTIONS = 32
# the place the display routine gives the arrow: 6 columns of the view
# (12 columns of dots) by 16 rows; the arrow stands one dot in and one down
WINDOW_COLS, WINDOW_ROWS = 12, 16
AT_X, AT_Y = 1, 1

# pointing up, in dots from the middle: tip, head, shaft
SHAPE = [(0, -5.0), (3.6, 0.6), (1.3, 0.6), (1.3, 4.6), (-1.3, 4.6), (-1.3, 0.6), (-3.6, 0.6)]
COVER = 0.43                # how much of a dot the arrow has to cover to light it


def _inside(p, x, y):
    hit = False
    j = len(p) - 1
    for i in range(len(p)):
        xi, yi = p[i]
        xj, yj = p[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            hit = not hit
        j = i
    return hit


def _drawn(angle, fine=8):
    """The white of the arrow: True where a dot is lit."""
    c, s = math.cos(angle), math.sin(angle)
    p = [(x * c - y * s, x * s + y * c) for x, y in SHAPE]
    out = []
    for r in range(N):
        row = []
        for q in range(N):
            n = 0
            for a in range(fine):
                for b in range(fine):
                    x = q - N / 2.0 + (a + 0.5) / fine
                    y = r - N / 2.0 + (b + 0.5) / fine
                    n += _inside(p, x, y)
            row.append(n >= COVER * fine * fine)
        out.append(row)
    return out


def _white(k):
    """Direction k of 32, clockwise from straight up. Only the first eighth
    of the turn is drawn; the rest is the same pictures mirrored and turned,
    so that the arrow looks the same whichever way it points."""
    quarter, r = divmod(k % DIRECTIONS, DIRECTIONS // 4)
    if r <= DIRECTIONS // 8:
        g = _drawn(2 * math.pi * r / DIRECTIONS)
    else:
        # mirrored in the diagonal: what points up points right
        d = _drawn(2 * math.pi * (DIRECTIONS // 4 - r) / DIRECTIONS)
        g = [[d[N - 1 - x][N - 1 - y] for x in range(N)] for y in range(N)]
    for _ in range(quarter):
        # a quarter turn to the right
        g = [[g[N - 1 - x][y] for x in range(N)] for y in range(N)]
    return g


def arrow(k):
    """Rows of 0 (nothing), 1 (the black line) and 2 (white)."""
    w = _white(k)
    out = [[0] * N for _ in range(N)]
    for y in range(N):
        for x in range(N):
            if w[y][x]:
                out[y][x] = 2
            elif any(0 <= x + dx < N and 0 <= y + dy < N and w[y + dy][x + dx]
                     for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                out[y][x] = 1
    return out


def pack(k):
    """For the display routine: the upper 8 rows first, then the lower 8;
    for every column of the view four bytes: what to keep of the view and
    what to light up, for its left column of dots and for its right one."""
    a = arrow(k)
    out = bytearray()
    for page in range(WINDOW_ROWS // 8):
        for x in range(WINDOW_COLS):
            keep = dots = 0
            for bit in range(8):
                gx, gy = x - AT_X, page * 8 + bit - AT_Y
                v = a[gy][gx] if 0 <= gx < N and 0 <= gy < N else 0
                if v == 0:
                    keep |= 1 << bit
                if v == 2:
                    dots |= 1 << bit
            out += bytes([keep, dots])
    return bytes(out)


def pack_all():
    return b"".join(pack(k) for k in range(DIRECTIONS))


def main():
    from PIL import Image
    out = sys.argv[1] if len(sys.argv) > 1 else "arrows.png"
    zoom = 8
    shades = [(0, 0, 0), (156, 156, 156), (215, 215, 215), (255, 255, 255)]
    per_row = 16
    sheet = Image.new("RGB", (per_row * 13 * zoom + 16, 4 * 13 * zoom + 16), shades[1])
    px = sheet.load()
    for ground in range(2):
        for k in range(DIRECTIONS):
            a = arrow(k)
            ox = 8 + (k % per_row) * 13 * zoom
            oy = 8 + (ground * 2 + k // per_row) * 13 * zoom
            for y in range(13):
                for x in range(13):
                    v = a[y - 1][x - 1] if 1 <= x <= N and 1 <= y <= N else 0
                    shade = shades[3] if v == 2 else shades[0] if v == 1 else shades[1 + ground]
                    for dy in range(zoom):
                        for dx in range(zoom):
                            px[ox + x * zoom + dx, oy + y * zoom + dy] = shade
    sheet.save(out)
    print("written:", out)
    for k in (0, 1, 2, 3, 4):
        print("direction %d" % k)
        for row in arrow(k):
            print("   " + "".join(" .#"[v] if v != 1 else "o" for v in row))


if __name__ == "__main__":
    main()
