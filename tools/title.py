#!/usr/bin/env python3
"""
Draw the title picture: black and white, 128 dots wide.

  python3 tools/title.py assets [enlarged.png]

writes two pictures into the folder given:

  title.png        128 x 64, what the console's game menu shows
  title_game.png   128 x 56, what the game itself shows when it starts; the
                   8 rows below it are where the game writes which button
                   does what. tools/build_assets.py puts it on the flash chip.

The picture is the cover of a crime game as everybody knows it: pictures in
frames like a page of a comic, and the name in the middle in heavy letters
with slits for openings. The pictures show what there is in the game: the
city, the player with a pistol, money, a car to get away in, the police.

The two pictures are the same down to row 55. The frames of the bottom row
are 8 rows taller in the menu's picture, and show that much more.

Everything is drawn here, dot by dot: shaded 3D models turn to mush in black
and white at this size. In the drawings

  #  lit            .  dark           o  every other dot lit (grey)
  :  one dot in four lit              (space)  nothing: what is behind stays
"""
import os, sys
from PIL import Image

W = 128
MENU_ROWS, GAME_ROWS = 64, 56

# ---------------------------------------------------------------- the name
# Letters 12 rows tall: 2 rows that only the tall ones use, 10 rows for all.
# Strokes are 3 dots wide, the openings 1: that is what makes them look heavy.
LETTERS = {
    "s": ["       ", "       ", ".######", "#######", "###....", "######.",
          "#######", ".######", "....###", "#######", "#######", "######."],
    "m": ["           ", "           ", "##########.", "###########", "###.###.###", "###.###.###",
          "###.###.###", "###.###.###", "###.###.###", "###.###.###", "###.###.###", "###.###.###"],
    "a": ["       ", "       ", ".#####.", "#######", "....###", ".######",
          "#######", "###.###", "###.###", "#######", "#######", ".######"],
    "l": [".##", "###", "###", "###", "###", "###",
          "###", "###", "###", "###", "###", "###"],
    "t": ["..###..", "..###..", "#######", "#######", "..###..", "..###..",
          "..###..", "..###..", "..###..", "..###..", "..#####", "...####"],
    "h": ["###....", "###....", "######.", "#######", "###.###", "###.###",
          "###.###", "###.###", "###.###", "###.###", "###.###", "###.###"],
    "e": ["       ", "       ", ".#####.", "#######", "###.###", "###.###",
          "#######", "#######", "###....", "#######", "#######", ".#####."],
    "f": ["#######", "#######", "###....", "###....", "#####..", "#####..",
          "###....", "###....", "###....", "###....", "###....", "###...."],
    "u": ["       ", "       ", "###.###", "###.###", "###.###", "###.###",
          "###.###", "###.###", "###.###", "#######", "#######", ".######"],
    "o": ["       ", "       ", ".#####.", "#######", "###.###", "###.###",
          "###.###", "###.###", "###.###", "###.###", "#######", ".#####."],
}


class Picture:
    def __init__(self, rows):
        self.rows = rows
        self.img = Image.new("L", (W, rows), 0)
        self.px = self.img.load()
        self.clip = (0, 0, W - 1, rows - 1)

    def dot(self, x, y, sign):
        x0, y0, x1, y1 = self.clip
        if sign == " " or not (x0 <= x <= x1 and y0 <= y <= y1):
            return
        lit = (sign == "#" or (sign == "o" and (x + y) & 1 == 0)
               or (sign == ":" and x & 1 == 0 and y & 1 == 0))
        self.px[x, y] = 255 if lit else 0

    def fill(self, x0, y0, x1, y1, sign):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.dot(x, y, sign)

    def line(self, x0, y0, x1, y1, sign, every=1):
        """A line; with every = 2 it is dotted."""
        n = max(abs(x1 - x0), abs(y1 - y0), 1)
        for k in range(0, n + 1, every):
            self.dot(int(round(x0 + (x1 - x0) * k / float(n))),
                     int(round(y0 + (y1 - y0) * k / float(n))), sign)

    def disc(self, cx, cy, r, sign):
        for y in range(int(cy - r - 1), int(cy + r + 2)):
            for x in range(int(cx - r - 1), int(cx + r + 2)):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r + 0.5:
                    self.dot(x, y, sign)

    def stamp(self, rows, x, y, mirror=False):
        """A drawing made of the signs above, its top left corner at (x, y);
        with mirror, every row is followed by its mirror image."""
        for r, row in enumerate(rows):
            line = row + row[::-1] if mirror else row
            for k, sign in enumerate(line):
                self.dot(x + k, y + r, sign)

    def word(self, text, x, y):
        for c in text:
            self.stamp(LETTERS[c], x, y)
            x += len(LETTERS[c][0]) + 1

    def frame(self, x0, y0, x1, y1, sign):
        """A picture's frame, filled; what is drawn from now on stays inside it."""
        self.clip = (0, 0, W - 1, self.rows - 1)
        self.fill(x0, y0, x1, y1, "#")
        self.fill(x0 + 1, y0 + 1, x1 - 1, y1 - 1, sign)
        self.clip = (x0 + 1, y0 + 1, x1 - 1, y1 - 1)
        return x0 + 1, y0 + 1


# ---------------------------------------------------------------- the pictures

# ---- the player: dark glasses, hair combed back, aiming a pistol. On white.
HERO = [
    "      ........                       ",
    "    ............                     ",
    "   ..............                    ",
    "   ...............                   ",
    "   ......#######..                   ",
    "   .....#########.                   ",
    "   ....##########.                   ",
    "   ...............                   ",
    "   .##.#....#.#..                    ",
    "   .##......#...                     ",
    "   .#.#....###..     ............... ",
    "    ..#########.    .................",
    "     .#######.##.   ..###......####..",
    "     .#########.    .................",
    "     .####....#.    ...............  ",
    "     .#########.    .#####..  .      ",
    "      .#######.   ...######.....     ",
    "      .#......  .....####......      ",
    "     ..####.  .......#######.        ",
    "   ....####..........####....        ",
    " ........###.........######.         ",
    "..........##.................        ",
    "...........#................         ",
    "..........................           ",
    ".........................            ",
    "........................             ",
    "........................             ",
    ".......................              ",
    ".......................              ",
    ".......................              ",
    "......................               ",
    "......................               ",
    "......................               ",
    "......................               ",
]

# ---- the police, from the front: the left half, the right is its mirror image
POLICE = [
    "   #     #    #  ",
    "    #     #   #  ",
    "     #    #      ",
    "           ######",
    "          #######",
    "          ##ooooo",
    "        #########",
    "       ##########",
    "      ##.........",
    "      #..#.......",
    "     ##.#........",
    "     #...........",
    " ## ##...........",
    " #####...........",
    "  ###############",
    " ################",
    "#################",
    "#......##########",
    "#.####.#.........",
    "#.####.#.########",
    "#.####.#.........",
    "#......#.########",
    "#################",
    "###...###########",
    "#################",
    " ......##########",
    " ooooooo         ",
    " ooooooo         ",
    "  ooooo          ",
]

# ---- the car to get away in, from the side, going right
GETAWAY = [
    "            ###########                  ",
    "          ##....#......##                ",
    "         ##.....#.......##               ",
    "        ##......#........###             ",
    " ########################################",
    "#########################################",
    "#################.#####################.#",
    "####.....########.#######.....###########",
    "###.ooooo.#######.######.ooooo.##########",
    " #.ooo#ooo.############.ooo#ooo.######## ",
    "  .oo###oo.            .oo###oo.         ",
    "  .ooo#ooo.            .ooo#ooo.         ",
    "   .ooooo.              .ooooo.          ",
]

# ---- money
NOTE = [
    "......................",
    ".####################.",
    ".#.######....######.#.",
    ".###..##..##..##..###.",
    ".##.##.#.#..#.#.##.##.",
    ".##.##.#.####.#.##.##.",
    ".##.##.#.#..#.#.##.##.",
    ".###..##..##..##..###.",
    ".#.######....######.#.",
    ".####################.",
    "......................",
]

NOTE_BEHIND = [NOTE[0], NOTE[1]] + [NOTE[1]] * 7 + [NOTE[1], NOTE[0]]

DOLLAR = [
    "    ...    ",
    "  ...#...  ",
    " ..#####.. ",
    "..#######..",
    ".###.#.###.",
    ".###.#.....",
    ".#######.. ",
    "..#######..",
    " ..#######.",
    ".....#.###.",
    ".###.#.###.",
    "..#######..",
    " ..#####.. ",
    "  ...#...  ",
    "    ...    ",
]


PALM = [
    "    ...     ..   ",
    "  ......  .....  ",
    " ...  ........ . ",
    "..  ....... ...  ",
    ".  .. ......  .. ",
    "  ..  .. ....  ..",
    " ..  ..  .. ..  .",
    " .   .   ..  ..  ",
    "    ..   ..   .  ",
    "    .    ..   .  ",
    "        ..       ",
    "        ..       ",
    "        ..       ",
    "       ..        ",
    "       ..        ",
    "       ..        ",
    "      ...        ",
    "      ...        ",
    "      ...        ",
    "     ....        ",
]


def skyline(p, x, y, shore):
    """The city across the water, the sun low behind it, a palm on this side."""
    p.disc(x + 23, shore - 3, 8, "o")
    #          from the left, width, height
    houses = ((12, 4, 4), (16, 4, 7), (20, 5, 3), (25, 3, 5), (28, 5, 11), (33, 4, 7))
    for k, (at, wide, tall) in enumerate(houses):
        p.fill(x + at, shore - tall, x + at + wide - 1, shore, ".")
        for wy in range(shore - tall + 2, shore, 2):
            for wx in range(x + at + 1, x + at + wide - 1, 2):
                if (wx * 7 + wy * 3 + k) % 5:
                    p.dot(wx, wy, "#")
    p.fill(x + 30, shore - 14, x + 30, shore - 12, ".")             # something on the roof of the tallest
    p.fill(x, shore + 1, x + 36, shore + 40, ".")                    # the water
    for k, (wx, wide) in enumerate(((18, 11), (24, 5), (16, 7), (29, 5), (19, 4))):
        p.fill(x + wx, shore + 2 + k, x + wx + wide - 1, shore + 2 + k, "#")
    p.stamp(PALM, x - 1, y)


def picture(rows):
    p = Picture(rows)
    bottom = rows - 1

    # ---- the name, in the middle
    p.word("small", 42, 1)
    p.word("theft", 47, 14)
    p.word("auto", 44, 27)

    # ---- the pictures around it
    x, y = p.frame(0, 0, 38, 26, ".")
    p.stamp(NOTE_BEHIND, x + 15, y + 4)
    p.stamp(NOTE_BEHIND, x + 13, y + 7)
    p.stamp(NOTE, x + 11, y + 10)
    p.stamp(DOLLAR, x, y + 5)

    x, y = p.frame(0, 28, 38, bottom, "#")
    p.stamp(HERO, x, y + 1)

    x, y = p.frame(89, 0, 127, 21, "#")
    skyline(p, x, y, y + 14)

    x, y = p.frame(89, 23, 127, bottom, ".")
    p.stamp(POLICE, x + 1, y + 1, mirror=True)
    for k in range(3):                                               # the road it comes down
        p.fill(x + 18, y + 32 + 3 * k, x + 18, y + 33 + 3 * k, "#")
    p.line(x + 3, y + 31, x - 6, y + 40, "#")
    p.line(x + 33, y + 31, x + 42, y + 40, "#")

    x, y = p.frame(40, 40, 87, bottom, ".")
    for k, (at, wide) in enumerate(((0, 4), (1, 2), (0, 3), (2, 2))):  # it is fast
        p.fill(x + at, y + 3 + 2 * k, x + at + wide - 1, y + 3 + 2 * k, "#")
    p.stamp(GETAWAY, x + 5, y + 1)
    p.fill(x, y + 14, x + 45, y + 14, "#")                           # the road
    for at in range(3, 46, 12):
        p.fill(x + at, y + 18, x + at + 6, y + 18, "#")
    return p.img


def main():
    folder = sys.argv[1]
    menu, game = picture(MENU_ROWS), picture(GAME_ROWS)
    menu.convert("1").save(os.path.join(folder, "title.png"))
    game.convert("1").save(os.path.join(folder, "title_game.png"))
    if len(sys.argv) > 2:
        # enlarged copies to look at, the menu's above the game's
        sheet = Image.new("L", (W * 6, (MENU_ROWS + GAME_ROWS + 4) * 6), 90)
        sheet.paste(menu.resize((W * 6, MENU_ROWS * 6), Image.NEAREST), (0, 0))
        sheet.paste(game.resize((W * 6, GAME_ROWS * 6), Image.NEAREST), (0, (MENU_ROWS + 4) * 6))
        sheet.save(sys.argv[2])
    print("wrote title.png and title_game.png to", folder)


if __name__ == "__main__":
    main()
