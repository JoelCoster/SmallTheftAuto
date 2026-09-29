#!/usr/bin/env python3
"""The clip and the pictures for showing the game to other people.

The desktop build (host/host_main.cpp: the game's own code, with a fake
flash chip) plays the scenes listed below at 24 pictures a second (the
console shows 18 to 25 in the street) and writes every picture to disk. The
cut takes stretches of them, one after the other, with a line of text above
the picture.

  python3 tools/post_clip.py record            play the scenes (build/post/<scene>.raw, .log)
  python3 tools/post_clip.py sheet shoot 40-700/30   look at a scene: build/post/sheet-shoot.png
  python3 tools/post_clip.py cut               the tour, the short one and single pictures, into post/
  python3 tools/post_clip.py own film.mov [from [long]]
                                               a film of one's own, made small enough for the forum
                                               (7 MB): post/console.mp4; from so many seconds in, so
                                               many seconds long. Where it was taken is left out.

The game data is taken from build/game (tools/build.sh makes it).
Nothing here goes on the console.
"""
import hashlib, os, shutil, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")) + "/"
OUT = ROOT + "build/post/"          # what is played, and everything in between
POST = ROOT + "post/"               # what is shown to people
DATA = ROOT + "build/game/fxdata.bin"
TICKS = "6.5"                       # a frame: 6.5 of the 156 ticks a second, 24 pictures a second
FPS = 24
SHADES = (0, 156, 215, 255)         # how the 4 levels look on the panel (tools/frames_to_gif.py)
W, H = 128, 64

# the first mission's drive, as tools/lab/regress.py has it
GARAGE = "drive:93,153.5;drive:110,153.5;drive:112.5,151;drive:112.5,116;drive:114.5,113.5;drive:119,113.5;stop"

# name: frames, what is set for it
SCENES = {
    "start": (1000, {"SCENE": "pages", "SEED": "3",
                     "PLAY": "wait:50;b;wait:25;walk:91.4,154.6;down;wait:110;b;wait:12;car;" + GARAGE + ";wait:150"}),
    "jack": (500, {"SCENE": "jack", "SEED": "2", "DONE": "444"}),
    "shoot": (800, {"SCENE": "shoot", "SEED": "3", "DONE": "444"}),
    "busted": (420, {"SCENE": "busted", "SEED": "9", "DONE": "444"}),
    "chase": (700, {"SCENE": "chase", "SEED": "9", "DONE": "444"}),
    "flee": (800, {"SCENE": "flee", "STARS": "2", "SEED": "11", "DONE": "444"}),
    "map": (420, {"DONE": "100", "CASH": "100",
                  "PLAY": "wait:30;map;wait:50;hold:40,28;hold:10,10;wait:14;b;wait:25;car;drive:93,153.5;drive:110,153.5;wait:30"}),
    "frenzy": (900, {"DONE": "300", "SEED": "5", "CASH": "700",
                     "PLAY": "walk:91.2,154.6;down;wait:110;b;spree;wait:120"}),
    "hit": (1000, {"DONE": "200", "CASH": "300",
                   "PLAY": "walk:91.2,154.6;down;wait:110;b;walk:84.5,154.5;walk:84.5,149.6;hunt:3;flee;wait:120"}),
    "bridge": (520, {"SCENE": "people", "DONE": "444",
                     "PLAY": "at:159.5,208.4;kind:5;drive:164,208.4;drive:176,208.4;drive:190,208.4;drive:203,208.4;wait:20"}),
    "cops": (420, {"SCENE": "people", "DONE": "444",
                   "PLAY": "at:100.5,113.5;kind:6;drive:109,113.5;drive:123,113.5;drive:141,113.5;wait:20"}),
    "taxi": (420, {"SCENE": "people", "DONE": "444", "SEED": "4",
                   "PLAY": "at:128.4,147;kind:3;drive:128.4,140;drive:128.4,127;drive:128.4,114;drive:128.4,100;wait:20"}),
    "van": (420, {"SCENE": "people", "DONE": "444", "SEED": "6",
                  "PLAY": "at:50,153.4;kind:4;drive:56,153.4;drive:75,153.4;drive:95,153.4;wait:20"}),
    "park": (520, {"DONE": "444", "SEED": "2",
                   "PLAY": "at:113.5,111.4;walk:115.6,109.4;walk:116.0,103.0;walk:118.5,101.4;run:123.0,101.4;wait:20"}),
}

# The tour: scene, first and last frame, the line of text above the picture
TOUR = [
    ("start", 0, 49, "FOR THE ARDUBOY FX"),
    ("start", 100, 199, "A CITY IN 3D"),
    ("start", 200, 308, "TELEPHONES RING WITH WORK"),
    ("start", 345, 440, "ANY CAR WILL DO"),
    ("start", 441, 560, "AN ARROW SHOWS THE WAY"),
    ("start", 770, 900, "TWELVE MISSIONS"),
    ("jack", 70, 230, "OR STOP ONE AND TAKE IT"),
    ("bridge", 35, 150, "TWO ISLANDS, TWO BRIDGES"),
    ("park", 20, 125, "PARKS AND PLAZAS"),
    ("taxi", 30, 110, "TAXIS"),
    ("van", 70, 140, "VANS"),
    ("cops", 45, 125, "POLICE CARS"),
    ("shoot", 20, 120, "NOBODY SAYS YOU HAVE TO BE NICE"),
    ("shoot", 230, 330, "NOBODY SAYS YOU HAVE TO BE NICE"),
    ("busted", 40, 130, "THE POLICE TAKE NOTICE"),
    ("busted", 170, 290, "THE POLICE TAKE NOTICE"),
    ("flee", 75, 230, "LOSE THEM"),
    ("chase", 570, 690, "OR DON'T"),
    ("frenzy", 232, 330, "FRENZY: TEN IN SIXTY SECONDS"),
    ("frenzy", 440, 580, "FRENZY: TEN IN SIXTY SECONDS"),
    ("hit", 440, 600, "CONTRACTS"),
    ("map", 35, 152, "A MAP OF ALL OF IT"),
    ("map", 153, 260, "SET A MARKER, FOLLOW THE ARROW"),
]
# what the last picture of the tour says, and for how many frames
END = (84, "SMALL THEFT AUTO", ["ARDUBOY FX: 8 BIT, 16 MHZ, 2.5 KB OF RAM",
                                "PROGRAM 26 KB; CITY, CARS AND PEOPLE 1.1 MB ON THE FLASH CHIP",
                                "18 TO 25 PICTURES A SECOND IN FOUR SHADES"])

# The short one, without text, to go round and round at the top of a post
SHORT = [
    ("start", 0, 24),
    ("jack", 118, 225),
    ("shoot", 96, 160),
    ("bridge", 40, 110),
    ("busted", 196, 270),
    ("flee", 78, 170),
    ("park", 30, 90),
    ("frenzy", 440, 560),
]

# single pictures: name, scene, frame
STILLS = [
    ("title", "start", 10),
    ("street", "jack", 200),
    ("mission", "start", 250),
    ("passed", "start", 850),
    ("police", "shoot", 290),
    ("busted", "busted", 250),
    ("bridge", "bridge", 60),
    ("park", "park", 30),
    ("map", "map", 120),
]

ZOOM = 5                            # 640 x 320, under a strip of 40 for the text
STRIP = 40
FONT = "/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf"


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        sys.exit("%s\n%s" % (" ".join(cmd), (r.stderr or r.stdout)[-3000:]))
    return r


def build():
    os.makedirs(OUT, exist_ok=True)
    run(["clang++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Wno-unused-function", "-Wno-ignored-attributes",
         "-DHOST", "-o", OUT + "host_sim", ROOT + "host/host_main.cpp"])


def stamp(name):
    frames, env = SCENES[name]
    h = hashlib.sha256()
    for p in (OUT + "host_sim", DATA):
        with open(p, "rb") as f:
            h.update(f.read())
    h.update(repr((frames, sorted(env.items()), TICKS)).encode())
    return h.hexdigest()


def record(only=None):
    build()
    for name, (frames, env) in SCENES.items():
        if only and name not in only:
            continue
        mark = OUT + name + ".stamp"
        if os.path.exists(mark) and os.path.exists(OUT + name + ".raw") and open(mark).read() == stamp(name):
            continue
        e = dict(os.environ)
        for k in ("SCENE", "SEED", "STARS", "FOOT", "STILL", "TRACE", "NAV_TO", "HERO_AT", "SETTINGS", "RANGE", "LIST",
                  "PLAY", "CASH", "DONE"):
            e.pop(k, None)
        e.update(env)
        r = run([OUT + "host_sim", DATA, OUT + name + ".raw", str(frames), TICKS], env=e)
        with open(OUT + name + ".log", "w") as f:
            f.write(r.stdout)
        with open(mark, "w") as f:
            f.write(stamp(name))
        print("played: %-8s %4d frames, %.0f s" % (name, frames, frames / FPS))


_raw = {}


def picture(scene, n):
    """One picture of a scene, 128 x 64, levels 0..3."""
    if scene not in _raw:
        with open(OUT + scene + ".raw", "rb") as f:
            _raw[scene] = f.read()
    d = _raw[scene][n * W * H:(n + 1) * W * H]
    if len(d) < W * H:
        sys.exit("%s has no frame %d" % (scene, n))
    return d


def grey(data, zoom):
    img = Image.frombytes("L", (W, H), bytes(SHADES[v & 3] for v in data))
    return img.resize((W * zoom, H * zoom), Image.NEAREST)


def span(text):
    out = []
    for a in text.split():
        part, _, step = a.partition("/")
        lo, _, hi = part.partition("-")
        out += list(range(int(lo), int(hi or lo) + 1, int(step or 1)))
    return out


def sheet(scene, which, per_row=4, zoom=2):
    wanted = span(which)
    rows = (len(wanted) + per_row - 1) // per_row
    cw, ch = W * zoom + 6, H * zoom + 18
    img = Image.new("L", (per_row * cw + 6, rows * ch + 6), 60)
    draw = ImageDraw.Draw(img)
    for k, n in enumerate(wanted):
        x, y = 6 + (k % per_row) * cw, 6 + (k // per_row) * ch
        img.paste(grey(picture(scene, n), zoom), (x, y + 12))
        draw.text((x, y), "%s %d" % (scene, n), fill=255)
    path = OUT + "sheet-" + scene + ".png"
    img.save(path)
    print("written:", path)


def font(size):
    try:
        return ImageFont.truetype(FONT, size)
    except OSError:
        return ImageFont.load_default()


_strips = {}


def strip(text):
    """The line of text above the picture; the name of the game at the right."""
    if text not in _strips:
        img = Image.new("L", (W * ZOOM, STRIP), 0)
        draw = ImageDraw.Draw(img)
        f = font(30)
        draw.text((12, STRIP // 2 + 3), text, font=f, fill=255, anchor="lm")
        draw.text((W * ZOOM - 12, STRIP // 2 + 3), "SMALL THEFT AUTO", font=font(22), fill=SHADES[1], anchor="rm")
        _strips[text] = img
    return _strips[text]


def end_card():
    frames, big, lines = END
    img = Image.new("L", (W * ZOOM, H * ZOOM + STRIP), 0)
    draw = ImageDraw.Draw(img)
    draw.text((W * ZOOM // 2, 118), big, font=font(96), fill=255, anchor="mm")
    for k, line in enumerate(lines):
        draw.text((W * ZOOM // 2, 204 + 38 * k), line, font=font(28), fill=SHADES[2], anchor="mm")
    return [img] * frames


def tour_pictures():
    out = []
    for scene, a, b, text in TOUR:
        for n in range(a, b + 1):
            img = Image.new("L", (W * ZOOM, H * ZOOM + STRIP), 0)
            img.paste(strip(text), (0, 0))
            img.paste(grey(picture(scene, n), ZOOM), (0, STRIP))
            out.append(img)
    return out + end_card()


def video(pictures, path, bits):
    tool = OUT + "frames_to_mp4"
    src = ROOT + "tools/lab/frames_to_mp4.swift"
    if not os.path.exists(tool) or os.path.getmtime(tool) < os.path.getmtime(src):
        run(["swiftc", "-O", "-o", tool, src])
    folder = OUT + "frames/"
    os.makedirs(folder, exist_ok=True)
    for f in os.listdir(folder):
        os.remove(folder + f)
    for i, img in enumerate(pictures):
        img.save(folder + "f%05d.png" % i)
    print(run([tool, folder, path, str(FPS), str(bits)]).stdout.strip())
    for f in os.listdir(folder):
        os.remove(folder + f)
    os.rmdir(folder)


def loop(path):
    pal = []
    for v in SHADES:
        pal += [v, v, v]
    pal += [0] * (768 - len(pal))
    out = []
    for scene, a, b in SHORT:
        for n in range(a, b + 1):
            img = Image.frombytes("P", (W, H), bytes(v & 3 for v in picture(scene, n)))
            img.putpalette(pal)
            out.append(img.resize((W * ZOOM, H * ZOOM), Image.NEAREST))
    # (a GIF counts in hundredths of a second: 4 of them a picture, 25 a second)
    out[0].save(path, save_all=True, append_images=out[1:], duration=40, loop=0, optimize=False, disposal=1)
    print("%d pictures, %.1f s -> %s, %.2f MB" % (len(out), len(out) / 25, os.path.basename(path),
                                                   os.path.getsize(path) / 1e6))


def cut():
    record()
    os.makedirs(POST, exist_ok=True)
    video(tour_pictures(), POST + "tour.mp4", 700000)
    loop(POST + "clip.gif")
    for name, scene, n in STILLS:
        grey(picture(scene, n), ZOOM).save(POST + "picture-" + name + ".png")
    print("single pictures: " + ", ".join("picture-%s.png" % name for name, _, _ in STILLS))
    # the game itself, as it was built last
    shutil.copyfile(ROOT + "build/game/SmallTheftAuto.arduboy", POST + "SmallTheftAuto.arduboy")
    print("the game: SmallTheftAuto.arduboy, %d KB" % (os.path.getsize(POST + "SmallTheftAuto.arduboy") // 1024))

LIMIT = 6.8e6                       # the forum takes 7168 KB (read from its settings, 2026-09-29)


def own(film, start=None, length=None):
    """A film from a telephone is a .mov of many MB: the forum takes neither.
    macOS's own avconvert makes an .mp4 of it, the best of its sizes that fits.
    (It leaves out what the telephone noted about the place, unless told not to.)"""
    os.makedirs(POST, exist_ok=True)
    path = POST + "console.mp4"
    for preset in ("Preset1280x720", "Preset960x540", "Preset640x480", "PresetMediumQuality", "PresetLowQuality"):
        cmd = ["avconvert", "--source", film, "--output", path, "--preset", preset, "--replace"]
        if start:
            cmd += ["--start", start]
        if length:
            cmd += ["--duration", length]
        run(cmd)
        size = os.path.getsize(path)
        print("%-20s %.1f MB" % (preset, size / 1e6))
        if size <= LIMIT:
            print("written: post/console.mp4")
            return
    os.remove(path)
    sys.exit("Too long for 7 MB even at the smallest size: take a part of it (from, long), or put it on YouTube.")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    what = sys.argv[1]
    if what == "record":
        record(sys.argv[2:])
    elif what == "sheet":
        sheet(sys.argv[2], " ".join(sys.argv[3:]))
    elif what == "cut":
        cut()
    elif what == "own" and len(sys.argv) > 2:
        own(*sys.argv[2:5])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
