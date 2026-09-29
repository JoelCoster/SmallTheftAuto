#!/usr/bin/env python3
"""
Small Theft Auto sounds.

The console's speaker sits between two pins that a timer drives, one the
opposite of the other. The timer makes one pulse per period, counting in steps
of 8 microseconds. A sound is a list of steps:

    (planes, base, mask, width)

  planes  how long the step lasts, in display planes (156 to the second)
  base    shortest period, in counts, less one
  mask    chance adds (random & mask) counts to every period: 0 gives a clean
          tone, more gives noise
  width   how long each pulse is, in counts. Narrow pulses are quieter, which
          is the only volume control a pin has. Must stay below base.

This file is where the sounds are defined (build_assets.py writes them into
tables.h). Run by itself it plays them the way the console's program would,
on paper, and writes what comes out:

    python3 tools/sound.py [folder]      one .wav per sound, plus figures
"""
import math, os, struct, sys, wave

COUNT_S = 8e-6                 # one timer count: 16 MHz / 128
PLANE_COUNTS = 1603 * 4 / 8.0  # one display plane in timer counts (1603 counts of 4 us)
REFRESH_COUNTS = 146           # the display refresh holds everything else up for 1.17 ms

SOUNDS = {
    # a crack, then a rumble that dies away
    "shot": [
        (2, 12, 0x1F, 7),
        (4, 20, 0x3F, 10),
        (4, 30, 0x7F, 8),
        (5, 40, 0x7F, 5),
        (6, 60, 0x7F, 3),
        (8, 80, 0x7F, 2),
        (8, 100, 0x7F, 1),
    ],
    # money picked up: two clear notes, the second one ringing out
    "cash": [
        (5, 62, 0, 20),
        (6, 46, 0, 16),
        (5, 46, 0, 8),
        (5, 46, 0, 4),
        (6, 46, 0, 2),
    ],
    # hit by a bullet, or by a police car: a short dull blow
    "hurt": [
        (3, 60, 0x3F, 14),
        (4, 110, 0x7F, 10),
        (5, 120, 0x7F, 4),
    ],
    # WASTED, BUSTED: down the stairs, and the last step is a long one
    "over": [
        (16, 79, 0, 20),
        (16, 94, 0, 24),
        (16, 118, 0, 30),
        (16, 158, 0, 40),
        (40, 238, 0, 60),
        (20, 238, 0, 16),
    ],
    # a police car: high, low, high, low; not loud
    "siren": [
        (22, 84, 0, 9),
        (22, 112, 0, 12),
        (22, 84, 0, 9),
        (22, 112, 0, 12),
    ],
    # there: where the arrow was leading. Three notes up, the last one held
    "there": [
        (7, 62, 0, 18),
        (7, 49, 0, 16),
        (9, 41, 0, 14),
        (8, 41, 0, 5),
    ],
    # a telephone that rings: two notes in turn, fast
    "ring": [
        (3, 52, 0, 12),
        (3, 66, 0, 14),
        (3, 52, 0, 12),
        (3, 66, 0, 14),
        (3, 52, 0, 12),
        (3, 66, 0, 14),
        (3, 52, 0, 10),
        (3, 66, 0, 6),
    ],
    # mission passed: up the stairs two at a time, and the top one rings out
    "passed": [
        (8, 94, 0, 22),
        (8, 74, 0, 20),
        (8, 62, 0, 18),
        (24, 46, 0, 16),
        (10, 46, 0, 6),
        (10, 46, 0, 2),
    ],
    # mission failed: two notes down
    "failed": [
        (14, 118, 0, 30),
        (30, 158, 0, 40),
        (12, 158, 0, 12),
    ],
}
ORDER = ["shot", "cash", "hurt", "over", "siren", "there", "ring", "passed", "failed"]


def table(name):
    out = []
    for planes, base, mask, width in SOUNDS[name]:
        assert 0 < planes < 256 and 3 <= base < 256 and base + mask < 256 and 0 < width < base
        assert mask & (mask + 1) == 0, "mask must be one less than a power of two"
        out += [planes, base, mask, width]
    return out + [0]


def play(name, refresh=True, start=0.0, dice=0xACE1):
    """Follow the console's program count by count. Returns (levels, periods,
    calls): the level of the speaker (+1, -1, 0) for every count, how many
    periods the timer made, and how many times the interrupt ran (fewer:
    periods that go by while the display is refreshed share one call; the test
    build on the console counts the calls). start: how far into a display
    plane the sound begins, in counts; dice: where the random numbers stand."""
    steps = list(SOUNDS[name])
    levels = []
    periods = 0
    calls = 0
    planes, base, mask, width = steps.pop(0)
    top = base
    now_width = width
    next_width = width
    left = planes
    t = float(start)              # counts since the plane in which the sound began
    seen = 0
    while True:
        # one period: high for the pulse, low for the rest
        n = top + 1
        for k in range(n):
            levels.append(1 if k < now_width else -1)
        t += n
        periods += 1
        now_width = next_width
        # the interrupt at the start of the next period; it waits while the
        # display is being refreshed
        at = t
        if refresh and (at % PLANE_COUNTS) < REFRESH_COUNTS:
            at = at - (at % PLANE_COUNTS) + REFRESH_COUNTS
        plane = int(at // PLANE_COUNTS)
        gone = plane - seen
        if gone:
            seen = plane
            if gone >= left:
                if not steps:
                    break
                planes, base, mask, width = steps.pop(0)
                left = planes
                next_width = width
            else:
                left -= gone
        calls += 1
        dice ^= (dice << 7) & 0xFFFF
        dice ^= dice >> 9
        dice ^= (dice << 8) & 0xFFFF
        want = base + (dice & mask)
        late = int(at - t)        # where the counter is by the time we get to it
        if late + 2 < want:
            top = want
        # (otherwise the period stays as it was)
        if late > top:            # periods that went by unattended
            extra = late // (top + 1)
            for _ in range(extra):
                for k in range(top + 1):
                    levels.append(1 if k < now_width else -1)
            t += extra * (top + 1)
            periods += extra
    levels += [0] * 200
    return levels, periods, calls


def bandpass(x, rate, f0, q):
    """A plain two-pole resonator: roughly what a small piezo speaker does."""
    w = 2 * math.pi * f0 / rate
    a = math.sin(w) / (2 * q)
    b0, b2 = a, -a
    a0, a1, a2 = 1 + a, -2 * math.cos(w), 1 - a
    y = []
    x1 = x2 = y1 = y2 = 0.0
    for v in x:
        o = (b0 * v + b2 * x2 - a1 * y1 - a2 * y2) / a0
        x2, x1 = x1, v
        y2, y1 = y1, o
        y.append(o)
    return y


def lowpass(x, rate, f0):
    k = 1 - math.exp(-2 * math.pi * f0 / rate)
    y = []
    s = 0.0
    for v in x:
        s += (v - s) * k
        y.append(s)
    return y


def write_wav(path, x, rate_in, rate_out=44100, gain=0.5):
    x = lowpass(lowpass(x, rate_in, 16000), rate_in, 16000)
    n = int(len(x) * rate_out / rate_in)
    peak = max(1e-9, max(abs(v) for v in x))
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate_out)
        frames = bytearray()
        for i in range(n):
            p = i * rate_in / rate_out
            k = int(p)
            v = x[k] if k + 1 >= len(x) else x[k] + (x[k + 1] - x[k]) * (p - k)
            frames += struct.pack("<h", int(max(-1.0, min(1.0, v / peak * gain)) * 32767))
        w.writeframes(bytes(frames))


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(out, exist_ok=True)
    rate = 1.0 / COUNT_S
    for name in ORDER:
        levels, periods, calls = play(name)
        secs = len(levels) * COUNT_S
        print("%s: %d bytes in the program, %.0f ms, %d periods" % (name, len(table(name)), secs * 1000, periods))
        # how loud, 20 ms at a time, as a small speaker would give it
        heard = bandpass([float(v) for v in levels], rate, 4000.0, 1.5)
        win = int(0.02 / COUNT_S)
        loud = []
        for i in range(0, len(heard) - win + 1, win):
            e = math.sqrt(sum(v * v for v in heard[i:i + win]) / win)
            loud.append(e)
        top = max(loud)
        print("  loudness every 20 ms, dB below the loudest: " +
              " ".join("%.0f" % (20 * math.log10(max(1e-6, e) / top)) for e in loud))
        # pulses per second in each step
        t = 0
        for planes, base, mask, width in SOUNDS[name]:
            mean = base + 1 + mask / 2.0
            print("  %3d ms: periods %4.0f to %4.0f us (about %5.0f a second), pulse %3.0f us"
                  % (planes * PLANE_COUNTS * COUNT_S * 1000, (base + 1) * 8, (base + mask + 1) * 8,
                     1e6 / (mean * 8), width * 8))
        import random
        rnd = random.Random(1)
        runs = [play(name, True, rnd.uniform(0, PLANE_COUNTS), rnd.randrange(1, 65536))[1:] for _ in range(200)]
        for k, what in ((0, "periods"), (1, "interrupt calls")):
            v = [r[k] for r in runs]
            print("  %s, begun at any moment: %d to %d, %d on average" % (what, min(v), max(v), sum(v) // len(v)))
        write_wav(os.path.join(out, name + ".wav"), [float(v) for v in levels], rate)
        write_wav(os.path.join(out, name + "_small_speaker.wav"), heard, rate, gain=0.9)
        print("  written: %s.wav, %s_small_speaker.wav" % (name, name))


if __name__ == "__main__":
    main()
