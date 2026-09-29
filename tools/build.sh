#!/bin/sh
# Build everything: assets, then the console program, then the .arduboy package.
# Output lands in build/game, or in build/$OUT.
#
#   tools/build.sh                         the game as it is played. build/game is what the
#                                          list of games on the console is made from
#                                          (../CartManager): only what is meant to go there
#   OUT=dev tools/build.sh                 the same, kept apart in build/dev: for trying out
#   EXTRA_FLAGS=-DDIAG OUT=diag tools/build.sh
#                                          test build that a computer can look into over USB
#                                          (tools/diag.py)
#   EXTRA_FLAGS=-DPROBE OUT=probe tools/build.sh
#                                          the game as it is played, playing by itself for a
#                                          while and writing down how it went (tools/lab/probe.py)
#   EXTRA_FLAGS=-DUSB_LINK OUT=link tools/build.sh
#                                          the game with a USB connection that answers "s" with
#                                          one line of status, as every build did until 2026-09-29
#   EXTRA_FLAGS=-DSELFTEST OUT=selftest tools/build.sh
#                                          run assembly and reference code side by side;
#                                          the HUD shows columns drawn / columns that differ
#   EXTRA_FLAGS=-DPROFILE OUT=profile tools/build.sh
#                                          the HUD shows time per frame for each part of
#                                          the renderer, in units of 0.1 ms
#
# The game as it is played has no USB connection: 3.7 KB of program that the
# game has better use for (SmallTheftAuto.ino, NO_USB). To load anything, the
# console has to be in its menu: hold Up and Down for two seconds.
#
# Two options of the compiler make the program 0.4 KB smaller and cost
# nothing: -mrelax (short jumps and calls where the way is short) and
# -mstrict-X (one of the three address registers is not used where it takes
# more instructions than it saves). Because the program is put together as a
# whole when it is linked, they go to the linker as well.
#
# The test build carries the USB connection on top of the game (3.8 KB) and
# would not fit: it is built with -mcall-prologues as well, which saves
# another 0.4 KB and costs 1.5% of the speed. The game as it is played is not.
set -e
cd "$(dirname "$0")/.."
T="$PWD/.toolchain"
SMALLER="-mrelax -mstrict-X"
case "${EXTRA_FLAGS:-}" in *-DDIAG*) SMALLER="$SMALLER -mcall-prologues" ;; esac
export OUT="${OUT:-game}"
python3 tools/build_assets.py "${SEED:-4}"
"$T/bin/arduino-cli" --config-file "$T/arduino-cli.yaml" compile \
  --fqbn arduino:avr:leonardo \
  --build-property "upload.maximum_size=29696" \
  --build-property "compiler.cpp.extra_flags=${EXTRA_FLAGS:-} $SMALLER" \
  --build-property "compiler.c.extra_flags=$SMALLER" \
  --build-property "compiler.S.extra_flags=${EXTRA_FLAGS:-}" \
  --build-property "compiler.c.elf.extra_flags=$SMALLER" \
  --build-path "$PWD/build/$OUT-obj" \
  --output-dir "$PWD/build/$OUT" \
  SmallTheftAuto
O="build/$OUT"
python3 tools/package.py "$O/SmallTheftAuto.ino.hex" "$O/fxdata.bin" "$O/SmallTheftAuto.arduboy"
cp tools/web/ardens.html build/ardens.html
ls -la "$O/SmallTheftAuto.ino.hex" "$O/fxdata.bin" "$O/SmallTheftAuto.arduboy"
