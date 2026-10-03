# Small Theft Auto

> These are the working notes of the project, as they were written along
> the way, for the author's own console and computer. Three things they
> speak of are not in this repository: the tool that puts the game into the
> console's list of games (`../CartManager`; `tools/diag.py` and
> `tools/lab/probe.py`, which talk to the console, use a part of it), the two
> clips in `preview/`, and the text in `post/`. Any tool for the Arduboy FX
> that takes an `.arduboy` file will put the game on a console.

A 3D open-world crime game for the Arduboy FX, in the spirit of GTA and small
in every way: 128 x 64 dots, four shades of gray, 26 KB of program.
(Until 2026-09-29 the game was called Two-Bit City.)

**Status: milestone 5, missions.** You walk through a 3D city, get into any
car (your own, a parked one, one that is driving past) and drive it. There is
traffic, there are parked cars and people on the pavements. On foot you carry
a pistol. Whoever goes down leaves money behind, to be picked up. What you do
wrong brings the police: stars in the HUD, police cars that come after you,
officers who arrest you (BUSTED) or, from two stars on, shoot (WASTED). Pick
a place on the map, and an arrow at the top of the picture points to it and
says how far it is. Three telephones in the city ring: whoever answers is
offered a mission, twelve in all, and what they pay is kept when the console
is switched off.

The game plays by day. A night look was tried as a concept and dropped.

## Controls

B is the upper of the two buttons and does the main thing: the accelerator in
a car, the trigger on foot. Down is for what is next to you: the car door,
both ways, and the telephone.

| Button | On foot | In a car |
|---|---|---|
| Up | Run forward | |
| Down | Answer the telephone next to you if it rings (the HUD says `DOWN:ANSWER`); get into the car next to you (`DOWN:GET IN`); otherwise step backward | Get out, at walking pace or slower |
| Left / Right | Turn | Steer |
| B (upper) | Fire; keep it down to keep firing | Accelerate |
| A (lower) | With Up: sprint | Brake, then reverse |

**Left + Right together: the map**, any time during the game; the game stands
still meanwhile. The square that grows and shrinks is you.

| Button | On the map |
|---|---|
| Up, Down, Left, Right | Move the cross: a dot for a tap, on and on when held. The map moves along |
| B (upper) | Set marker: back to the game, with an arrow that shows the way to where the cross is. With the cross on yourself: the marker is taken away, back to the game with no arrow. With a mission on, the marker is the mission's, and B only goes back |
| A (lower) | The settings |
| Left + Right together | Put the map away; nothing changes |

Anywhere: Up + Down, held 2 seconds, goes back to the console's game menu.
The money is kept on the way out.

**The settings** (A on the title page or the map): SOUND, POLICE LIGHT,
GRAYSCALE and START OVER. GRAYSCALE OFF shows the game in two shades instead
of four, for panels that flicker with the four; an FX-C or a Mini starts
that way, an FX with the four. All of it is kept on the flash chip.

The HUD, left to right: health, the stars, speed or a hint, the money. With a
mission on: what the mission wants next instead of the speed, and the time
that is left instead of the money.

## Missions

Three telephone boxes stand in the city. One that has a mission to offer
rings (from about 30 metres it is heard), has an arrow hanging over it, and is
on the map as the first letter of whoever is on the line: V, L, C. The first
one is a few steps ahead of where the game begins.

- **Down next to the box answers.** A page says what the mission is and what
  it pays. B takes it, A does not (it is offered again any time).
- **What to do next is in the bottom line**, and the arrow at the top of the
  picture leads to where it is to be done. The same arrow that hangs over
  the telephones hangs over the place, or over the person it is about.
- **Every mission has a clock**, bottom right. A new step sets it again.
- **It fails** when the clock runs out, and with WASTED or BUSTED. The
  telephone offers it again.
- **MISSION PASSED** pays, and the telephone has the next one. What has been
  done and the money are kept on the flash chip at that moment.
- **Where a car has to stop**, walking pace within 12 metres of the place
  is enough.

| | Mission | Pays | What it takes |
|---|---|---|---|
| Vinnie, downtown | Warm up | $100 | Any car to the garage at the park, 3 minutes |
| | Taxi driver | $200 | A taxi to the hotel (2.5 minutes), then to the south park (1.5 minutes) |
| | Loudmouth | $400 | The man in the white shirt at the plaza; then no stars |
| | Frenzy | $500 | 10 people in 60 seconds |
| Lola, at the park in the north-east | Speed date | $300 | By car to three places: 50, 26 and 34 seconds |
| | Van order | $400 | A van to the docks across the north bridge, 4 minutes |
| | Black and white | $800 | A police car to the docks, 5 minutes |
| | Two birds | $700 | One man at the park, one downtown; then no stars |
| The Captain, at the docks | Getaway | $1000 | By car to the bank; two stars are handed out, to be lost; to the docks |
| | Cop out | $1200 | Three officers; then no stars |
| | Rush hour | $1500 | 20 people in 90 seconds |
| | The big one | $3000 | A sports car to the north plaza; the judge; three stars to be lost; home to the docks |

The clocks and the numbers are first guesses: played by the desktop build's
autopilot and by remote control on the console, not yet by a person. They
are data (`tools/missions.py`): changing them costs a build, no program space.
`build/game/missions.txt` lists the missions as the build made them, with
how far it is from step to step by the streets.

## The way to go

With a marker set on the map, the top of the picture shows an arrow and a
number, as in the concept clip (`preview/city_day.gif`): the arrow points to
the place, as the crow flies and counted from where you are looking, so that
straight up means straight ahead; the number is how far it is, `374M`, from
a kilometre on `1.2K`. Round the houses is up to you.

- The arrow leads to a street: the one nearest to the cross, looking north,
  east, south and west from it. A cross on a roof is a place nobody gets to.
- 12 metres from the place you are there: three notes, and arrow and number
  go.
- The ring on the map is the marker, where the arrow leads. It stays when
  you are WASTED or BUSTED.

## Title and settings

The game starts with its title: B starts, A goes to the settings. The title
is the cover of a crime game as everybody knows it: pictures in frames like
a page of a comic (money, the player with a pistol, the city, a car to get
away in, the police) and the name in the middle, in heavy letters with slits
for openings. The console's menu shows the same picture, 8 rows taller.

The settings are reached from the map as well. Up and Down pick a line, B
changes it, A goes back.

| Setting | What it does | To begin with |
|---|---|---|
| Sound | On or off, for this game only | As the console has it for all its games |
| Police light | The light next to the screen: red, blue, red, blue, as long as there are stars. At a quarter of its brightness. Nothing else ever uses the light: it stays dark on the title, the map and the settings, also while it is being switched on there | Off |
| Start over | No money, no mission done, and the player where the game begins. B asks `SURE?`, B again does it. The two settings above stay | |

The settings, the money and the missions done are kept when the console is
switched off. They are stored on the flash chip, in 4 KB that the list of
games sets aside for this game, not in the console's small settings memory,
where games get in each other's way. They are written when a setting has
been changed, when a mission is passed, and on the way out to the console's
menu (Up + Down).

## Money, the police, and how it ends

- **Money.** Whoever is shot or run over leaves a dollar sign hanging in the
  air over them: $10 to $73, picked up by walking or driving up to it. It lies
  there for about 25 seconds.
- **The record.** A shot fired counts 1, taking a car with its driver or
  shooting at one 2, a person killed 4, an officer killed 16. One star from 8,
  two from 24, three from 56, four from 120: the second person shot brings the
  first star.
- **The police.** For every star one police car or officer is after you,
  if there is one to be had: a car is looked for near by, and if none is
  found, nobody comes. With one star they take their time and look every
  three seconds only, which makes it about every other time that nobody
  comes at all before the star is forgotten. They do not know where you are:
  they know where they saw you last, or where somebody called them to, and
  that is where they go. A police car takes whatever street leads there,
  lanes or no lanes, a little slower than the fastest a car can go. It drives
  into a moving car it sees (one dot of health each time). If you are on foot
  or slow it stops and its officer gets out.
- **Officers** are slower than you: whoever keeps moving gets away.
  - *One star: they arrest.* An officer has to have hold of you for almost
    two seconds (the HUD says `GET AWAY!`): time to run, or to turn round and
    shoot. Only then: BUSTED.
  - *Two stars and more: they shoot*, every second and a half, and hit half
    the time. A hit costs one dot of health with two stars, two with three,
    three with four. Nobody is arrested any more.
- **Health** is 16 dots. At none: WASTED. It comes back by itself, a dot every
  2.5 seconds, while there are no stars.
- **Getting away.** The police has you in sight when a car or an officer is
  within 8 cells with no building in between. Round a corner they lose sight
  of you, and go to the corner.
  - *Out of sight for 4 seconds: they have lost you.* The stars blink. Nobody
    goes after you and nobody new is sent; police cars drive on like traffic
    (keeping their eyes open), officers stand where they are.
  - *Another 4 seconds: a star is forgotten*, and one more every 4 seconds,
    as long as nobody sees you. Anything new on the record brings them back.
  - *Called, but never there in time:* if no police has seen you 9 seconds
    after what you did, they give up looking, and the first star is
    forgotten after 13.
  - *Up to two stars, outrunning the officers is enough.* Nobody takes their
    place as long as they are within 18 cells. From three stars on the next
    car is on its way as soon as an officer is 8 cells behind: on foot you
    will not make it, in a car you may.
- **WASTED or BUSTED** costs half the money. The game goes on from where it
  started, with full health and no stars.

How often they come, and how it goes (the desktop build, every run with dice
of its own):

| | Now | The build before (2026-09-29, 03:00) | The one before that |
|---|---|---|---|
| Standing still after the first star: the police came | 22 times of 48 | 48 of 48 | 30 of 48 |
| Shooting at whoever comes along, never getting out of the way: the police is there, from the first star | after 0 to 19 s, 5 in the middle | 0 to 7 s, 1 | 0 to 11 s, 2 |
| ... and it is over (WASTED mostly, four stars mostly) | after 7 to 71 s, 38 in the middle | 7 to 74 s, 35 | 6 to 70 s, 34 |

Getting away, tried by a driver and a runner who know how (the desktop
build's `flee`: round the corners, away from the police; they set off when
the police has arrived and seen them; 24 tries for every line, of which
those count in which the police came: 8 with one star, 22 with more):

| | Got away, by car | Took | Got away, on foot | Took |
|---|---|---|---|---|
| One star | 8 of 8 | 11 to 66 s | 8 of 8 | 12 to 18 s |
| Two stars | 11 of 22 | 13 to 38 s | 20 of 22 | 17 to 22 s |
| Three stars | 9 of 22 | 17 to 48 s | 6 of 22 | 37 to 73 s |
| Four stars | 10 of 22 | 22 to 39 s | 5 of 22 | 31 to 57 s |

With the rules as they were at first (the police always knew where the player
was, and a star took 10 seconds each to forget) the same driver got away 4
times out of 84, never with more than two stars, the runner 18 times out of
84, once with three.

(The figures that stood here before, 12 tries a line, came from runs whose
dice were only a few throws apart, which made them more alike than they
should have been.)

Where to turn the screws (`game.h`): `GRIP_BUSTED`, `COP_SPEED`, `CHASE_SPEED`,
`SIGHT`, `CALM_SEEN`, `CALM_LOST`, `CALM_STAR`, the numbers in `ped_kill()`
and `cop_step()`, in `ped_step()` from how many stars on an officer left
behind is replaced, in `cars_step()` how often a police car is looked for
(every 64 frames with one star, every 16 with more) and in `traffic_spawn()`
how hard (4 tries; with 12 they always come).

## Measured performance

**18 to 25 fps** in the street, up to about 40 close to walls, on a real
Arduboy FX (measured over USB on 2026-09-29), in 4-shade grayscale. Twice as
many people as before cost two or three frames a second. On the real screen
the picture was judged to look great.

The same 12 seconds (the player turning round and round where the game
begins), played by builds that play by themselves (`-DPROBE`):

| Build | Pictures a second |
|---|---|
| Milestone 4 as it was on the console (with USB) | 24.0 |
| The same without USB, with the two options of the compiler and the rewrites | 24.25 |
| Milestone 5: with missions | 23.9 to 24.0 |

The first version put on the console showed a black screen although it ran
fine in the emulator; see "Lessons from the real console" below.

## Try it in the emulator

```bash
python3 tools/serve.py build 8642
```

Then open <http://localhost:8642/ardens.html?pkg=game/SmallTheftAuto.arduboy>.
Keys: the arrows, `S` for the console's B button (accelerate, fire) and `A` for
its A button (brake, sprint). Click the picture first so it has keyboard focus.

`ardens.html` is a small wrapper that loads the Ardens web emulator from its
official page and hands it the freshly built files from this machine.

## Put it on a real Arduboy FX

The build produces `build/game/SmallTheftAuto.arduboy`: program, flash data,
4 KB for the game to write its settings to, and the title picture for the
console's menu, in one file.

**The game has no USB connection** (since milestone 5: it is 3.6 KB of
program that the missions needed). While the game is on the screen the
computer does not see the console, and nothing can be loaded. Hold Up + Down
for two seconds (or switch the console off and on): the console's menu has
the connection.

With the console switched on, plugged in and showing its menu:

```bash
python3 ../CartManager/cartmanager.py update
```

replaces the old build in the console's menu (under "My games") with the new
one and leaves every other game on the console as it is. (The game's old name
is noted in `../CartManager/sources.json`, so the entry called Two-Bit City
was replaced too, not kept next to the new one.) The game list chooser
in `../CartManager` shows the new build too, for when the choice of games
should change as well. On the console: right, down, A.

The game finds its data wherever the list puts it, so it needs no fixed place
on the flash chip.

**4-shade grayscale depends on display timing** that the emulator cannot fully
judge. If the picture flickers or shows bands on the real screen, that is the
thing to report.

**The FX-C and the Mini** (since 2026-10-03) run the same build. Their flash
chip is selected by PE2 instead of PD1; the game looks for its data on PD1
and then on PE2 when it starts, and drives only the line it found it on.
Their panels are said to flicker with the four shades, so on them the game
starts with GRAYSCALE OFF: two shades, the picture sent as it is every third
refresh, the panel scanning by itself. Tried in the emulator on both wirings
(`python3 tools/package.py <hex> <bin> <out> ArduboyMini` makes a package the
emulator puts on PE2; an old build shows no title picture there), not on a
real FX-C.

## Build

```bash
tools/build.sh
```

This regenerates the assets, compiles the program and packages both, in
`build/game`. That folder is what the list of games on the console is made
from: it is for builds that are meant to go there. `OUT=dev tools/build.sh`
builds the same into `build/dev`, for trying out. The Arduino
toolchain lives in `.toolchain/` inside this folder; nothing is installed
system-wide. The compiler is an Intel binary, so an Apple Silicon Mac needs
Rosetta 2.

Test builds:

```bash
EXTRA_FLAGS=-DSELFTEST OUT=selftest tools/build.sh
```

runs the assembly routines and their C++ reference versions side by side on the
console, and compares the direction of every column's ray, which the program
works out, with the table it used to look it up in; the HUD shows columns
drawn and columns that differ (should stay 0).

```bash
EXTRA_FLAGS=-DPROFILE OUT=profile tools/build.sh
```

shows time per frame for each part of the renderer, in units of 0.1 ms.

```bash
EXTRA_FLAGS=-DPROBE OUT=probe tools/build.sh
python3 tools/lab/probe.py probe 3 picture.png
```

is the game as it is played, playing by itself: it starts, stands for 2
seconds, turns round and round for 12, writes down how many pictures that
made, how much of the stack was never used and the last picture, and goes
back to the console's menu, where the computer reads what it wrote. It is
the way to try a build that has no USB connection on the console.

```bash
EXTRA_FLAGS=-DDIAG OUT=diag tools/build.sh
python3 tools/diag.py load
python3 tools/diag.py state 10
python3 tools/diag.py picture picture.png
python3 tools/diag.py press 80 1.5
python3 tools/diag.py stars 2
```

builds a version that lets the computer look into the console's memory over
USB, and write to it, and puts it straight into the console's processor (the
game list is not touched). `state` says what the game is doing (where the
player is, stars, police, the way to go, the mission, pictures a second); `picture` fetches
the picture as it is on the screen; `press` holds buttons down, so that the
game can be played from the computer (`80` is Up); `stars` puts stars on the
record; `peek` and `poke` do the same for any variable of the program by its
name. Where a variable is, `diag.py` knows from the build. The test build
itself knows nothing of all that: it hands out memory and takes it, which
costs 0.6 KB of program instead of the 2 KB of reports it had before. Picking
the game in the console's menu brings the normal build back.

If the game list does not hold this build's game data yet, `load` puts the data
at the end of the flash chip, which the list does not reach, in front of the
last 4 KB: those are what a build loaded this way writes its settings to.

The test build carries the USB connection on top of the game and is full to
the last 0.2 KB (29.5 of 29.7 KB, with one more option of the compiler than
the game has). Its stack comes within 43 bytes of the variables. When the
game grows, the test build will have to leave something out.

Until milestone 5 the normal build had a USB connection too and answered the
letter `s` with one line of status. A build with `-DUSB_LINK` still does:

```bash
EXTRA_FLAGS=-DUSB_LINK OUT=link tools/build.sh
python3 tools/diag.py load link
python3 tools/diag.py watch 5 1:s 2:s 3:s
```

```bash
host/build.sh 1100 7
```

builds the same engine for the desktop and lets an autopilot play: it walks to
the car, gets in, drives a route, gets out, walks on, fires the pistol, picks
up the money and ends up BUSTED. The run is written to `build/host/run.gif`.
More scenes, run with `SCENE=...` in front of `build/host/host_sim`: `jack`
takes a car that is driving past, `people` runs someone over, `shoot` walks
the pavements with the pistol, `car` fires at the traffic, `range` fires one
shot at somebody standing `RANGE` cells ahead and fetches the money. With the
police: `busted` shoots somebody and waits, `wasted` walks off with two stars
and little health, `chase` drives the route with three stars, `escape` shoots
somebody and takes the car, `forget` shows the stars going away, `pages` goes
through title, settings and map, `walk` walks, runs, stands and turns and
says which step of the walk is shown, `flee` gets away from the police with
`STARS` stars (in a car; on foot with `FOOT=1`) and says how long it took,
`nav` brings up the map, puts the cross where the drive of the tour ends
(or on `NAV_TO=x,y`, with the player at `HERO_AT=x,y`), goes on the tour and
says what arrow and distance show and what they should. `SEED` gives any
scene other dice, `TRACE=1` prints where the police is, `SETTINGS=3` starts
with sound and police light switched on.

`PLAY` plays by a list of orders instead of a scene, which is how missions
are tried (the orders are listed at the top of `host/host_main.cpp`):

```bash
PLAY="walk:91.4,154.6;down;wait:30;b;car;drive:110,153.5;drive:112.5,116;drive:119,113.5;stop" \
  build/host/host_sim build/game/fxdata.bin build/host/frames.raw 900 7
```

walks to the first telephone, answers, takes the mission, gets into the
nearest car and drives to the garage. `DONE=210` says how many of its
missions every telephone has seen done, `CASH=100` how much money there is.

```bash
python3 tools/lab/regress.py save before
python3 tools/lab/regress.py check before
```

plays 22 scenes (10 of them missions) and compares the pictures, frame by
frame, and what happened with a run kept earlier: the way to make sure that a
change that is not meant to show does not show.

```bash
python3 tools/sound.py build/sound
```

plays the sounds on paper, the way the console's program would, and writes
them as `.wav` files to listen to on the computer. The console's small speaker
sounds thinner than that.

## Layout

| Path | What |
|---|---|
| `SmallTheftAuto/` | The program (Arduino sketch) |
| `SmallTheftAuto/engine.h` | Renderer, with C++ reference versions of the inner loops |
| `SmallTheftAuto/render.S` | The inner loops in assembly: ground, walls, ray walk |
| `SmallTheftAuto/display.S` | Display refresh interrupt: grayscale, pages, and the arrow laid over the picture |
| `SmallTheftAuto/fastmath.S` | Multiply routines, flash data lookup |
| `SmallTheftAuto/game.h` | Player on foot and driving, the pistol, cars, people, money, the police, the way to go, missions, camera, HUD |
| `SmallTheftAuto/pages.h` | Title, map (and picking a place on it), settings, a mission offered |
| `tools/missions.py` | The missions: telephones, places, texts, steps |
| `SmallTheftAuto/platform.h` | Flash chip, buttons, frame clock, the light |
| `SmallTheftAuto/sound.h`, `sound.S` | Sound: set-up, and the interrupt that makes it |
| `tools/sound.py` | The sounds themselves, and a way to hear them on the computer |
| `SmallTheftAuto/diag.h`, `tools/diag.py` | Test build that reports over USB, and the computer's end of it |
| `SmallTheftAuto/probe.h`, `tools/lab/probe.py` | The build that plays by itself, and the computer's end of it |
| `SmallTheftAuto/tables.h`, `consts.h`, `fxdata.h` | Generated by the asset pipeline |
| `tools/build_assets.py` | Asset pipeline: city, textures, sprites, flash image |
| `tools/citygen.py` | Procedural city generator |
| `tools/sprites.py` | Renders 3D models to sprites at every angle and size |
| `tools/title.py`, `assets/title.png`, `assets/title_game.png` | The title picture, drawn dot by dot: for the console's menu (64 rows) and for the game (56 rows) |
| `tools/arrows.py` | The arrow that shows the way, in 32 directions |
| `host/` | Desktop test build |
| `tools/lab/shades.py` | Draws the game in two shades from recorded scenes, every candidate dot pattern next to the four shades, for choosing one |
| `tools/lab/` | Tools for measuring: `stack_depth.py` (how deep the stack can get, from the machine code), `size_map.py` (where the program space goes), `size_flags.py`, `size_trial.py`, `size_try.py` (what options of the compiler, changes to the sources and pieces of the program cost; `trials/RESULTS.md` has what was found), `same_asm.py` (are the routines that are timed by hand the same in two builds), `regress.py` (does the game still do what it did), `frames.py` and `sprite_look.py` (pictures out of a run, models as the game shows them), `console_do.py`, `console_go.py` and `console_spree.py` (play on the console from the computer, test build), `police_*.py` (how often the police comes, how a rampage goes, who gets away; many runs of the desktop build) |
| `LICENSE` | The MIT licence: anybody may do with it what they like, as long as the notice with Joël Coster's name stays in |
| `preview/` | The concept clip and a clip from the desktop build; `preview/source/` is what drew the concept clip |
| `post/`, `tools/post_clip.py` | For showing the game to people: the text of a post for the Arduboy forum and how to post it (`post/README.md`); the tool plays scenes with the desktop build and cuts a tour (video), a short clip (GIF) and single pictures from them, into `post/`. `tools/lab/frames_to_mp4.swift` writes the video with what macOS brings along, `mp4_frame.swift` takes a picture out of one |

## How it works

- **The city is a 256 x 256 grid of 4 m cells**, one byte per cell, the same grid
  size GTA 1 used. It is stored on the flash chip.
- **One ray per screen column** walks the grid. Tall buildings show over low ones.
  The 3D view is 64 double-wide columns by 56 rows; the bottom 8 rows are the HUD.
- **Cars, people, trees and lamps are pre-rendered** from 3D models at up to 32
  angles and 24 sizes and stored on the flash chip (about 0.8 MB). The console
  only copies them. What the player is (on foot, or any of the cars) has its own
  set, seen from the chase camera at 64 or 32 angles.
- **Every car but the player's sits in one pool of 12**: traffic, cars the city
  parked, cars the player left behind. Getting in takes a car out of the pool,
  getting out puts one in.
- **Parked cars are not stored anywhere.** Whether a cell of pavement or parking
  lot holds a car, and which, follows from its position, so the same cars stand
  in the same places every time. The last four the player took stay gone.
- **Traffic follows the lanes** and waits for whatever is in its way: for the
  player as long as it takes, for other cars five seconds.
- **People walk the pavements** and turn at corners: 16 of them, where the
  player is heading. They appear out of view or a good way off, and whoever is
  left behind makes room. A driver whose car is taken gets out and runs.
  Someone hit by the player's car at speed stays down. Whoever hears a shot
  runs, away from the player and across the road if need be, and calms down
  after a while.
- **Everybody walks in four steps**: a foot set down ahead, the other leg
  swinging past, and the same the other way round. It is made to show from
  behind, which is how the player sees their own figure: the leg that swings
  is a leg that gets shorter, the body goes down a row with both feet on the
  ground, the arms end higher or lower. One leg is a shade lighter than the
  other and there is dark between them, so that two legs can be told apart
  at any size. The step shown follows from the distance covered (the player:
  four steps to a cell, which makes 2.5 a second walking and 4 running), for
  people in the street from where they are. Standing still is a picture of
  its own.
- **The police is made of what was there.** A police car is traffic of its
  own kind: with stars in the HUD it picks, cell by cell, the street that
  leads to where the player was seen last. An officer is a person of their
  own kind, to whom running means running there. One clock says how long
  ago the police knew where the player was; when it has run out, police
  cars are traffic again and officers stand.
- **WASTED and BUSTED are sprites** like everything else, put straight into
  the list of things to draw instead of somewhere in the city.
- **The pistol hits the first thing on its line**: a person, a car, a wall. A
  near miss on a person counts as a hit (about 8 degrees either side), because
  nobody aims to the degree with a cross of buttons. Range is 12 cells, 48 m.
- **On foot the camera looks over the player's shoulder.** Seen from straight
  behind, the player hides exactly what they are aiming at. The camera picks
  the shoulder with more room, so that a wall next to the player does not fill
  the picture; the pistol is in the hand on the camera's side.
- **Sound is made by a timer alone.** The speaker sits between two pins that
  timer 4 drives, one the opposite of the other. A sound is a short list of
  steps: how long the periods are, how much chance stretches them (which turns
  a tone into noise) and how wide the pulses are (narrow is quieter). A small
  interrupt rolls the dice for every period. The shot is 29 bytes. Without
  chance the same thing plays notes: the money, the siren, the end.
- **Trees stop cars and people, lamp posts only people.** Only what the renderer
  has gathered in front of the camera is known, which is where the player goes.
- **Grayscale** comes from showing three 1-bit pictures in turn, 156 times a
  second, in step with the panel's refresh. The step-keeping method is the one
  from Peter Brown's ArduboyG library. Unlike ArduboyG, the scene is drawn once
  into a 2-bit picture and the three pictures are derived from it while they are
  sent, which is what allows a slow 3D renderer underneath.
- **Two shades** (GRAYSCALE OFF) come from the same picture: level 3 lit,
  level 0 dark, level 2 a checkerboard over the two panel dots of a view dot
  and two rows, level 1 the top left dot of those four. The display routine
  sends that every third refresh and the panel is not parked, so it scans by
  itself as it does for any other game. The clock ticks every refresh as
  before.
- **Pages are black and white and 128 dots wide.** The 3D view has dots twice
  as wide as high, which is no good for lettering or a map. For title, map
  and settings the display routine takes the same memory differently: of
  every two columns of dots the left one from one bit plane, the right one
  from the other. The title picture and the map of the whole city (two cells
  to the dot) are on the flash chip.
- **The arrow is not in the picture: the display routine lays it over.** An
  arrow of 11 dots each way cannot be drawn in dots twice as wide. For every
  one of its 12 columns of dots the display routine has two bytes (48 for
  the two halves of 8 rows each): what to keep of the 3D view, and what to
  light up. It puts them together while it sends the picture, in all three
  gray planes, so the arrow is white with a black line round it and the
  view shows in its grays right up to that line. The 32 arrows are on the
  flash chip; the one that is needed is fetched when the direction changes.
  The distance next to the arrow is 9 columns of the view, 8 rows, that the
  display routine takes the way it takes a page: black and white, in single
  dots, with the HUD's lettering.
- **Which way, and how far, comes from one loop.** Of 32 directions, counted
  from where the camera looks, the one in which the place lies furthest
  ahead is the way, and how far ahead is the distance (off by half a
  percent at most). No arc tangent, no square root.
- **Reading the flash chip is one routine**, wherever from: so many bytes
  from there to here. It used to be written out in eight places, which was
  0.3 KB more.
- **What is kept is kept on the flash chip**, seven bytes for every change
  (the settings, the money, how many of its missions every telephone has
  seen done, and a byte that makes the sum come out: an entry the console was
  switched off in the middle of does not count), in 4 KB of the game's own;
  when they are full they are wiped and begun again. Settings kept by
  milestone 4, one byte each, are still read.
- **A mission is data.** On the flash chip it is 512 bytes: its text, as
  places in the lettering, and up to eight steps. A step says what ends it
  (being at a place, so many people down, no stars), what it takes (a car of
  a kind, standing still, only officers count, only the one with the arrow
  over them counts), what the clock is set to, how many stars are handed out,
  and two hints for the bottom line. The program reads the step that is due
  and waits. 2.5 KB of program play any number of missions.
- **Whoever a mission is about is there when the player gets near**: put in
  the place of somebody who is just walking by, 12 cells off. They walk
  their rounds like anybody else and run when they hear a shot; the arrow
  follows them.
- **The direction of every column's ray is worked out**, not looked up:
  `m * 210 - ((m * 20 + 140) >> 8)` for m = 2c - 63 gives the 64 values of
  the table there used to be, to the last bit. The asset pipeline finds the
  three numbers, and stops if there are none.
- **Each column is drawn in a scratch buffer and copied to the picture in one
  go**, even columns first, then odd ones. There is no second frame buffer: the
  console has 2.5 KB of memory in total.

## Lessons from the real console

- **Set the refresh timer's mode before its period.** Arduino's start-up code
  leaves timer 3 in an 8-bit PWM mode. In that mode the chip keeps only the low
  8 bits of a period written to it: 1602 became 66 (read back on the console).
  The refresh interrupt then ran about 3700 times a second instead of 156, each
  run takes 1.2 ms, and the game got no processor time: black screen. The
  emulator does not imitate this, so the build ran there. `refresh_period()` in
  `SmallTheftAuto.ino` stops the timer, leaves PWM mode, then writes the period.
- **The emulator passing is not enough.** Before a build goes into the
  console's menu, load it with `tools/diag.py load game` and ask it for its
  status: frames per second above 20 and `fail=0` mean it runs.
- **Sound can be checked without ears.** The test build makes the timer play a
  steady tone and watches the two speaker pins from the program (`q`): on the
  console they switched at counts 0 and 32 of 125, exactly opposite to each
  other, 1000 times a second. A shot made 273 to 281 interrupt calls there;
  `tools/sound.py` expects 262 to 304. The other four sounds came out inside
  what it expects as well. How it *sounds* still takes ears.
- **The bottom row of the screen never lights up** (the display waits there
  between pictures), so HUD text sits one row higher than it first did.
- **A page is drawn when it changes, not over and over.** Wiping and
  redrawing it many times a second showed as flicker: the display picks up
  the memory at any moment, half drawn or not.
- **Shaded 3D models turn to mush in black and white.** The title's car was
  first drawn from the game's model, with dots for the shades in between; at
  this size it could not be made out. Everything on the title is drawn by
  hand now.
- **A title has to say what kind of game it is.** A sunset over a road says
  racing game. Frames like a comic's and the heavy lettering say crime game
  at first sight, which is why the title looks the way it does.
- **Grey made of dots swallows thin lines.** On the title, anything drawn
  with lines one dot wide stands on black or on white.
- **Legs that swing forwards and backwards do not show from behind.** The
  first walk had four frames and from the chase camera all four looked the
  same: the figure slid along. What shows from behind is up and down.
- **A figure five dots wide only comes out clean when it stands square to
  the dots.** The camera over the shoulder sees the player from 6 degrees to
  the side; drawn from there, the legs ran into one another in some frames.
  Seen from almost behind, the player is now drawn as seen from behind.
- **An arrow needs eleven dots.** In 7 by 7 an arrow that points anywhere
  but up, down, left or right is a blob, and so it is in dots twice as wide
  as high at any size that leaves the picture alone. Hence the trouble taken
  to show it in single dots.
- **A cross that turns the dots under it round does not show on a map.** On
  a street it is dark, on a house lit, across both it falls apart. The cross
  is lit with a dark edge now, and what it stood on is fetched again from the
  flash chip when it moves.
- **Two directions cannot be told apart from 15 m in whole metres.** The
  arrow was off by two steps close to the place it led to, until distances
  were counted in sixteenths of a metre.
- **Test runs need dice of their own.** Twelve runs whose dice were a few
  throws apart gave the same answer more often than they should have: the
  police came "always", or "half the time", depending on which twelve.
  `SEED` now puts every run far from the others in the sequence.

- **A build without USB cannot be asked how it is doing.** It can be made to
  play by itself, write down how it went, and go back to the console's menu,
  where the computer reads what it wrote (`-DPROBE`). Without USB interrupts
  such runs come out the same to the frame.
- **The loader leaves USB switched on.** A program that has no USB interrupt
  has to switch it off first thing, or the first interrupt lands nowhere.
- **Somebody with their back to the wall ran through it.** Whoever is
  frightened takes no way that leads towards the player; with no other way
  left, the rule picked the way back without looking at it. Seen when the
  first mission put a man into the corner of a plaza.
- **What the computer measures of a trial is only worth what was looked at.**
  The first way of working out the direction of a ray saved 114 bytes on
  paper and was wrong (the product did not fit 16 bits); it had been
  measured, never run.

## Budget

| | Used | Limit |
|---|---|---|
| Program | 26.8 KB | 29.7 KB |
| Memory | 2147 bytes | 2560 bytes |
| Flash chip | 1.07 MB | 16 MB |

The FX-C (one build for both consoles, two shades in the settings) took 596
bytes of program and 5 of memory: the search for the chip's select line and
the two lines it drives about 230, the two-shade display routines about 130,
the settings line and the lettering ten rows apart about 140, the rest the
calls that fx_end() became. The stack has the 413 bytes that the variables leave. Going by the machine
code it needs 177 at the most (the deepest chain of calls, drawing a sprite,
157; the display routine, 20 on top). On the console 234 bytes of it were
never used.

Milestone 4 was 28.2 KB with 1.5 KB to spare. Without the USB connection,
with two options of the compiler and eight rewrites it came to 23.7 KB
(`tools/lab/trials/RESULTS.md`); the missions took 2.5 KB of that, the FX-C
0.6 KB. 2.9 KB are left. The `-DUSB_LINK` build (the game with a USB status
line) no longer fits; `-DPROBE` does. In reserve: a third option of the compiler (0.4 KB, 1.5% slower) and
half a sine table (0.2 KB, 1% slower).

## Roadmap

1. Drive-around tech demo (done)
2. On foot, getting in and out of cars, parked cars, pedestrians (done)
3. A pistol, people who run, the first sound (done)
4. Money from whoever goes down; stars, police cars, officers, health, WASTED
   and BUSTED; a title, a map, settings, and the way to a place picked on
   the map (done)
5. Missions, scripted from the flash chip; saving (this milestone)
6. A hand-designed city with districts, more sound, polish
