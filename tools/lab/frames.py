#!/usr/bin/env python3
"""Pictures out of a run of the desktop build: the frames asked for, side by
side and one under the other, enlarged.

  python3 tools/lab/frames.py build/jobs/m1.raw sheet.png 100 146 300 [...]   these frames
  python3 tools/lab/frames.py build/jobs/m1.raw sheet.png 100-200/20           every 20th of these
"""
import sys
from PIL import Image

SHADES = [0, 156, 215, 255]


def main():
    raw, out = sys.argv[1], sys.argv[2]
    wanted = []
    for a in sys.argv[3:]:
        if "-" in a:
            span, _, step = a.partition("/")
            lo, hi = span.split("-")
            wanted += list(range(int(lo), int(hi) + 1, int(step or 1)))
        else:
            wanted.append(int(a))
    data = open(raw, "rb").read()
    zoom, per_row = 3, 3
    rows = (len(wanted) + per_row - 1) // per_row
    sheet = Image.new("L", (per_row * (128 * zoom + 8) + 8, rows * (64 * zoom + 8) + 8), 60)
    for k, n in enumerate(wanted):
        f = data[n * 8192:(n + 1) * 8192]
        if len(f) < 8192:
            continue
        img = Image.new("L", (128, 64))
        img.putdata([SHADES[v & 3] for v in f])
        img = img.resize((128 * zoom, 64 * zoom), Image.NEAREST)
        sheet.paste(img, (8 + (k % per_row) * (128 * zoom + 8), 8 + (k // per_row) * (64 * zoom + 8)))
    sheet.save(out)
    print("written:", out, "frames", wanted)


if __name__ == "__main__":
    main()
