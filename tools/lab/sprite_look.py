#!/usr/bin/env python3
"""A look at models as the game will show them: every one at a row of sizes,
on the greys of the street, enlarged, dots twice as wide as high.

  python3 tools/lab/sprite_look.py out.png phone mark person
"""
import math, os, sys
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sprites as sp

PAL = [(0, 0, 0), (156, 156, 156), (215, 215, 215), (255, 255, 255)]
MODELS = {
    "phone": lambda: (sp.phone(), None),
    "mark": lambda: (sp.mark(), (2, 3)),
    "person": lambda: (sp.person(0.95, 0), (1, 12)),
    "lamp": lambda: (sp.lamp(True), None),
    "tree": lambda: (sp.tree(), None),
    "both": lambda: (sp.phone() + sp.mark(), None),
}


def main():
    out = sys.argv[1]
    names = sys.argv[2:]
    zoom = 3
    sizes = [16.0 * 2.0 ** (-k / 6.0) for k in (0, 3, 6, 9, 12, 15, 18)]
    high = 130
    sheet = Image.new("RGB", (1300, high * 3 * len(names)), (60, 60, 90))
    for row, name in enumerate(names):
        faces, outline = MODELS[name]()
        for band, back in enumerate((PAL[0], PAL[1], PAL[2])):
            top = (row * 3 + band) * high
            for yy in range(high - 4):
                for xx in range(sheet.width):
                    sheet.putpixel((xx, top + yy), back)
            x = 10
            for angle in (0.0, 0.6):
                s = sp.Sprite(faces, angle, 6.0, outline)
                for ppm in sizes:
                    rows, w, h, ox, oy = s.scaled(ppm)
                    for y in range(h):
                        for xk in range(w):
                            v = rows[y][xk]
                            if v < 0:
                                continue
                            for dy in range(zoom):
                                for dx in range(zoom * 2):
                                    px, py = x + xk * zoom * 2 + dx, top + 4 + y * zoom + dy
                                    if px < sheet.width and py < top + high - 4:
                                        sheet.putpixel((px, py), PAL[v])
                    x += w * zoom * 2 + 14
    sheet.save(out)
    print("written:", out)


if __name__ == "__main__":
    main()
