#!/usr/bin/env python3
"""Map program address ranges (from the Ardens profiler) back to source lines.
   usage: tools/where.py 0x31ce-0x3234 0x3196-0x31be ..."""
import glob, os, re, subprocess, sys
root = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
od = glob.glob(os.path.join(root, ".toolchain/data/packages/arduino/tools/avr-gcc/*/bin/avr-objdump"))[0]
elf = os.path.join(root, "build/game/SmallTheftAuto.ino.elf")
for rng in sys.argv[1:]:
    a, b = rng.split("-")
    out = subprocess.run([od, "-d", "-l", "--start-address=" + a, "--stop-address=" + hex(int(b, 16) + 2), elf],
                         capture_output=True, text=True).stdout
    counts, cur = {}, None
    for line in out.splitlines():
        m = re.match(r".*/(\w+\.(?:h|ino|S|cpp|c)):(\d+)", line)
        if m:
            cur = "%s:%s" % (m.group(1), m.group(2))
        elif re.match(r"\s+[0-9a-f]+:\t", line) and cur:
            counts[cur] = counts.get(cur, 0) + 1
    top = sorted(counts.items(), key=lambda kv: -kv[1])[:7]
    print(rng, " ".join("%s(%d)" % kv for kv in top))
