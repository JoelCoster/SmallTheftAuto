// Small Theft Auto - pages: the title, the map, the settings, a mission offered.
//
// A page is black and white and 128 dots wide (platform.h, disp_wide), which
// is what lettering and a map need; the 3D view has dots twice as wide. While
// a page is up the game stands still, and the light is off: it is a police
// light and nothing else, the settings page does not show it either.
//
//   title      B starts the game, A goes to the settings
//   map        LEFT and RIGHT together, any time during the game; the same
//              again puts it away. The four directions move a cross over the
//              map, and the map with it. B sets the marker: that is where I
//              want to go; back to the game, where an arrow shows the way.
//              On the player's own place B takes the marker away: no arrow.
//              A goes to the settings
//   settings   UP and DOWN pick a line, B changes it, A goes back. The last
//              line is START OVER: no money, no mission done, back to where
//              the game begins. It asks once more before it does it
//   mission    DOWN next to a telephone that rings: what the mission is, in
//              the words of whoever is on the line. B takes it, A does not
//
// With a mission on, the marker is the mission's: it is where the mission
// wants the player, and B on the map sets nothing.
//
// The pictures (title, map of the whole city) are on the flash chip, drawn by
// tools/title.py and tools/build_assets.py.
#pragma once

#define MAP_BYTES 16               // per column of the map: 128 rows
#define MAP_STEPS (MAP_BYTES - COLBYTES)
#define MAP_EDGE 5                 // the cross stays this far from the edges: it is this long each way
#define MAP_AHEAD 16               // and the map moves along before the cross gets this near to its upper or lower edge

static uint8_t page_from;          // settings: the page to go back to
static uint8_t page_pick;          // map: how far down it has been moved, in steps of 8 rows;
                                   // settings: the line the mark is on
static uint8_t settings_were;      // as they were when the settings page came up
static bool page_sure;             // settings: START OVER has been asked for once
static uint8_t map_x, map_y;       // map: where the cross is, in dots of the map (two cells to the dot)
static uint8_t map_tick, map_wait; // when the cross moved last, and how many ticks until it does again

static void settings_apply() {
  sound_enable(settings & SET_SOUND);
}

// A picture on the flash chip, 7 bytes of it for every column of dots (it
// has so many bytes to the column): its columns from here on, so many
static void page_picture(uint24_t addr, uint8_t bytes, uint8_t x, uint8_t columns) {
  addr += (uint16_t)x * bytes;
  while (columns--) {
    fx_read(addr, page_column(x++), COLBYTES);
    addr += bytes;
  }
}

static void map_picture(uint8_t x, uint8_t columns) {
  page_picture(FX_MAP_PICTURE + page_pick, MAP_BYTES, x, columns);
}

static void page_clear() {
  for (uint16_t i = 0; i < FB_BYTES; i++) fb_hi[i] = fb_lo[i] = 0;
}

// Dots of the map around a place on it, so many to each side, lit or made
// dark. Nothing is done if they are not on the page in full (false).
static bool page_box(uint8_t x, uint8_t y, uint8_t wide, uint8_t high, bool lit) {
  uint8_t left = x - wide;
  uint8_t top = y - page_pick * 8 - high;
  wide = 2 * wide + 1;
  high = 2 * high + 1;
  if (left > (uint8_t)(128 - wide) || top > (uint8_t)(ROWS - high)) return false;
  while (wide--) {
    uint8_t *p = page_column(left++);
    uint8_t row = top;
    for (uint8_t n = high; n--; row++) {
      uint8_t dot = pgm_read_byte(&BITMASK[row & 7]);
      uint8_t *q = p + (row >> 3);
      if (lit) *q |= dot;
      else *q &= ~dot;
    }
  }
  return true;
}

// a mark on the map: a square of lit dots in a dark one
static void page_mark(uint8_t x, uint8_t y, uint8_t half) {
  page_box(x, y, 3, 3, false);
  page_box(x, y, half, half, true);
}

// The cross: lit, with dark round it so that it shows on streets as well as
// on houses, and a gap in the middle.
static void map_cross() {
  page_box(map_x, map_y, MAP_EDGE, 1, false);
  page_box(map_x, map_y, 1, MAP_EDGE, false);
  page_box(map_x, map_y, MAP_EDGE - 1, 0, true);
  page_box(map_x, map_y, 0, MAP_EDGE - 1, true);
  page_box(map_x, map_y, 1, 1, false);
}

static uint8_t map_inside(uint8_t v) {
  return v < MAP_EDGE ? MAP_EDGE : v > 127 - MAP_EDGE ? 127 - MAP_EDGE : v;
}

// B on the map sets the marker: where the cross is, that is where the player
// wants to go
static void nav_pick() {
  nav_x = 0;
  nav_way = NONE;
  // on their own place: nowhere
  if ((uint8_t)(map_x - (uint8_t)(hero.x >> 9) + 1) < 3 && (uint8_t)(map_y - (uint8_t)(hero.y >> 9) + 1) < 3) return;
  // The arrow leads to the nearest street, looking north, east, south and
  // west from the cross: a place that can be got to. No street anywhere
  // near: the place itself.
  int16_t cx = map_x * 2, cy = map_y * 2;
  nav_x = (uint8_t)cx;
  nav_y = (uint8_t)cy;
  for (uint8_t far = 0; far < 32; far++) {
    for (uint8_t d = 0; d < 4; d++) {
      int16_t x = cx + dir_x(d) * far, y = cy + dir_y(d) * far;
      if (x < 1 || x > 254 || y < 1 || y > 254) continue;
      if (!is_road(cell_at((uint8_t)x, (uint8_t)y))) continue;
      nav_x = (uint8_t)x;
      nav_y = (uint8_t)y;
      return;
    }
  }
}

static uint8_t page_drawn;         // the page as it was drawn last, and whether the mark was large

// A mark on the map for every telephone that rings: the first letter of
// whoever is on the line, on a dark ground.
static void map_phones() {
  for (uint8_t k = 0; k < N_PHONES; k++) {
    if (!phone_rings(k)) continue;
    uint8_t x = spot_x >> 9, y = spot_y >> 9;
    if (!page_box(x, y, 2, 3, false)) continue;
    // the letter's three columns of dots, five rows from two above the place
    const uint8_t *g = &FONT[pgm_read_byte(&PHONE_SIGNS[k]) * 3];
    for (uint8_t c = 0; c < 3; c++) {
      uint8_t dots = pgm_read_byte(g++);
      for (uint8_t r = 0; r < 5; r++)
        if ((dots >>= 1) & 1) page_box(x - 1 + c, y - 2 + r, 0, 0, true);
    }
  }
}

static void page_open(uint8_t which) {
  if (which == PAGE_SETTINGS) {
    page_from = page;
    page_pick = 0;
    page_sure = false;
    settings_were = settings;
  } else if (which == PAGE_MAP) {
    // the cross on the player, the player in the middle, as far as the map goes
    map_x = map_inside(hero.x >> 9);
    map_y = map_inside(hero.y >> 9);
    int8_t step = (int8_t)(map_y >> 3) - 3;
    page_pick = step < 0 ? 0 : step > MAP_STEPS ? MAP_STEPS : step;
    // what brought the map up is not meant for the cross
    held = BTN_LEFT | BTN_RIGHT;
  }
  if (page == PAGE_SETTINGS && settings != settings_were) save_store();
  light(LIGHT_OFF);
  // black is black both ways of showing the picture: nothing flashes up
  page_clear();
  hud_clear();
  page = which;
  page_drawn = 0xFF;
  disp_wide = which != PAGE_GAME;
  if (which == PAGE_GAME) {
    // what was pressed to get here is not meant for the game
    held = BTN_UP | BTN_DOWN | BTN_LEFT | BTN_RIGHT | BTN_A | BTN_B;
    last_tick = ticks();
  }
}

static void setting_line(uint8_t band, const char *name, const char *is) {
  text_band = band;
  hud_char(20, page_pick == band - 3 ? '>' : ' ');
  hud_text(28, name);
  hud_text(92, is);
}

static const char *on_or_off(uint8_t which) {
  return (settings & which) ? PSTR("ON ") : PSTR("OFF");
}

// no money, no mission done, and the player where the game begins
static void start_over() {
  if (job != NONE) job_end(SPR_FAILED);
  for (uint8_t i = 1; i < sizeof(kept); i++) ((uint8_t *)&kept)[i] = 0;
  note = 0;
  save_store();
  game_init();
  page_from = PAGE_TITLE;
}

static void page_frame(uint8_t btn, uint8_t fresh) {
  // ---- the buttons
  bool move = false;
  switch (page) {
    case PAGE_MAP: {
      if ((btn & (BTN_LEFT | BTN_RIGHT)) == (BTN_LEFT | BTN_RIGHT)) {
        page_open(PAGE_GAME);              // put away, and nothing has changed
        return;
      }
      // the cross: a dot for a tap; held down, on and on after a moment
      uint8_t go = btn & (BTN_UP | BTN_DOWN | BTN_LEFT | BTN_RIGHT);
      uint8_t tick = (uint8_t)last_tick;
      if (go && ((fresh & go) || (uint8_t)(tick - map_tick) >= map_wait)) {
        map_wait = (fresh & go) ? 45 : 4;
        map_tick = tick;
        move = true;
      }
      if ((fresh & BTN_B) && job == NONE) nav_pick();
    }
      // fall through
    case PAGE_TITLE:
      if (fresh & BTN_B) page_open(PAGE_GAME);
      else if (fresh & BTN_A) page_open(PAGE_SETTINGS);
      break;
    case PAGE_JOB:
      if (fresh & BTN_B) job_take();
      if (fresh & (BTN_A | BTN_B)) page_open(PAGE_GAME);
      break;
    default:
      if (fresh & (BTN_UP | BTN_DOWN)) {
        // three lines, round and round
        page_pick += (fresh & BTN_DOWN) ? 1 : 2;
        if (page_pick > 2) page_pick -= 3;
        page_sure = false;
      }
      if (fresh & BTN_B) {
        if (page_pick == 2) {
          // (it cannot be undone: asked for twice, then done)
          if (page_sure) start_over();
          page_sure = !page_sure;
        } else {
          settings ^= page_pick ? SET_LED : SET_SOUND;
          settings_apply();
        }
        sound_play(SOUND_CASH);
      }
      if (fresh & BTN_A) page_open(page_from);
      break;
  }

  // ---- the picture, when there is something new to show: drawing it over
  // and over would make it flicker
  uint8_t now = page | ((uint8_t)(last_tick >> 1) & 0x10);     // the mark changes five times a second
  bool whole = page_drawn == 0xFF;
  if (page == PAGE_MAP) {
    // the map itself is fetched when it has moved, not for a mark
    if (now == page_drawn && !move) return;
    if (move) {
      // what the cross has been standing on
      if (!whole) map_picture(map_x - MAP_EDGE, 2 * MAP_EDGE + 1);
      if (btn & BTN_LEFT) map_x--;
      if (btn & BTN_RIGHT) map_x++;
      if (btn & BTN_UP) map_y--;
      if (btn & BTN_DOWN) map_y++;
      map_x = map_inside(map_x);
      map_y = map_inside(map_y);
      // the map goes along, as far as it goes, so that there is something
      // to be seen ahead of the cross
      uint8_t row = map_y - page_pick * 8;
      if (row < MAP_AHEAD) {
        if (page_pick) {
          page_pick--;
          whole = true;
        }
      } else if (row > ROWS - 1 - MAP_AHEAD && page_pick < MAP_STEPS) {
        page_pick++;
        whole = true;
      }
    }
  } else if (now == page_drawn && !fresh) return;
  page_drawn = now;
  bool blink = now & 0x10;
  text_band = 7;
  switch (page) {
    case PAGE_GAME:
      break;

    case PAGE_TITLE:
      page_picture(FX_TITLE, COLBYTES, 0, 128);
      hud_text(14, PSTR("B:START     A:SETTINGS"));
      break;

    case PAGE_MAP:
      if (whole) {
        map_picture(0, 128);
        hud_text(16, job == NONE ? PSTR("B:SET MARKER  A:SETTINGS") : PSTR("B:BACK        A:SETTINGS"));
      }
      map_phones();
      // the marker, where the player wants to go (or a mission wants them): a ring
      if (nav_x) {
        page_mark(nav_x >> 1, nav_y >> 1, 2);
        page_box(nav_x >> 1, nav_y >> 1, 1, 1, false);
      }
      // where the player is: a square that grows and shrinks, with room around it
      page_mark(hero.x >> 9, hero.y >> 9, blink ? 2 : 1);
      map_cross();
      break;

    case PAGE_JOB:
      hud_text(14, PSTR("B:TAKE THE JOB   A:NOT NOW"));
      // its name and what it pays, a line under them, and what it is about
      for (uint8_t line = 0; line < JOB_LINES; line++) {
        text_band = line ? line + 1 : 0;
        hud_run(4, job_of(phone), JOB_TEXT + line * JOB_LINE, JOB_LINE);
      }
      for (uint8_t x = 4; x < 124; x++) page_column(x)[1] = 0x04;
      text_band = 7;
      break;

    default:
      hud_text(22, PSTR("B:CHANGE     A:BACK"));
      text_band = 0;
      hud_text(48, PSTR("SETTINGS"));
      for (uint8_t x = 8; x < 120; x++) page_column(x)[1] = 0x04;
      setting_line(3, PSTR("SOUND"), on_or_off(SET_SOUND));
      setting_line(4, PSTR("POLICE LIGHT"), on_or_off(SET_LED));
      setting_line(5, PSTR("START OVER"), page_sure ? PSTR("SURE?") : PSTR("     "));
      text_band = 7;
      break;
  }
}
