# Building Small Theft Auto

It was built on a Mac. It takes Python 3 with Pillow, and `arduino-cli` with
the Arduino AVR core (1.8.8 was used) in a folder `.toolchain` at the top of
the repository:

```bash
mkdir -p .toolchain/bin
curl -L https://downloads.arduino.cc/arduino-cli/arduino-cli_latest_macOS_ARM64.tar.gz | tar -xz -C .toolchain/bin
printf 'directories:\n  data: %s/.toolchain/data\n  downloads: %s/.toolchain/downloads\n  user: %s/.toolchain/user\n' "$PWD" "$PWD" "$PWD" > .toolchain/arduino-cli.yaml
.toolchain/bin/arduino-cli --config-file .toolchain/arduino-cli.yaml core update-index
.toolchain/bin/arduino-cli --config-file .toolchain/arduino-cli.yaml core install arduino:avr
```

The compiler is an Intel program: a Mac with Apple's own processor needs
Rosetta 2.

```bash
tools/build.sh
```

makes the pictures and the city, compiles the program and puts both into
`build/game/SmallTheftAuto.arduboy`.

## On the computer, without a console

The game's code also runs on the computer. Once the game's data is there
(`tools/build.sh` makes it; so does `python3 tools/build_assets.py 4`, which
needs no Arduino):

```bash
python3 tools/lab/regress.py save mine
```

builds the game for the computer (it takes `clang++`), plays 22 scenes by
script and keeps a fingerprint of each. `check mine` plays them again and
says which differ.
