#!/usr/bin/env python3
"""
The computer's end of the test build (EXTRA_FLAGS=-DDIAG OUT=diag tools/build.sh).

  python3 tools/diag.py load            put build/diag's program straight into the
                                        console's processor and start it. The game
                                        list on the flash chip is not touched. If
                                        the list holds this build's game data, the
                                        program uses it; if not, the data goes to
                                        the very end of the chip, which the list
                                        does not reach.
  python3 tools/diag.py load game       the same with the game as it is played
                                        (build/game), or any other build by the name
                                        of its folder. The game as it is played has no
                                        USB connection: once it runs the computer does
                                        not see the console, until Up and Down are held
                                        for two seconds (back to the console's menu)
  python3 tools/diag.py watch 10 2:s 5:s
                                        print what a build made with -DUSB_LINK says
                                        for 10 seconds, sending "s" after 2 s and 5 s

With the test build running:

  python3 tools/diag.py state           what the game is doing: where the player is,
                                        stars, the way to go, frames per second ...
  python3 tools/diag.py state 10        the same for 10 seconds, whenever it changes
  python3 tools/diag.py picture out.png the picture as it is on the screen
  python3 tools/diag.py press 80 1.5    hold buttons down (hex, the bits of the
                                        game's buttons: 04 B, 08 A, 10 down, 20 left,
                                        40 right, 80 up) for 1.5 seconds
  python3 tools/diag.py peek hero       a variable of the program, as it is in memory
  python3 tools/diag.py poke health 3   put a number into one
  python3 tools/diag.py stars 2         put that many stars on the player's record

The test build itself only knows how to hand out memory and how to take it.
Where a variable is, this end knows from the build (build/diag, by way of
the compiler's avr-nm); what it means is written down below.

Picking the game in the console's menu puts the normal build back.
"""
import glob
import os
import re
import select
import struct
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(os.path.dirname(ROOT), "CartManager"))

from arduboycart import cartimage, device  # noqa: E402
from arduboycart.serialport import SerialPort  # noqa: E402

COLS, COLBYTES, ROWS = 64, 7, 56
RAM_END = 0x0AFF

SAVE_PAGES = 16                     # the 4 KB the game may write to
SAVE_KEY = b"STA\x01"               # what they begin with once the game has

BUTTONS = {"b": 0x04, "a": 0x08, "down": 0x10, "left": 0x20, "right": 0x40, "up": 0x80}
RECORD = {0: 0, 1: 0x08, 2: 0x18, 3: 0x38, 4: 0x78}     # what it takes for so many stars


def find_data_page(loader, data):
    """Walk the game list on the console and return the pages where our data
    sits and where the game may write (None if the list gives it no place)."""
    page = 0
    for _ in range(4000):
        h = loader.read_flash(page, 1)
        if h[:7] != b"ARDUBOY":
            break
        size = (h[12] << 8) | h[13]
        data_page = (h[17] << 8) | h[18]
        save_page = (h[19] << 8) | h[20]
        if data_page != 0xFFFF and h[14] != 0xFF:
            first = loader.read_flash(data_page, 1)
            if first == data[:256]:
                return data_page, (None if save_page == 0xFFFF else save_page)
        if size == 0:
            break
        page += size
    return None, None


def list_end(loader):
    """The first page after the game list on the console."""
    page = 0
    for _ in range(4000):
        h = loader.read_flash(page, 1)
        if h[:7] != b"ARDUBOY":
            break
        size = (h[12] << 8) | h[13]
        if size == 0:
            break
        page += size
    return page


def put_data_at_end(loader, data):
    """Development place for the game data: the last pages of the chip, in
    front of the 4 KB the game may write to. Only blocks that differ are
    written. What the game has stored there stays; anything else in its place
    (game data of an earlier build) is wiped. Returns the page the data
    starts at."""
    pages = (len(data) + 255) // 256
    page = device.FLASH_PAGES - SAVE_PAGES - pages
    first = page - page % device.PAGES_PER_BLOCK
    if list_end(loader) + 1 > first:
        sys.exit("The game list on the console reaches into the last %.1f MB of the chip; "
                 "no room for test data." % ((device.FLASH_PAGES - first) / 4096))
    old = loader.read_flash(first, device.FLASH_PAGES - first)
    new = bytearray(old)
    at = (page - first) * 256
    new[at:at + len(data)] = data
    if not old[-SAVE_PAGES * 256:].startswith(SAVE_KEY):
        new[-SAVE_PAGES * 256:] = b"\xff" * (SAVE_PAGES * 256)
    blocks = len(new) // device.BLOCK
    differ = sum(1 for i in range(blocks)
                 if old[i * device.BLOCK:(i + 1) * device.BLOCK] != new[i * device.BLOCK:(i + 1) * device.BLOCK])
    if differ:
        print("writing the game data to the end of the chip: %d of %d blocks differ" % (differ, blocks))
        loader.write_flash(first, bytes(new), None, verify=True, known=old)
        if loader.read_flash(page, pages)[:len(data)] != data:
            sys.exit("The data did not read back as written.")
    print("game data is at the end of the chip, page %d (0x%04X)" % (page, page))
    return page


def connect(wait=15.0):
    """Like device.connect, but patient: a console that has just restarted
    takes a moment to show up on USB."""
    deadline = time.monotonic() + wait
    while True:
        try:
            return device.connect(log=print)
        except device.DeviceNotFound:
            if time.monotonic() > deadline:
                raise
            time.sleep(0.5)


def cmd_load(args):
    build = os.path.join(ROOT, "build", args[0] if args else "diag")
    with open(os.path.join(build, "SmallTheftAuto.ino.hex")) as f:
        program = bytearray(cartimage.read_hex(f.read()))
    with open(os.path.join(build, "fxdata.bin"), "rb") as f:
        data = f.read()
    with connect() as loader:
        pages = (len(data) + 255) // 256
        page, save = find_data_page(loader, data)
        if page is not None and loader.read_flash(page, pages)[:len(data)] != data:
            page = None
        if page is not None and save is not None:
            print("game data found in the game list at page %d (0x%04X), its place to write at page %d"
                  % (page, page, save))
        else:
            page = put_data_at_end(loader, data)
            save = device.FLASH_PAGES - SAVE_PAGES
        program[0x14:0x18] = bytes([0x18, 0x95, page >> 8, page & 0xFF])
        program[0x18:0x1C] = bytes([0x18, 0x95, save >> 8, save & 0xFF])
        loader.write_program(bytes(program))
        print("program written and read back: %d bytes" % len(program))
        loader.start_game()
    print("started")


def open_game(wait=15.0):
    deadline = time.monotonic() + wait
    while time.monotonic() < deadline:
        d = device.find_arduboy()
        if d and d["loader"] is False:
            try:
                port = SerialPort(d["port"], 115200, timeout=2.0)
                port.set_dtr(True)
                return port
            except OSError:
                pass
        time.sleep(0.1)
    sys.exit("No running game found on USB. (The game as it is played has no USB connection: "
             "only the test build and a build with -DUSB_LINK can be talked to.)")


def lines(port, seconds, sends=()):
    """Yield (time, line) for everything the game says; send commands on schedule."""
    t0 = time.monotonic()
    pending = sorted(sends)
    buf = b""
    while True:
        now = time.monotonic() - t0
        if now >= seconds:
            return
        while pending and pending[0][0] <= now:
            _, text = pending.pop(0)
            port.write(text.encode())
            yield now, "> " + text
        ready, _, _ = select.select([port.fd], [], [], 0.05)
        if not ready:
            continue
        try:
            chunk = os.read(port.fd, 65536)
        except BlockingIOError:
            continue
        except OSError as e:
            yield now, "(connection lost: %s)" % e
            return
        if not chunk:
            yield now, "(the device disconnected)"
            return
        buf += chunk
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            yield time.monotonic() - t0, line.decode("ascii", "replace").rstrip()


def cmd_watch(args):
    seconds = float(args[0]) if args else 10.0
    sends = []
    for a in args[1:]:
        at, text = a.split(":", 1)
        sends.append((float(at), text))
    with open_game() as port:
        for t, line in lines(port, seconds, sends):
            if line.startswith("R ") and len(line) > 100:
                line = "%s (%d bytes)" % (line[:6], (len(line) - 7) // 2)
            print("%6.2f  %s" % (t, line), flush=True)


# ---------------------------------------------------------------- the program's memory
def symbols(build="diag"):
    """Where the program's variables are: name -> (address, bytes). Names are
    the ones in the source; a variable inside a function is function.name."""
    elf = os.path.join(ROOT, "build", build, "SmallTheftAuto.ino.elf")
    nm = glob.glob(os.path.join(ROOT, ".toolchain", "data", "packages", "arduino", "tools", "avr-gcc", "*", "bin",
                                "avr-nm"))
    if not nm or not os.path.exists(elf):
        sys.exit("No build to look things up in: %s" % elf)
    out = subprocess.run([nm[0], "-S", elf], capture_output=True, text=True, check=True).stdout
    found = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 4:
            addr, size, kind, name = parts
        elif len(parts) == 3:
            addr, kind, name = parts
            size = "0"
        else:
            continue
        a = int(addr, 16)
        if a < 0x800000 or a >= 0x810000:
            continue
        found[plain_name(name)] = (a - 0x800000, int(size, 16))
    return found


def plain_name(name):
    """_ZL4hero -> hero, _ZZL9game_loopvE6before -> game_loop.before"""
    m = re.match(r"_ZZ?L?(\d+)", name)
    if not m:
        return name
    out = []
    rest = name[2:]
    while rest:
        m = re.match(r"[ZLNE]*(\d+)", rest)
        if not m:
            break
        n = int(m.group(1))
        start = m.end()
        out.append(rest[start:start + n])
        rest = rest[start + n:]
        rest = re.sub(r"^v?E", "", rest)           # (end of a function's name)
    return ".".join(out) if out else name


# What is looked at, and how it reads: name, how it is packed (as the struct
# module has it), and for lists how many bytes each entry has.
VALUES = (
    ("hero", "<HHHh"), ("on_foot", "B"), ("hero_kind", "B"), ("reach", "B"), ("held", "B"), ("kept", "<BH3B"),
    ("job", "B"), ("job_at", "B"), ("step", "7B"), ("job_left", "B"), ("job_clock", "<H"), ("job_fit", "B"),
    ("job_seen", "B"), ("job_from", "B"), ("job_paid", "<H"), ("phone", "B"), ("note", "B"), ("note_set", "B"),
    ("nav_near", "B"),
    ("health", "B"), ("crime", "B"), ("wanted", "B"), ("calm", "B"), ("seen_x", "<H"), ("seen_y", "<H"),
    ("cops", "B"), ("grip", "B"), ("over", "B"), ("page", "B"), ("nav_x", "B"), ("nav_y", "B"),
    ("nav_way", "B"), ("label_show", "B"), ("label_text", "4B"), ("disp_nav", "B"), ("disp_wide", "B"),
    ("frames_total", "<H"), ("fps_value", "B"), ("flash_fails", "B"), ("fx_page", "<H"), ("plane_ticks", "<H"),
    ("draw_count", "B"), ("map_x", "B"), ("map_y", "B"), ("page_pick", "B"), ("save_page", "<H"),
    ("save_next", "<H"), ("diag_buttons", "B"), ("cam_yaw", "<H"), ("cars", None), ("peds", None),
)
FONT_CHARS = " 0123456789$ABCDEFGHIJKLMNOPQRSTUVWXYZ.-:!/>,'?+"
# the console itself: ports and timers are in memory too
PORTS = {"PINB": 0x23, "DDRC": 0x27, "PINE": 0x2C, "PINF": 0x2F, "TIMSK4": 0x72, "TCCR1A": 0x80}


class Console:
    """A running test build."""

    def __init__(self, port=None, build="diag"):
        self.port = port or open_game()
        self.where = symbols(build)
        self.buf = b""

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.port.close()

    # ---- memory
    def fetch(self, ranges, before="", timeout=3.0):
        """[(address, bytes) ...] -> [bytes ...], all of them from between the
        same two frames if the request fits one USB packet (six ranges do)."""
        text = before + "".join("r%04X%04X" % (a, n) for a, n in ranges)
        self.port.write(text.encode())
        want = [a for a, _ in ranges]
        got = {}
        deadline = time.monotonic() + timeout
        while len(got) < len(want):
            left = deadline - time.monotonic()
            if left <= 0:
                raise device.DeviceError("The console did not answer (is the test build running?)")
            ready, _, _ = select.select([self.port.fd], [], [], left)
            if not ready:
                continue
            try:
                chunk = os.read(self.port.fd, 65536)
            except BlockingIOError:
                continue
            if not chunk:
                raise device.DeviceError("The console went away.")
            self.buf += chunk
            while b"\n" in self.buf:
                line, self.buf = self.buf.split(b"\n", 1)
                line = line.decode("ascii", "replace").strip()
                if line.startswith("R ") and len(line) >= 6:
                    try:
                        got[int(line[2:6], 16)] = bytes.fromhex(line[7:])
                    except ValueError:
                        pass
        return [got[a] for a in want]

    def read(self, addr, n):
        return self.fetch([(addr, n)])[0]

    def write(self, addr, data):
        self.port.write("".join("p%04X%02X" % (addr + i, v) for i, v in enumerate(data)).encode())

    def place(self, name):
        if name in PORTS:
            return PORTS[name], 1
        if name not in self.where:
            raise device.DeviceError("The program has no variable called %s." % name)
        return self.where[name]

    def peek(self, name):
        addr, n = self.place(name)
        return self.read(addr, n)

    def poke(self, name, value, offset=0):
        addr, n = self.place(name)
        if isinstance(value, int):
            value = value.to_bytes(max(1, n), "little", signed=value < 0)
        self.write(addr + offset, value)

    # ---- the game
    def buttons(self, held):
        self.poke("diag_buttons", held & 0xFF)

    def stars(self, n):
        """As if the player had done something for so many stars, here and now."""
        s = self.state()
        self.poke("seen_x", s["x_raw"])
        self.poke("seen_y", s["y_raw"])
        self.poke("calm", 0)
        self.poke("crime", RECORD[n])
        self.poke("wanted", n)

    def state(self, before=""):
        """What the game is doing, as a dict."""
        names = [n for n, _ in VALUES if n in self.where] + list(PORTS)
        places = sorted(self.place(n) for n in names)
        # as few pieces as will do: whatever lies close together comes in one
        ranges = []
        for a, n in places:
            if ranges and a - (ranges[-1][0] + ranges[-1][1]) < 24:
                ranges[-1][1] = max(ranges[-1][1], a + n - ranges[-1][0])
            else:
                ranges.append([a, n])
        data = self.fetch([tuple(r) for r in ranges], before)

        def raw(name):
            a, n = self.place(name)
            for (ra, rn), d in zip(ranges, data):
                if ra <= a and a + n <= ra + rn:
                    return d[a - ra:a - ra + n]
            raise KeyError(name)
        out = {}
        for name, how in VALUES:
            if name not in self.where:
                continue
            b = raw(name)
            if name == "hero":
                x, y, hd, speed = struct.unpack(how, b)
                out.update(x=x / 256.0, y=y / 256.0, x_raw=x, y_raw=y, hd=hd, heading=hd / 65536.0 * 360.0,
                           speed=speed)
            elif name == "cars":
                out["cars"] = [dict(x=c[0] / 256.0, y=c[1] / 256.0, hd=c[2], state=c[3] & 3, kind=(c[3] >> 2) & 7,
                                    wait=c[5])
                               for c in struct.iter_unpack("<HHBBBB", b) if c[3] & 3]
            elif name == "peds":
                out["peds"] = [dict(x=p[0] / 256.0, y=p[1] / 256.0, state=(p[2] >> 4) & 3, kind=(p[2] >> 2) & 3,
                                    cash=bool(p[2] & 0x40), timer=p[3])
                               for p in struct.iter_unpack("<HHBB", b) if (p[2] >> 4) & 3]
            elif name == "kept":
                v = struct.unpack(how, b)
                out.update(settings=v[0], cash=v[1], done=list(v[2:]))
            else:
                v = struct.unpack(how, b)
                out[name] = v[0] if len(v) == 1 else list(v)
        out["police_cars"] = sum(1 for c in out.get("cars", ()) if c["state"] == 1 and c["kind"] == 6)
        out["officers"] = sum(1 for p in out.get("peds", ()) if p["state"] == 2 and p["kind"] == 3)
        if "label_text" in out:
            out["label"] = "".join(FONT_CHARS[v] if v < len(FONT_CHARS) else "?" for v in out["label_text"])
        pins = {n: raw(n)[0] for n in PORTS}
        b = (~pins["PINF"]) & 0xF0
        b |= ((~pins["PINE"]) & 0x40) >> 3
        b |= ((~pins["PINB"]) & 0x10) >> 2
        out["buttons"] = b
        out["speaker"] = pins["DDRC"] >> 6
        out["light"] = {0x01: "off", 0x21: "red", 0x81: "blue"}.get(pins["TCCR1A"], hex(pins["TCCR1A"]))
        out["playing"] = pins["TIMSK4"] != 0
        return out

    def stack_free(self):
        """How far the stack has come down at most: bytes never touched
        between the variables and the stack."""
        start = self.where["__bss_end"][0] if "__bss_end" in self.where else self.where["__heap_start"][0]
        d = self.read(start, RAM_END + 1 - start)
        n = 0
        while n < len(d) and d[n] == 0xA5:
            n += 1
        return n

    def picture(self, before=""):
        """The picture as the display routine puts it on the screen."""
        parts = [self.place(n) for n in ("hud", "fb_hi", "fb_lo", "nav_over", "disp_wide", "disp_nav")]
        hud, hi, lo, over, wide, nav = self.fetch(parts, before)
        return picture_from(hud, hi, lo, wide[0] != 0, over if nav[0] else None)


NAV_C0, NAV_ARROW_COLS, NAV_BOX_C0, NAV_BOX_COLS = 26, 6, 33, 9


def picture_from(hud, hi, lo, wide=False, over=None):
    """wide: a page, black and white, the two planes side by side. over: the
    arrow laid over the view, and the distance next to it taken the way a
    page is."""
    from PIL import Image
    shades = [0, 156, 215, 255]
    img = Image.new("L", (128, 64), 0)
    px = img.load()
    for c in range(COLS):
        for r in range(ROWS):
            m = 1 << (r & 7)
            h, l = hi[c * COLBYTES + (r >> 3)] & m, lo[c * COLBYTES + (r >> 3)] & m
            if wide or (over is not None and r < 8 and NAV_BOX_C0 <= c < NAV_BOX_C0 + NAV_BOX_COLS):
                px[c * 2, r], px[c * 2 + 1, r] = (255 if h else 0), (255 if l else 0)
            else:
                px[c * 2, r] = px[c * 2 + 1, r] = shades[(2 if h else 0) + (1 if l else 0)]
    if over is not None and not wide:
        half = len(over) // 2
        for page in range(2):
            for c in range(NAV_ARROW_COLS):
                for side in range(2):
                    keep, dots = over[page * half + c * 4 + side * 2:page * half + c * 4 + side * 2 + 2]
                    for bit in range(8):
                        x, y = (NAV_C0 + c) * 2 + side, page * 8 + bit
                        if not (keep >> bit) & 1:
                            px[x, y] = 0
                        if (dots >> bit) & 1:
                            px[x, y] = 255
    for x in range(128):
        for b in range(7):                  # (the last row of the screen never lights up)
            if hud[x] & (1 << b):
                px[x, 56 + b] = 255
    return img


def say(s):
    """One line of what matters."""
    where = {0: "the game", 1: "the title", 2: "the map", 3: "the settings", 4: "a mission offered"}.get(s["page"], "?")
    text = "%s, %s at %.2f, %.2f heading %.0f speed %d; health %d, $%d, stars %d (record %d, calm %d)" % (
        where, "on foot" if s["on_foot"] else "driving", s["x"], s["y"], s["heading"], s["speed"], s["health"],
        s["cash"], s["wanted"], s["crime"], s["calm"])
    if s["police_cars"] or s["officers"]:
        text += ", police cars %d, officers %d" % (s["police_cars"], s["officers"])
    if s.get("nav_x"):
        text += "; on the way to %d, %d: arrow %d, label %s" % (s["nav_x"], s["nav_y"], s["nav_way"], s["label"].strip())
    if s["page"] == 2:
        text += "; the cross at %d, %d" % (s["map_x"], s["map_y"])
    if s["over"]:
        text += "; over (%d)" % s["over"]
    if s.get("job", 255) != 255:
        op = s["step"][0]
        text += "; mission %d, step %d (%s%s): %d s left" % (
            s["job"], s["job_at"], {0: "end", 1: "go", 2: "kill", 3: "lose the police"}[op & 3],
            "" if s["job_fit"] else ", the car is missing", s["job_clock"] // 156)
        if (op & 3) == 2:
            text += ", %d to go%s" % (s["job_left"], ", whoever it is about is there" if s["job_seen"] else "")
        if s["nav_near"]:
            text += ", there"
    if s.get("phone", 255) != 255:
        text += "; telephone %d within reach" % s["phone"]
    if s.get("note"):
        text += "; MISSION %s in the picture (%d)" % ("PASSED" if s["job_paid"] and s["job"] == 255 else "PASSED or FAILED", s["note"])
    if "done" in s:
        text += "; missions done %s" % "".join(str(v) for v in s["done"])
    text += "; buttons %02X, light %s%s, settings %d" % (
        s["buttons"] | s.get("diag_buttons", 0), s["light"], ", sound playing" if s["playing"] else "",
        s["settings"])
    if s.get("flash_fails"):
        text += ", THE FLASH CHIP DID NOT ANSWER %d TIMES AT THE START" % s["flash_fails"]
    return text


def speed(c, seconds=2.0):
    """Pictures a second, and display planes a second (156 is right): counted
    over a while, from what the game counts itself."""
    a = c.state()
    time.sleep(seconds)
    b = c.state()
    ticks = (b["plane_ticks"] - a["plane_ticks"]) & 0xFFFF
    frames = (b["frames_total"] - a["frames_total"]) & 0xFFFF
    return (frames * 156.0 / ticks if ticks else 0.0), ticks / seconds


def cmd_state(args):
    seconds = float(args[0]) if args else 0.0
    with Console() as c:
        t0 = time.monotonic()
        last = ""
        while True:
            s = c.state()
            text = say(s)
            if text != last:
                print("%6.2f  %s" % (time.monotonic() - t0, text), flush=True)
                last = text
            if time.monotonic() - t0 >= seconds:
                break
            time.sleep(0.2)
        fps, planes = speed(c)
        print("        %.1f pictures a second (%.0f planes); stack: %d bytes never used; game data at page %d, "
              "its place to write at %d" % (fps, planes, c.stack_free(), s["fx_page"], s["save_page"]))


def cmd_picture(args):
    out = args[0] if args else "picture.png"
    with Console() as c:
        c.picture().resize((512, 256), 0).save(out)
    print("picture written to", out)


def cmd_press(args):
    held = int(args[0], 16)
    seconds = float(args[1]) if len(args) > 1 else 0.3
    with Console() as c:
        c.buttons(held)
        time.sleep(seconds)
        c.buttons(0)
        time.sleep(0.2)
        print(say(c.state()))


def cmd_peek(args):
    with Console() as c:
        for name in args:
            addr, n = c.place(name)
            d = c.read(addr, n)
            print("%s at %04X, %d bytes: %s" % (name, addr, n, d.hex(" ")))


def cmd_poke(args):
    with Console() as c:
        c.poke(args[0], int(args[1], 0))
        time.sleep(0.2)
        print(say(c.state()))


def cmd_stars(args):
    with Console() as c:
        c.stars(int(args[0]))
        time.sleep(0.3)
        print(say(c.state()))


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd = {"load": cmd_load, "watch": cmd_watch, "picture": cmd_picture, "state": cmd_state, "press": cmd_press,
           "peek": cmd_peek, "poke": cmd_poke, "stars": cmd_stars}.get(sys.argv[1])
    if not cmd:
        sys.exit(__doc__)
    try:
        cmd(sys.argv[2:])
    except (device.DeviceError, device.SerialError) as e:
        sys.exit("Stopped: %s" % e)


if __name__ == "__main__":
    main()
