#!/usr/bin/env python3
"""Two shades instead of four: how the game would look in black and white.

The four shades are said to flicker on the FX-C, so the game gets a setting
that shows the same picture in two. The display routine then turns every dot
of the 2-bit picture into its two panel dots as before, and the two levels in
between black and white into a pattern over those two dots and two rows.
Which pattern is a matter of looking: this draws the candidates from scenes
the desktop build has played (build/post/<scene>.raw, made by
tools/post_clip.py record), so they can be judged before one goes into
display.S.

  python3 tools/lab/shades.py          build/post/shades/<scene>-<frame>.png, one sheet each,
                                       and page.html with all of them

A sheet shows the same picture in the four shades and in every candidate,
twice its size. The panel's dots are read the way display.S sends them: the
left panel dot of a view dot is the "hi" copy, the right one the "lo" copy,
rows counted from the top of the picture.
"""
import base64, io, os, sys
from PIL import Image, ImageDraw

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")) + "/"
RAW = ROOT + "build/post/"
OUT = ROOT + "build/post/shades/"
W, H = 128, 64
SHADES = (0, 156, 215, 255)          # the four levels as the panel shows them (tools/frames_to_gif.py)
ZOOM = 2

# scene, frame: what is looked at
PICKS = [
    ("start", 150), ("start", 470), ("jack", 150), ("bridge", 90), ("park", 70),
    ("cops", 85), ("taxi", 70), ("shoot", 70), ("busted", 240), ("busted", 400),
    ("flee", 150), ("chase", 630), ("frenzy", 280), ("hit", 300), ("start", 15), ("map", 60),
]


def lit_light(level, x, y):
    """level 2 and 3 white, 0 and 1 black: a plain threshold."""
    return level >= 2


def lit_124(level, x, y):
    """level 1: one panel dot in four (top left); level 2: a checkerboard; level 3: all four."""
    if level == 3: return True
    if level == 2: return (x & 1) == (y & 1)
    if level == 1: return not (x & 1) and not (y & 1)
    return False


def lit_134(level, x, y):
    """level 1: one dot in four; level 2: three in four; level 3: all."""
    if level == 3: return True
    if level == 2: return not ((x & 1) and (y & 1))
    if level == 1: return not (x & 1) and not (y & 1)
    return False


def lit_234(level, x, y):
    """level 1: a checkerboard; level 2: three in four; level 3: all."""
    if level == 3: return True
    if level == 2: return not ((x & 1) and (y & 1))
    if level == 1: return (x & 1) == (y & 1)
    return False


# name, what the display routine would do, in the order they are shown
WAYS = [
    ("FOUR SHADES", None),
    ("LIGHT: 2 AND 3 WHITE", lit_light),
    ("DOTS 1-2-4", lit_124),
    ("DOTS 1-3-4", lit_134),
    ("DOTS 2-3-4", lit_234),
]


def frame(scene, n):
    with open(RAW + scene + ".raw", "rb") as f:
        f.seek(n * W * H)
        return f.read(W * H)


def picture(levels, way):
    im = Image.new("L", (W, H))
    px = im.load()
    for y in range(H):
        for x in range(W):
            level = levels[y * W + x]
            px[x, y] = SHADES[level] if way is None else (255 if way(level, x, y) else 0)
    return im


def sheet(scene, n):
    levels = frame(scene, n)
    gap, top = 8, 14
    sh = Image.new("L", ((W * ZOOM + gap) * len(WAYS) + gap, H * ZOOM + top + gap), 40)
    d = ImageDraw.Draw(sh)
    for i, (name, way) in enumerate(WAYS):
        x = gap + i * (W * ZOOM + gap)
        d.text((x, 2), name, fill=255)
        sh.paste(picture(levels, way).resize((W * ZOOM, H * ZOOM), Image.NEAREST), (x, top))
    return sh


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = []
    for scene, n in PICKS:
        if not os.path.exists(RAW + scene + ".raw"):
            print("no %s.raw: python3 tools/post_clip.py record first" % scene)
            continue
        name = "%s-%d" % (scene, n)
        sh = sheet(scene, n)
        sh.save(OUT + name + ".png")
        buf = io.BytesIO()
        sh.save(buf, "PNG")
        rows.append((name, base64.b64encode(buf.getvalue()).decode()))
        print("wrote", OUT + name + ".png")
    with open(OUT + "page.html", "w") as f:
        f.write("<!doctype html><title>Two shades</title><body style='background:#282828;color:#ddd;font-family:sans-serif'>\n")
        f.write("<p>%s</p>\n" % " | ".join(n for n, _ in WAYS))
        for name, data in rows:
            f.write("<p>%s<br><img style='image-rendering:pixelated' src='data:image/png;base64,%s'></p>\n" % (name, data))
    print("page:", OUT + "page.html")


if __name__ == "__main__":
    main()
