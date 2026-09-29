#!/usr/bin/env python3
"""
Bundle the program and its flash data into one .arduboy package.

A .arduboy file is a zip holding the .hex, the flash image and an info.json. It is
what the Ardens emulator and the Arduboy flashing tools load in one go.

  python3 tools/package.py build/game/SmallTheftAuto.ino.hex build/game/fxdata.bin build/game/SmallTheftAuto.arduboy

The title picture (assets/title.png) is what the console's game menu shows.
It is drawn by tools/title.py.
"""
import json, os, sys, time, zipfile

TITLE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "title.png")


def main():
    hexf, binf, out = sys.argv[1:4]
    info = {
        "schemaVersion": 3,
        "title": "Small Theft Auto",
        "description": "A 3D open-world crime game for the Arduboy FX.",
        "author": "Joel",
        "version": "0.1.0",
        "date": time.strftime("%Y-%m-%d"),
        "genre": "Action",
        "binaries": [{
            "title": "Small Theft Auto",
            "filename": "SmallTheftAuto.hex",
            "device": "ArduboyFX",
            "flashdata": "fxdata.bin",
            "flashsave": "fxsave.bin",
            "cartImage": "title.png",
        }],
    }
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("info.json", json.dumps(info, indent=2))
        z.write(hexf, "SmallTheftAuto.hex")
        z.write(binf, "fxdata.bin")
        # what the game may write to (its settings): next to the data, 4 KB of nothing
        z.write(os.path.join(os.path.dirname(binf), "fxsave.bin"), "fxsave.bin")
        z.write(TITLE, "title.png")
    print("wrote", out)


if __name__ == "__main__":
    main()
