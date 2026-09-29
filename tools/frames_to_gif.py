#!/usr/bin/env python3
"""
Turn the raw frame dump of the desktop test build into a GIF and a contact sheet.

  python3 tools/frames_to_gif.py build/host/frames.raw build/host/run [ms per frame]

Frames are 128 x 64 bytes, one level (0..3) per pixel.
"""
import os, sys
from PIL import Image

LEVEL_RGB = (0, 156, 215, 255)     # how the 4 levels look on the panel


def load(path):
    data = open(path, "rb").read()
    n = len(data) // (128 * 64)
    pal = []
    for v in LEVEL_RGB:
        pal += [v, v, v]
    pal += [0] * (768 - len(pal))
    frames = []
    for i in range(n):
        im = Image.frombytes("P", (128, 64), data[i * 8192:(i + 1) * 8192])
        im.putpalette(pal)
        frames.append(im)
    return frames


def main():
    src, dst = sys.argv[1], sys.argv[2]
    ms = int(sys.argv[3]) if len(sys.argv) > 3 else 45
    frames = load(src)
    big = [f.resize((640, 320), Image.NEAREST) for f in frames]
    big[0].save(dst + ".gif", save_all=True, append_images=big[1:], duration=ms, loop=0, disposal=1)
    n = len(frames)
    cols, rows = 3, 3
    sheet = Image.new("RGB", (cols * 645 + 5, rows * 325 + 5), (40, 40, 60))
    for k in range(cols * rows):
        i = min(n - 1, int(k * (n - 1) / (cols * rows - 1)))
        sheet.paste(big[i].convert("RGB"), (5 + (k % cols) * 645, 5 + (k // cols) * 325))
    sheet = sheet.resize((sheet.width * 2 // 3, sheet.height * 2 // 3), Image.LANCZOS)
    sheet.save(dst + "_sheet.png")
    print("%d frames -> %s.gif (%d bytes), %s_sheet.png" % (n, dst, os.path.getsize(dst + ".gif"), dst))


if __name__ == "__main__":
    main()
