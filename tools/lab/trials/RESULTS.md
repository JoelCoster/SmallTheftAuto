# What was tried to make the program smaller (2026-09-29)

All figures are for the normal build. "Console" means measured on the real
Arduboy FX with a build that plays 12 seconds by itself (`-DPROBE`,
`tools/lab/probe.py`): the player stands at the start and turns round and
round.

| Build | Program | Memory | Pictures a second (console) | Stack never used (console) |
|---|---|---|---|---|
| As it is on the console | 28180 | 2266 | 24.0 to 24.1 | 74 to 116 |
| Without USB, Arduino's start-up code and the Arduboy library (`-DNO_USB`) | 24440 | 2114 | 24.5 | 261 to 270 |
| ... and `-mrelax` | 24206 | | 24.4 | 270 |
| ... and `-mstrict-X` | 24036 | | 24.5 | 270 |
| ... and `-mcall-prologues` | 23650 | | 24.1 | 245 to 254 |

Compiler options one at a time, on the build as it is (`tools/lab/size_flags.py`):
`-mcall-prologues` -472, `-mrelax` -246, `-mstrict-X` -178,
`-fno-move-loop-invariants` -94, `-fno-tree-ter` -38, `-fno-reorder-blocks` -32,
`-fno-inline-small-functions` -24, `-fno-tree-scev-cprop` -8; no change or
larger: `-fno-jump-tables`, `-fno-caller-saves`, `-fno-optimize-sibling-calls`,
`-fno-tree-switch-conversion`, `-fno-ipa-cp`, `-fno-ipa-sra`,
`-fno-partial-inlining`, `-ffreestanding` (+50), `-fno-tree-sra` (+88),
`-fno-guess-branch-probability` (+94), `-fno-split-wide-types` (+158),
`-fno-tree-loop-optimize` (+534), `-fno-ivopts` (+718). The three that are
used together: -900; the other small ones on top: -64 more, not worth the
unknowns.

Changes to the sources, on top of 23650 (`tools/lab/size_trial.py` with the
lists in this folder):

| Change | Bytes |
|---|---|
| `iabs` as a routine of its own | -36 |
| `dir_x`, `dir_y` as routines, one table for both | -8 |
| `fx_next` as a routine, written out only in `fx_read` | -68 |
| The flash chip asked at the start only, not every 32 frames | -60 |
| Trees and lamps: chunks counted in 8 bits | -70 |
| `hud_icon` without the test for the edge | -26 |
| What is drawn handed over in registers, not as a record | -4 |
| The order of the columns worked out, not looked up | -52 |
| The direction of a column's ray worked out, not looked up | -114 |
| **All of these** | **-438** |
| Half a sine table, the values between worked out (not done: 1% of a frame's time, values off by one in 16384) | -224 |

Not worth it (larger, or the same): `car_state`/`car_kind`/`car_dir` as
routines (+72), `hero_slow` as a routine (+24), `cell_at` as a routine (0),
a routine for the cell of a place (+8), `ped_state` as a routine (-4),
moving a tree's entry in a loop (0), `hud_money` by way of `digit_off` (0),
one routine that picks a cell for cars, parked cars and people (+52), the
player's data by way of a pointer in a register (-70 in four functions,
larger in six others).

Where the 28180 bytes are (`tools/lab/size_map.py`): the game's own code
20.7 KB (of which the renderer in assembly 1.1 KB, the display routine
0.4 KB), tables 3.4 KB, USB and Arduino 3.8 KB, arithmetic from the
compiler's library 0.35 KB.

## What went into the game (2026-09-29, evening)

Joel's choice: without USB, the two options that cost nothing (`-mrelax`,
`-mstrict-X`), and the rewrites. `-mcall-prologues` and the half sine table
stay in reserve.

| Build | Program | Memory |
|---|---|---|
| As it was on the console | 28180 | 2266 |
| Without USB, the two options | 24036 | 2114 |
| ... `iabs` a routine | 24032 | |
| ... `dir_x`, `dir_y` routines, one table | 24020 | |
| ... `fx_next` a routine but for `fx_read` | 23952 | |
| ... the flash chip asked at the start only | 23906 | 2113 |
| ... trees and lamps: chunks counted in 8 bits | 23836 | |
| ... `hud_icon` without the test for the edge | 23810 | |
| ... the order of the columns worked out | 23766 | |
| ... the direction of a column's ray worked out | **23680** | **2113** |

Every step showed the same pictures as the installed game, frame by frame,
in twelve scenes of the desktop build (`tools/lab/regress.py`).

The rewrites gave 356 bytes, not the 438 measured in the trial. Two reasons:
the trial measured on top of `-mcall-prologues`, where a routine of its own
saves more; and the trial's way of working out the direction of a ray was
wrong (it was only measured, never looked at: the product did not fit 16
bits). The one that went in is `m * 210 - ((m * 20 + 140) >> 8)` for
m = 2c - 63, which gives the table's 64 values to the last bit;
`tools/build_assets.py` finds the three numbers and stops the build if there
are none, and the build that checks itself (`-DSELFTEST`) compares with the
table on the console's processor: 13696 columns, none differed (emulator).

The test build lost the Arduboy library (it shares `console_boot` with the
game now) and the line of status it answered "s" with: 27428 bytes instead
of 28786, which leaves room for the game to grow by 2.2 KB before the test
build needs `-mcall-prologues` (0.45 KB more).

The two interrupt routines, which are timed by hand, are the same
instruction for instruction in the new build (`tools/lab/same_asm.py`); in
the renderer one long call became a short one.
